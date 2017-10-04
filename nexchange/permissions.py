from rest_framework import permissions
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User


class OwnerOnlyPermission(permissions.BasePermission):
    message = _('You do not have permission to view this resource')

    def has_object_permission(self, request, view, obj):
        # raise Exception(obj)
        user = obj if isinstance(obj, User) else getattr(obj, 'user')
        if user == request.user:
            return True
        return False


class NoUpdatePermission(permissions.BasePermission):
    SAFE_METHODS = ['GET', 'POST']
    message = _('DELETE/UPDATE requests are not allowed for this resource')

    def has_permission(self, request, view):
        if request.method in NoUpdatePermission.SAFE_METHODS:
            return True
        return False


class GetOnlyPermission(permissions.BasePermission):
    SAFE_METHODS = ['GET']
    message = _('DELETE/UPDATE/POST requests are not allowed for this resource')

    def has_permission(self, request, view):
        if request.method in NoUpdatePermission.SAFE_METHODS:
            return True
        return False
