from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission for admin users only"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'admin'


class IsDoctor(permissions.BasePermission):
    """Permission for doctor users only"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'doctor'


class IsReceptionist(permissions.BasePermission):
    """Permission for receptionist users only"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'receptionist'


class IsPatient(permissions.BasePermission):
    """Permission for patient users only"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'patient'


from rest_framework import permissions

class IsAdminOrReceptionist(permissions.BasePermission):
    """Permission for admin or receptionist"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Check if user has a profile with role
        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['admin', 'receptionist']
        return False

class IsClinicStaff(permissions.BasePermission):
    """Authenticated clinic staff (not public/anonymous clients)."""
    allowed_roles = {'admin', 'doctor', 'receptionist', 'accountant', 'nurse', 'assistant'}

    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                hasattr(request.user, 'profile') and
                request.user.profile.role in self.allowed_roles and
                request.user.profile.is_active and
                request.user.is_active)
