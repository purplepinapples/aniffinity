"""malaffinity exceptions."""


class RateLimitExceededError(Exception):  # noqa: D204, D205, D400
    """
    Raised when the service is blocking your request, because you're going
    over their rate limit. Slow down and try again.
    """
    pass


class MALAffinityException(Exception):  # noqa: D204
    """Base class for MALAffinity exceptions."""
    pass


class NoAffinityError(MALAffinityException):  # noqa: D204, D205, D400
    """
    Raised when either the shared rated anime between the base user
    and another user is less than 11, the user does not have any rated
    anime, or the standard deviation of either users' scores is zero.
    """
    pass


class InvalidUsernameError(MALAffinityException):  # noqa: D204
    """Raised when username specified does not exist."""
    pass