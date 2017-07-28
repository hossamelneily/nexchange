from rest_framework import permissions
from django.utils.translation import ugettext_lazy as _


class OwnerOnlyPermission(permissions.BasePermission):
    message = _('You do not have permission to view this resource')

    def has_object_permission(self, request, view, obj):
        if getattr(obj, 'user') == request.user:
            return True
        return False


class NoUpdatePermission(permissions.BasePermission):
    SAFE_METHODS = ['GET', 'POST']
    message = _('DELETE/UPDATE requests are not allowed for this resource')

    def has_permission(self, request, view):
        if request.method in NoUpdatePermission.SAFE_METHODS:
            return True
        return False
