from django.conf import settings
from django.contrib.auth.hashers import Argon2PasswordHasher


class IgaArgon2PasswordHasher(Argon2PasswordHasher):
    """Argon2id (Django's Argon2 hasher uses the "id" variant) with costs from the settings.

    It keeps Django's algorithm name, so stored hashes stay readable by Django's own hasher. When the
    costs change, Django re-hashes each password the next time its owner logs in.
    """

    @property
    def time_cost(self):
        return settings.ARGON2_TIME_COST

    @property
    def memory_cost(self):
        return settings.ARGON2_MEMORY_COST_KIB

    @property
    def parallelism(self):
        return settings.ARGON2_PARALLELISM
