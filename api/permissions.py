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


class IsAdminOrReceptionist(permissions.BasePermission):
    """Permission for admin or receptionist"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role in ['admin', 'receptionist']