from rest_framework.throttling import UserRateThrottle


class JoinRateThrottle(UserRateThrottle):
    """Per user: limits guessing of class, study-group and parent-link codes."""

    scope = "join"
