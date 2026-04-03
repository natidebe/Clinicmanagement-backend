from rest_framework.permissions import BasePermission

VALID_ROLES = ('admin', 'doctor', 'lab_tech', 'receptionist')


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'doctor'


class IsLabTech(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'lab_tech'


class IsReceptionist(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'receptionist'


class IsAdminOrSelf(BasePermission):
    """Allows admins full access; non-admins only access their own profile."""

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.id == request.user.id


class HasRole(BasePermission):
    """
    Inline role gate. Usage:
        permission_classes = [HasRole.for_roles('admin', 'doctor')]
    """
    required_roles: tuple = ()

    @classmethod
    def for_roles(cls, *roles):
        return type('HasRole', (cls,), {'required_roles': roles})

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in self.required_roles
        )
