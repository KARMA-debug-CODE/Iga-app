"""Profile avatars: drawn by the app (frontend/src/components/Avatar.jsx) from a few choices, never a photo.

An avatar is a small dict such as {"skin": 3, "hair": 4, ...}; each value is an index into that part's
options. Missing parts are filled from the user's id, so everyone has a stable avatar from the start.
Keep these counts in step with Avatar.jsx.
"""

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

PARTS = {
    "bg": 10,  # background colour
    "skin": 6,  # skin tone
    "hair": 10,  # none, short, buzz cut, afro, braids, bun, long, twists, headwrap, cap
    "hairColor": 6,
    "eyes": 5,
    "mouth": 5,
    "extra": 5,  # none, round glasses, square glasses, earrings, freckles
    "top": 8,  # uniform colour
}


def clean(value):
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValidationError(_("Choose an avatar from the options."))
    cleaned = {}
    for key, raw in value.items():
        if key not in PARTS or isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw < PARTS[key]:
            raise ValidationError(_("Choose an avatar from the options."))
        cleaned[key] = raw
    return cleaned
