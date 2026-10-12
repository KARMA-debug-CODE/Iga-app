"""The demo accounts made by `manage.py seed_demo`, and how to recognise them.

Their password is public (README, the landing page in development), so they must never exist on a
real server: seed_demo refuses to run with DEBUG off, `manage.py check` (and so `migrate`, which runs
when the container starts) fails on a real deployment that still has any, and
`manage.py remove_demo_accounts` switches them off.
"""

from django.db.models import Q

DEMO_PASSWORD = "Iga-demo-2026"
DEMO_EMAIL_DOMAIN = "demo.iga.rw"
DEMO_USERNAMES = (
    "admin",
    "teacher",
    "parent",
    "aline",
    "eric",
    "divine",
    "kevin",
    "grace",
    "lkadmin",
    "apadeadmin",
    "samuel",
    "gsadmin",
)


def demo_accounts():
    """Active accounts that still sign in with the public demo password."""
    from apps.accounts.models import User

    candidates = User.objects.filter(is_active=True).filter(
        Q(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}") | Q(username__in=DEMO_USERNAMES)
    )
    return [user for user in candidates if user.has_usable_password() and user.check_password(DEMO_PASSWORD)]
