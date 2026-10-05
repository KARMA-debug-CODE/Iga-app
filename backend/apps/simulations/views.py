from django.db.models import Q
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.utils import request_language
from apps.curriculum.models import localized_lesson_titles
from apps.gamification import services as gamification

from .models import Simulation, SimulationView
from .serializers import SimulationSerializer


class SimulationViewSet(viewsets.ReadOnlyModelViewSet):
    """The virtual lab library. Filters: ?subject=physics&grade=S2&provider=phet&q=circuit"""

    serializer_class = SimulationSerializer
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        qs = Simulation.objects.prefetch_related("subjects")
        params = self.request.query_params
        if params.get("subject"):
            qs = qs.filter(subjects__code=params["subject"])
        if params.get("provider"):
            qs = qs.filter(provider=params["provider"])
        if params.get("q"):
            term = params["q"]
            qs = qs.filter(Q(title__icontains=term) | Q(topics__icontains=term) | Q(description__icontains=term))
        qs = qs.distinct()
        grade = params.get("grade")
        if grade:
            # JSON containment isn't supported on every database, so filter in Python (the catalogue is small).
            return [sim for sim in qs if not sim.grades or grade in sim.grades]
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": request_language(self.request)}

    def get_object(self):
        return Simulation.objects.prefetch_related("subjects").get(slug=self.kwargs["slug"])

    def retrieve(self, request, *args, **kwargs):
        try:
            sim = self.get_object()
        except Simulation.DoesNotExist:
            return Response({"detail": _("Not found.")}, status=404)
        data = self.get_serializer(sim).data
        lessons = list(sim.lessons.filter(status="published")[:10])
        titles = localized_lesson_titles(lessons, request_language(request))
        data["lessons"] = [{"slug": lesson.slug, "title": titles[lesson.id]} for lesson in lessons]
        return Response(data)

    @action(detail=True, methods=["post"])
    def view(self, request, slug=None):
        try:
            sim = self.get_object()
        except Simulation.DoesNotExist:
            return Response({"detail": _("Not found.")}, status=404)
        SimulationView.objects.create(user=request.user, simulation=sim)
        xp = gamification.on_simulation_viewed(request.user, sim)
        return Response({"xp_gained": xp, "xp": request.user.xp})
