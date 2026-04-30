"""
Tenant scoping helpers for multi-tenant SaaS isolation.

Every tenant-scoped queryset and write should pass through these helpers so we
have a single, audited choke point. Platform-level ADMIN bypasses scoping.
"""
from rest_framework.exceptions import PermissionDenied


PLATFORM_ROLES = {'ADMIN'}  # roles that see across tenants (us, the SaaS operator)


def is_platform_admin(user):
    return getattr(user, 'role', None) in PLATFORM_ROLES


def get_user_org_id(user):
    """Resolve the org id for a user, preferring direct FK, then department, then managed."""
    if not user or not user.is_authenticated:
        return None
    org_id = getattr(user, 'organization_id', None)
    if org_id:
        return org_id
    dept = getattr(user, 'department', None)
    if dept and getattr(dept, 'organization_id', None):
        return dept.organization_id
    return getattr(user, 'managed_organization_id', None)


def scope_qs_to_org(queryset, user, user_path='user'):
    """
    Filter a queryset to the caller's tenant.

    `user_path` is the dotted ORM path from the model to the User row whose
    `organization` we should match (e.g. 'user' for ManualTimeEntry,
    'session__user' for NetworkActivity).

    Platform admins bypass scoping.
    """
    if is_platform_admin(user):
        return queryset
    org_id = get_user_org_id(user)
    if org_id is None:
        return queryset.none()
    return queryset.filter(**{f'{user_path}__organization_id': org_id})


def assert_same_org(target_user, requesting_user):
    """Raise PermissionDenied if `target_user` is not in `requesting_user`'s org."""
    if is_platform_admin(requesting_user):
        return
    a = get_user_org_id(requesting_user)
    b = get_user_org_id(target_user)
    if a is None or a != b:
        raise PermissionDenied('Cross-organization access is not allowed.')
