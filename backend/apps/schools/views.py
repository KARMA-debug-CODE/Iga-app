import logging

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core import audit
from apps.core.permissions import IsPlatformAdmin
from apps.core.throttles import JoinRateThrottle

from . import billing, membership, notify, providers
from .access import content_access
from .constants import PROVINCES
from .models import Payment, School
from .serializers import (
    CheckoutSerializer,
    ChooseSchoolSerializer,
    DecideSerializer,
    ManualPaymentSerializer,
    MemberSerializer,
    PaymentSerializer,
    PlatformSchoolSerializer,
    SchoolAdminSerializer,
    SchoolListSerializer,
)

log = logging.getLogger(__name__)
MAX_RESULTS = 20


# --- Finding and joining a school --------------------------------------------------


class SchoolDirectoryView(APIView):
    """Verified schools, for the school picker at registration. ?q=name&district=Gasabo"""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        district = request.query_params.get("district") or ""
        if len(q) < 2 and not district:
            return Response([])
        qs = School.objects.filter(status=School.Status.VERIFIED)
        if q:
            qs = qs.filter(name__icontains=q)
        if district:
            qs = qs.filter(district=district)
        return Response(SchoolListSerializer(qs.order_by("name")[:MAX_RESULTS], many=True).data)


class DistrictsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response([{"province": p, "districts": d} for p, d in PROVINCES.items()])


class MySchoolView(APIView):
    """The signed-in user's school membership: see it, choose a school (optionally with its code), or leave."""

    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        if self.request.method == "POST":
            return [JoinRateThrottle()]  # guessing school codes
        return super().get_throttles()

    def _payload(self, user):
        from apps.accounts.serializers import school_summary

        result = content_access(user)
        return {
            "school": school_summary(user),
            "school_status": user.school_status,
            "access": {"premium": result.premium, "reason": result.reason},
        }

    def get(self, request):
        return Response(self._payload(request.user))

    def post(self, request):
        user = request.user
        if user.is_school_admin and user.school_id and user.school_status == User.SchoolStatus.APPROVED:
            raise ValidationError({"school": "School administrators change school through the Iga team."})
        data = ChooseSchoolSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        membership.choose_school(user, data.validated_data["school"], data.validated_data.get("school_code", ""), request=request)
        return Response(self._payload(user))

    def delete(self, request):
        user = request.user
        if user.is_school_admin and user.school_id and user.school_status == User.SchoolStatus.APPROVED:
            raise ValidationError({"school": "School administrators leave a school through the Iga team."})
        membership.leave_school(user, request=request)
        return Response(self._payload(user))


# --- The school administrator's dashboard -------------------------------------------


class IsSchoolAdmin(BasePermission):
    message = "Only approved school administrators can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.managed_school is not None)


def managed_school(request):
    return request.user.managed_school


class SchoolAdminView(APIView):
    permission_classes = [IsSchoolAdmin]

    def get(self, request):
        return Response(SchoolAdminSerializer(managed_school(request)).data)

    def patch(self, request):
        school = managed_school(request)
        serializer = SchoolAdminSerializer(school, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit.record(request, "update_school", school, fields=sorted(request.data.keys()))
        return Response(serializer.data)


class SchoolMembersView(APIView):
    """?status=pending|approved|rejected&role=student|teacher|school_admin&q=name"""

    permission_classes = [IsSchoolAdmin]

    def get(self, request):
        school = managed_school(request)
        qs = school.members.all()
        params = request.query_params
        if params.get("status") in User.SchoolStatus.values:
            qs = qs.filter(school_status=params["status"])
        if params.get("role") in User.Role.values:
            qs = qs.filter(role=params["role"])
        if params.get("grade"):
            qs = qs.filter(grade=params["grade"])
        if params.get("q"):
            term = params["q"].strip()
            qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(username__icontains=term))
        qs = qs.order_by("school_status", "role", "grade", "first_name", "last_name")[:1000]
        return Response(MemberSerializer(qs, many=True).data)


class DecideMembersView(APIView):
    permission_classes = [IsSchoolAdmin]

    def post(self, request):
        school = managed_school(request)
        data = DecideSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        users = list(User.objects.filter(pk__in=data.validated_data["ids"], school=school))
        changed = membership.decide(request.user, school, users, data.validated_data["approve"], request=request)
        return Response({"changed": [u.id for u in changed]})


