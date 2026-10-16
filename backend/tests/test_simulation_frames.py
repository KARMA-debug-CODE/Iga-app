"""Simulations are shown in a frame that may run scripts (frontend/src/components/SimEmbed.jsx), so an
"external" simulation's address must be an https page: never javascript:, data: or plain http."""

import pytest
from django.core.exceptions import ValidationError

from apps.simulations.models import Simulation

pytestmark = pytest.mark.django_db

UNSAFE = [
    "javascript:alert(document.domain)",
    " JavaScript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "http://example.org/lab",
    "//example.org/lab",
    "/api/auth/me/",
    "https:///nohost",
]


@pytest.mark.parametrize("address", UNSAFE)
def test_an_external_simulation_needs_an_https_address(client_for, student, address):
    sim = Simulation(slug="lab", title="Lab", provider="external", provider_id=address)
    with pytest.raises(ValidationError) as refused:
        sim.full_clean()
    assert "provider_id" in refused.value.message_dict
    # One stored anyway (an import, an older row) is never handed to the browser.
    sim.save()
    assert sim.embed_url() is None
    assert client_for(student).get("/api/simulations/lab/").data["embed_url"] is None


def test_https_pages_and_known_providers_still_work(client_for, student):
    Simulation.objects.create(slug="ext", title="Ext", provider="external", provider_id="https://lab.example.org/x?y=1")
    Simulation.objects.create(slug="forces", title="Forces", provider="phet", provider_id="forces-and-motion-basics")
    Simulation(slug="ok", title="Ok", provider="external", provider_id="https://lab.example.org/x").full_clean()
    client = client_for(student)
    assert client.get("/api/simulations/ext/").data["embed_url"] == "https://lab.example.org/x?y=1"
    assert client.get("/api/simulations/forces/").data["embed_url"].startswith("https://phet.colorado.edu/sims/html/")
