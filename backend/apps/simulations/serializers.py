from rest_framework import serializers

from .models import Simulation


class SimulationSerializer(serializers.ModelSerializer):
    embed_url = serializers.SerializerMethodField()
    subjects = serializers.SlugRelatedField(many=True, read_only=True, slug_field="code")
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)

    class Meta:
        model = Simulation
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "provider",
            "provider_label",
            "provider_id",
            "embed_url",
            "subjects",
            "grades",
            "topics",
            "learning_goals",
            "supports_kinyarwanda",
        ]

    def get_embed_url(self, sim):
        return sim.embed_url(self.context.get("lang", "en"))