class RemoveMemberView(APIView):
    permission_classes = [IsSchoolAdmin]

    def post(self, request, user_id):
        school = managed_school(request)
        user = get_object_or_404(User, pk=user_id, school=school)
        membership.remove(request.user, school, user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NewSchoolCodeView(APIView):
    permission_classes = [IsSchoolAdmin]

    def post(self, request):
        return Response({"join_code": membership.regenerate_code(request.user, managed_school(request), request=request)})


class SchoolPaymentsView(APIView):
    permission_classes = [IsSchoolAdmin]

    def get(self, request):
        payments = managed_school(request).payments.select_related("school", "created_by")[:200]
        return Response(PaymentSerializer(payments, many=True).data)


# --- Paying -------------------------------------------------------------------------------


class CheckoutView(APIView):
    """Start paying for N months: returns the provider's hosted checkout page to send the browser to."""

    permission_classes = [IsSchoolAdmin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "sensitive"

    def post(self, request):
        school = managed_school(request)
        data = CheckoutSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        provider = providers.online_provider()
        if provider is None:
            raise ValidationError("Online payment isn't set up yet. Please pay by bank transfer and contact the Iga team.")
        payment = billing.start_payment(
            school, request.user, data.validated_data["months"], data.validated_data["currency"].upper(), provider.key
        )
        try:
            url = provider.create_checkout(payment, request.user, request)
        except Exception:
            billing.fail_payment(payment, status=Payment.Status.CANCELLED)
            raise
        audit.record(request, "start_payment", school, reference=payment.reference, months=payment.months)
        return Response({"reference": payment.reference, "checkout_url": url}, status=status.HTTP_201_CREATED)


def _payment_for(request, reference):
    payment = get_object_or_404(Payment.objects.select_related("school"), reference=reference)
    user = request.user
    if not (user.is_platform_admin or (user.managed_school is not None and user.managed_school.pk == payment.school_id)):
        raise PermissionDenied("This payment belongs to another school.")
    return payment


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        return Response(PaymentSerializer(_payment_for(request, reference)).data)


class ConfirmPaymentView(APIView):
    """Called when the browser comes back from the provider. Asks the provider; never trusts the redirect.

    Body (optional): {"transaction_id": "..."} from the provider's redirect, so the attempt that
    just finished is the one checked. A payment marked failed or cancelled is checked again too,
    because the payer may have succeeded on a later attempt in the same checkout.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "billing_confirm"

    def post(self, request, reference):
        payment = _payment_for(request, reference)
        if payment.status != Payment.Status.SUCCEEDED and payment.provider != Payment.Provider.MANUAL:
            transaction_id = str(request.data.get("transaction_id") or "")[:40]
            verification = providers.get(payment.provider).verify(payment, transaction_id)
            payment = billing.settle(payment, verification, request=request)
        return Response(PaymentSerializer(payment).data)


class DevCompleteView(APIView):
    """The fake checkout's buttons (development and tests only)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, reference):
        provider = providers.get(Payment.Provider.DEV)
        if not provider.available():
            raise PermissionDenied("Test payments are switched off.")
        payment = _payment_for(request, reference)
        if payment.provider != Payment.Provider.DEV or payment.status != Payment.Status.PENDING:
            raise ValidationError("This payment can't be completed here.")
        outcome = "success" if request.data.get("outcome") == "success" else "cancel"
        payment.provider_data = {"dev_outcome": outcome}
        payment.save(update_fields=["provider_data"])
        payment = billing.settle(payment, provider.verify(payment), request=request)
        return Response(PaymentSerializer(payment).data)


class FlutterwaveWebhookView(APIView):
    """Flutterwave tells us a transaction changed. We check the signature, then ask its API."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        provider = providers.get(Payment.Provider.FLUTTERWAVE)
        if not provider.webhook_is_authentic(request):
            log.warning("Rejected a Flutterwave webhook with a bad signature")
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            payload = provider.parse_webhook(request.content_type, request.body)
        except ValueError:
            log.warning("Unreadable Flutterwave webhook (content type %s)", request.content_type)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        reference = provider.webhook_reference(payload)
        if not reference:
            # Acknowledge so it isn't retried, but say so: usually the dashboard isn't set to v3 JSON webhooks.
            log.warning("Flutterwave webhook without a transaction reference; fields: %s", sorted(payload)[:12])
            return Response({"ignored": True})
        payment = Payment.objects.filter(reference=reference, provider=Payment.Provider.FLUTTERWAVE).first()
        if payment is None:
            log.info("Flutterwave webhook for an unknown reference %s", reference[:60])
            return Response({"ignored": True})  # not ours: acknowledge so it isn't retried
        if payment.status != Payment.Status.SUCCEEDED:
            billing.settle(payment, provider.verify(payment, provider.webhook_transaction_id(payload)))
        return Response({"received": True})


# --- Platform administrators ------------------------------------------------------------


class PlatformSchoolsView(APIView):
    """All schools. ?status=pending|verified|suspended&q=name&subscription=active|unpaid"""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = School.objects.annotate(
            approved_members=Count("members", filter=Q(members__school_status=User.SchoolStatus.APPROVED))
        )
        params = request.query_params
        if params.get("status") in School.Status.values:
            qs = qs.filter(status=params["status"])
        if params.get("q"):
            qs = qs.filter(name__icontains=params["q"].strip())
        now = timezone.now()
        if params.get("subscription") == "active":
            qs = qs.filter(paid_until__gt=now)
        elif params.get("subscription") == "unpaid":
            qs = qs.filter(Q(paid_until__isnull=True) | Q(paid_until__lte=now))
        qs = qs.order_by("status", "name")[:500]
        rows = []
        for school in qs:
            rows.append(
                {
                    "id": school.id,
                    "name": school.name,
                    "district": school.district,
                    "status": school.status,
                    "members": school.approved_members,
                    "subscription": {"state": school.subscription_state(), "paid_until": school.paid_until},
                    "created_at": school.created_at,
                }
            )
        return Response(rows)


class PlatformSchoolDetailView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request, school_id):
        school = get_object_or_404(School, pk=school_id)
        data = PlatformSchoolSerializer(school).data
        data["payments"] = PaymentSerializer(school.payments.select_related("created_by")[:100], many=True).data
        return Response(data)

    def patch(self, request, school_id):
        school = get_object_or_404(School, pk=school_id)
        serializer = PlatformSchoolSerializer(school, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit.record(request, "update_school", school, fields=sorted(request.data.keys()))
        return Response(serializer.data)


class PlatformSchoolActionView(APIView):
    """POST verify | suspend | reinstate | reject (a pending registration that isn't a real school)."""

    permission_classes = [IsPlatformAdmin]

    def post(self, request, school_id, action):
        school = get_object_or_404(School, pk=school_id)
        if action == "verify":
            school.status = School.Status.VERIFIED
            school.verified_by = request.user
            school.verified_at = timezone.now()
            school.save(update_fields=["status", "verified_by", "verified_at"])
            # Whoever registered the school becomes its first administrator.
            creator = school.created_by
            if creator is not None and creator.school_id == school.pk and creator.school_status == User.SchoolStatus.PENDING:
                membership.decide(request.user, school, [creator], True)
        elif action == "suspend":
            school.status = School.Status.SUSPENDED
            school.save(update_fields=["status"])
        elif action == "reinstate":
            school.status = School.Status.VERIFIED
            school.save(update_fields=["status"])
        elif action == "reject":
            if school.status != School.Status.PENDING or school.payments.exists():
                raise ValidationError("Only a school waiting for verification, with no payments, can be rejected.")
            audit.record(request, "reject_school", school, name=school.name, district=school.district)
            school.delete()  # its members are released (signals.release_members)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("Unknown action.")
        audit.record(request, f"{action}_school", school)
        return Response(PlatformSchoolSerializer(school).data)


class PlatformManualPaymentView(APIView):
    """Record money received outside the app (bank transfer, mobile money to the company, cash) or free months."""

    permission_classes = [IsPlatformAdmin]

    def post(self, request, school_id):
        school = get_object_or_404(School, pk=school_id)
        data = ManualPaymentSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        payment = billing.record_manual_payment(school, request.user, v["months"], v["amount"], v["currency"], v["note"])
        audit.record(
            request,
            "manual_payment",
            school,
            reference=payment.reference,
            months=payment.months,
            amount=str(payment.amount),
            currency=payment.currency,
            note=payment.note,
        )
        notify.payment_received(payment)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PlatformMembersView(APIView):
    """Members of any school, for platform administrators (also approves pending school admins)."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request, school_id):
        school = get_object_or_404(School, pk=school_id)
        qs = school.members.order_by("school_status", "role", "first_name")[:1000]
        return Response(MemberSerializer(qs, many=True).data)

    def post(self, request, school_id):
        school = get_object_or_404(School, pk=school_id)
        data = DecideSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        users = list(User.objects.filter(pk__in=data.validated_data["ids"], school=school))
        changed = membership.decide(request.user, school, users, data.validated_data["approve"], request=request)
        return Response({"changed": [u.id for u in changed]})


def revenue_summary():
    """Paid money per currency for this calendar month and in total, plus active schools."""
    now = timezone.now()
    month_start = timezone.localtime(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid = Payment.objects.filter(status=Payment.Status.SUCCEEDED)

    def by_currency(qs):
        return {row["currency"]: f"{row['total']:.2f}" for row in qs.values("currency").annotate(total=Sum("amount"))}

    return {
        "this_month": by_currency(paid.filter(paid_at__gte=month_start)),
        "all_time": by_currency(paid),
        "active_schools": School.objects.filter(status=School.Status.VERIFIED, paid_until__gt=now).count(),
        "verified_schools": School.objects.filter(status=School.Status.VERIFIED).count(),
        "pending_schools": School.objects.filter(status=School.Status.PENDING).count(),
    }
