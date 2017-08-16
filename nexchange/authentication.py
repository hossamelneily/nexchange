
from rest_framework.authentication import BaseAuthentication


class SessionAuthenticationNoCSRF(BaseAuthentication):
    """
    Use Django's session framework for authentication.
    Don't force CSRF token usage (for web app).
    """

    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """
        # Get the underlying HttpRequest object
        request = request._request
        user = getattr(request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None

        return (user, None)

    def enforce_csrf(self, request):
        """
        Disable CSRF check!
        """
        pass
