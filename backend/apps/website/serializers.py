from rest_framework import serializers

from apps.core.text import CleanCharField

from .models import ContactMessage


class ContactSerializer(serializers.Serializer):
    name = CleanCharField(max_length=120)
    email = serializers.EmailField(max_length=254)
    school = CleanCharField(max_length=200, required=False, allow_blank=True, default="")
    message = CleanCharField(multiline=True, min_length=10, max_length=5000)
    # A field people never see (the form hides it): only robots fill it in.
    website = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")

    def validate_name(self, value):
        return " ".join(value.split())

    def validate_email(self, value):
        return value.strip().lower()


class AdminContactSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    handled_by = serializers.CharField(source="handled_by.display_name", read_only=True, default=None)

    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "school", "message", "language", "sender", "created_at", "handled_at", "handled_by"]
        read_only_fields = fields

    def get_sender(self, message):
        """The account that sent it (when signed in), as platform admins see accounts."""
        user = message.user
        if user is None:
            return None
        return {"id": user.id, "username": user.username, "role": user.role}


class HandleSerializer(serializers.Serializer):
    handled = serializers.BooleanField()
