from urllib.parse import quote

from django.conf import settings
from django.db import models


class Simulation(models.Model):
    """An interactive lab: a PhET sim, a GeoGebra app, or one of our own built-in sims."""

    class Provider(models.TextChoices):
        PHET = "phet", "PhET Interactive Simulations"
        GEOGEBRA = "geogebra", "GeoGebra"
        BUILTIN = "builtin", "Built-in (works offline)"
        EXTERNAL = "external", "Other embeddable page"

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    provider = models.CharField(max_length=12, choices=Provider.choices)
    provider_id = models.CharField(
        max_length=200,
        help_text=(
            "PhET: the sim name (e.g. 'projectile-motion'). GeoGebra: an app name "
            "('graphing', 'geometry', '3d') or a material id. Built-in: the component key. "
            "External: a full https URL."
        ),
    )
    subjects = models.ManyToManyField("curriculum.Subject", related_name="simulations", blank=True)
    grades = models.JSONField(default=list, blank=True, help_text='e.g. ["S1", "S2"]')
    topics = models.CharField(max_length=300, blank=True, help_text="Comma-separated keywords")
    learning_goals = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    GEOGEBRA_APPS = {"graphing", "geometry", "3d", "classic", "scientific", "suite"}

    def embed_url(self, lang="en"):
        if self.provider == self.Provider.PHET:
            name = quote(self.provider_id)
            locale = "fr" if lang == "fr" else "en"  # PhET sims are translated into French
            return f"https://phet.colorado.edu/sims/html/{name}/latest/{name}_all.html?locale={locale}"
        if self.provider == self.Provider.GEOGEBRA:
            if self.provider_id in self.GEOGEBRA_APPS:
                return None  # rendered client-side with the GeoGebra deploy script
            return f"https://www.geogebra.org/material/iframe/id/{quote(self.provider_id)}"
        if self.provider == self.Provider.EXTERNAL:
            return self.provider_id
        return None


class SimulationView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="simulation_views")
    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="views")
    viewed_at = models.DateTimeField(auto_now_add=True)
