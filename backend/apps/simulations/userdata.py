"""The labs app's part of "Download my data" and "Delete my account" (apps/accounts/privacy.py)."""

from apps.core.exporting import iso

from .models import SimulationView


def export_for(user):
    return {
        "labs_opened": [
            {"lab": view.simulation.slug, "title": view.simulation.title, "opened_at": iso(view.viewed_at)}
            for view in SimulationView.objects.filter(user=user).select_related("simulation").order_by("viewed_at")
        ]
    }


def erase_for(user):
    SimulationView.objects.filter(user=user).delete()
