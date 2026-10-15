"""Shared serializer behaviour."""

from rest_framework.utils import model_meta


class SaveChangedFieldsMixin:
    """Update only the columns the request changed.

    DRF's ModelSerializer.update saves the whole row, so a request that read a row just before someone
    else changed it writes the old values back: a profile edit could undo a school's approval or the Iga
    team withdrawing a teacher's approval, and a school's contact edit could undo a subscription payment
    (paid_until). Saving only the fields in the request leaves everyone else's changes alone.
    """

    def update(self, instance, validated_data):
        info = model_meta.get_field_info(instance)
        fields, many = [], []
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                many.append((attr, value))
            else:
                setattr(instance, attr, value)
                fields.append(attr)
        if fields:
            fields += [f.name for f in instance._meta.concrete_fields if getattr(f, "auto_now", False)]
            instance.save(update_fields=sorted(set(fields)))
        for attr, value in many:
            getattr(instance, attr).set(value)
        return instance
