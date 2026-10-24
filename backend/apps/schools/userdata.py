"""The schools app's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py).

Money is never deleted. Payments a school administrator made and the money ledger are financial records Iga
must keep (tax and accounting law): after an erasure they still point at the user's row, which is emptied
and anonymised ("Deleted account"), and the ledger, which nothing may change, keeps the name it copied when
the entry was written."""

from apps.core.exporting import iso, number

from .models import Payment, School


def export_for(user):
    school = user.managed_school
    return {
        # School administrators: the school they run, as they manage it.
        "school_managed": (
            {
                "name": school.name,
                "district": school.district,
                "sector": school.sector,
                "phone": school.phone,
                "email": school.email,
                "status": school.status,
                "paid_until": iso(school.paid_until),
            }
            if school is not None
            else None
        ),
        "schools_registered": [
            {"name": s.name, "district": s.district, "created_at": iso(s.created_at)}
            for s in School.objects.filter(created_by=user).order_by("created_at")
        ],
        "payments_made": [
            {
                "reference": p.reference,
                "school": p.school.name,
                "months": p.months,
                "amount": number(p.amount),
                "currency": p.currency,
                "status": p.status,
                "provider": p.provider,
                "created_at": iso(p.created_at),
                "paid_at": iso(p.paid_at),
            }
            for p in Payment.objects.filter(created_by=user).select_related("school").order_by("created_at")
        ],
    }


def erase_for(user):
    # Nothing to delete: see the module docstring. The membership itself is emptied with the user row
    # (apps/accounts/userdata.py).
    return None
