"""Field-level encryption for secrets and personal data kept in the database.

Values are encrypted with Fernet (AES-128-CBC with an HMAC-SHA256 check) under the keys in
FIELD_ENCRYPTION_KEYS. MultiFernet encrypts with the first key and decrypts with any of them, so a
key can be rotated: put the new key first, keep the old one after it, run
`manage.py rotate_field_encryption`, then remove the old key. A copy of the database (a backup, a
leaked dump) is then useless without the keys, which live only in the server's environment.

Stored values start with "fernet:". Anything else is a value written before encryption was
switched on; it is read as it is and encrypted the next time it is saved (the migration that
introduces an encrypted field encrypts every existing row).
"""

import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django import forms
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

PREFIX = "fernet:"


@lru_cache(maxsize=4)
def _cipher(keys):
    return MultiFernet([Fernet(key) for key in keys])


def cipher():
    return _cipher(tuple(settings.FIELD_ENCRYPTION_KEYS))


def encrypt(text):
    return PREFIX + cipher().encrypt(text.encode()).decode()


def decrypt(value):
    if not value.startswith(PREFIX):
        return value  # written before encryption: re-encrypted on the next save
    try:
        return cipher().decrypt(value[len(PREFIX) :].encode()).decode()
    except InvalidToken:
        raise ImproperlyConfigured(
            "An encrypted value can't be decrypted with FIELD_ENCRYPTION_KEYS. Was a key removed too early?"
        ) from None


class EncryptedTextField(models.TextField):
    """Text kept encrypted in the database and plain in Python. Empty stays empty (so "is it set?"
    still works); other lookups on the value can't, so use it only for values never searched."""

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value else value

    def to_python(self, value):
        value = super().to_python(value)
        return decrypt(value) if value else value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt(value) if value else value


class EncryptedJSONField(models.TextField):
    """JSON data (a dict, a list...) kept encrypted in the database and as Python values in code, like
    a JSONField without lookups into it. Rows written before encryption (plain JSON) are still read."""

    def from_db_value(self, value, expression, connection):
        return json.loads(decrypt(value)) if value is not None else value

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        return encrypt(json.dumps(value, cls=DjangoJSONEncoder)) if value is not None else value

    def value_to_string(self, obj):
        return self.value_from_object(obj)  # like JSONField: serializers write the data itself

    def formfield(self, **kwargs):
        return super().formfield(**{"form_class": forms.JSONField, "encoder": DjangoJSONEncoder, **kwargs})


# Every field type whose values are encrypted (manage.py rotate_field_encryption re-encrypts them all).
ENCRYPTED_FIELDS = (EncryptedTextField, EncryptedJSONField)
