"""Santa's allowances: how much of the school server's model each student, and each school, may use.

Santa's model is the costliest thing Iga runs, so its use is counted (SantaUsage, one row per student and day)
and capped, all from settings (0 = no limit):

* per student, per day and per calendar month: questions the model answered (SANTA_USER_DAILY_QUESTIONS,
  SANTA_USER_MONTHLY_QUESTIONS) and the tokens they took (SANTA_USER_DAILY_TOKENS, SANTA_USER_MONTHLY_TOKENS);
* per school, per day: the tokens all its members took together (SANTA_SCHOOL_DAILY_TOKENS).

Days and months are Kigali time (TIME_ZONE). A question is let through while something is left, so one
answer may go a little over; one answer at a time per student (services.answer) keeps that to one answer.
When an allowance is used up, Santa answers from the lesson passages instead and says why, and the
student sees what is left (`Allowance.public`). Questions answered from the lessons for any reason don't
count, so a student is never left without help. Platform admins see the totals (`summary`).
"""

import math
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from .models import SantaUsage

CHARS_PER_TOKEN = 3  # what Santa's limits assume (French and maths take more tokens than English prose)

# Why Santa is answering from the lessons: the allowance used up, in the order they are checked.
DAY, MONTH, SCHOOL = "limit_day", "limit_month", "limit_school"


def estimate_tokens(chars):
    return math.ceil(max(0, chars) / CHARS_PER_TOKEN)


def _today():
    return timezone.localdate()


@dataclass(frozen=True)
class Allowance:
    questions_today: int = 0
    tokens_today: int = 0
    questions_month: int = 0
    tokens_month: int = 0
    school_tokens_today: int = 0
    has_school: bool = False

    @staticmethod
    def _left(limit, used):
        return None if not limit else max(0, limit - used)

    @property
    def reached(self):
        """DAY, MONTH or SCHOOL when an allowance is used up (the first that applies), else ""."""
        s = settings
        if self._left(s.SANTA_USER_DAILY_QUESTIONS, self.questions_today) == 0:
            return DAY
        if self._left(s.SANTA_USER_DAILY_TOKENS, self.tokens_today) == 0:
            return DAY
        if self._left(s.SANTA_USER_MONTHLY_QUESTIONS, self.questions_month) == 0:
            return MONTH
        if self._left(s.SANTA_USER_MONTHLY_TOKENS, self.tokens_month) == 0:
            return MONTH
        if self.has_school and self._left(s.SANTA_SCHOOL_DAILY_TOKENS, self.school_tokens_today) == 0:
            return SCHOOL
        return ""

    def public(self):
        """What the student is shown: questions left today and this month (None = no limit), and which
        allowance is used up. Token budgets are shown as a share left, since tokens mean nothing to a student."""
        s = settings
        shares = [
            self._left(limit, used) / limit
            for limit, used in (
                (s.SANTA_USER_DAILY_TOKENS, self.tokens_today),
                (s.SANTA_USER_MONTHLY_TOKENS, self.tokens_month),
            )
            if limit
        ]
        return {
            "questions_left_today": self._left(s.SANTA_USER_DAILY_QUESTIONS, self.questions_today),
            "questions_per_day": s.SANTA_USER_DAILY_QUESTIONS or None,
            "questions_left_month": self._left(s.SANTA_USER_MONTHLY_QUESTIONS, self.questions_month),
            "questions_per_month": s.SANTA_USER_MONTHLY_QUESTIONS or None,
            "time_left_percent": round(100 * min(shares)) if shares else None,
            "reached": self.reached,
        }


def allowance(user):
    """The student's use of Santa today and this month, and their school's today."""
    today = _today()
    rows = SantaUsage.objects.filter(user=user, day__gte=today.replace(day=1), day__lte=today)
    totals = rows.aggregate(
        questions_month=Sum("questions"),
        tokens_month=Sum(F("input_tokens") + F("output_tokens")),
        questions_today=Sum("questions", filter=Q(day=today)),
        tokens_today=Sum(F("input_tokens") + F("output_tokens"), filter=Q(day=today)),
    )
    school_tokens = 0
    if user.school_id and settings.SANTA_SCHOOL_DAILY_TOKENS:
        school_tokens = SantaUsage.objects.filter(school_id=user.school_id, day=today).aggregate(
            n=Sum(F("input_tokens") + F("output_tokens"))
        )["n"]
    return Allowance(
        questions_today=totals["questions_today"] or 0,
        tokens_today=totals["tokens_today"] or 0,
        questions_month=totals["questions_month"] or 0,
        tokens_month=totals["tokens_month"] or 0,
        school_tokens_today=school_tokens or 0,
        has_school=bool(user.school_id),
    )


def _row(user, today):
    try:
        with transaction.atomic():
            row, _ = SantaUsage.objects.get_or_create(user=user, day=today, defaults={"school_id": user.school_id})
    except IntegrityError:  # created by another request at the same moment
        row = SantaUsage.objects.get(user=user, day=today)
    return row


def record(user, input_tokens=0, output_tokens=0, limited=False):
    """Count one question: answered by the model (with its tokens), or from the lessons because an allowance
    was used up (`limited`)."""
    row = _row(user, _today())
    changes = {"school_id": user.school_id}
    if limited:
        changes["limited"] = F("limited") + 1
    else:
        changes.update(
            questions=F("questions") + 1,
            input_tokens=F("input_tokens") + max(0, int(input_tokens)),
            output_tokens=F("output_tokens") + max(0, int(output_tokens)),
        )
    SantaUsage.objects.filter(pk=row.pk).update(**changes)


def summary(top=5):
    """Santa's use for platform admins: today, the last 30 days, the busiest schools today, and the limits."""
    today = _today()

    def totals(rows):
        names = ("questions", "input_tokens", "output_tokens", "limited")
        t = rows.aggregate(
            **{f"total_{name}": Sum(name) for name in names},
            students=Count("user", distinct=True, filter=Q(questions__gt=0)),
        )
        return {name: t[f"total_{name}"] or 0 for name in names} | {"students": t["students"]}

    today_rows = SantaUsage.objects.filter(day=today)
    schools = (
        today_rows.exclude(school=None)
        .values("school_id", "school__name")
        .annotate(questions=Sum("questions"), tokens=Sum(F("input_tokens") + F("output_tokens")), students=Count("user"))
        .order_by("-tokens")[:top]
    )
    s = settings
    return {
        "today": totals(today_rows),
        "last_30_days": totals(SantaUsage.objects.filter(day__gt=today - timedelta(days=30))),
        "top_schools_today": [
            {"school": r["school__name"], "questions": r["questions"], "tokens": r["tokens"] or 0, "students": r["students"]}
            for r in schools
        ],
        "limits": {
            "user_daily_questions": s.SANTA_USER_DAILY_QUESTIONS,
            "user_monthly_questions": s.SANTA_USER_MONTHLY_QUESTIONS,
            "user_daily_tokens": s.SANTA_USER_DAILY_TOKENS,
            "user_monthly_tokens": s.SANTA_USER_MONTHLY_TOKENS,
            "school_daily_tokens": s.SANTA_SCHOOL_DAILY_TOKENS,
            "max_input_tokens": s.SANTA_MAX_INPUT_TOKENS,
            "max_output_tokens": s.SANTA_MAX_TOKENS,
            "parallel": s.SANTA_PARALLEL,
        },
    }
