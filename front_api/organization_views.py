"""
Organization-related API views for Organization, Department, JobPosition, and User assignment.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from tracker_api.models import Organization, Department, JobPosition, User
from .tenant import get_user_org_id, is_platform_admin
from .serializers import OrganizationSerializer, DepartmentSerializer, JobPositionSerializer, UserProfileSerializer


def _can_manage_org(user):
    """Admin, Manager, ORG_MANAGER, or ORG_ADMIN can access org pages."""
    return (user.is_admin_user() or user.is_manager_user()
            or user.is_org_manager_user() or user.is_org_admin_user())


def _can_write_org(user):
    """Only Admin, Manager, ORG_MANAGER can create/edit/delete orgs (not ORG_ADMIN)."""
    return user.is_admin_user() or user.is_manager_user() or user.is_org_manager_user()


def _scoped_orgs(user):
    """Restrict an Organization queryset to the caller's tenant. Platform admins see all."""
    qs = Organization.objects.filter(is_active=True)
    if is_platform_admin(user):
        return qs
    if user.is_org_manager_user():
        # ORG_MANAGER is a platform-side curator role today; treat as platform-admin for orgs
        return qs
    org_id = get_user_org_id(user) or getattr(user, 'managed_organization_id', None)
    if not org_id:
        return qs.none()
    return qs.filter(pk=org_id)


# ============================================================
# ORGANIZATION CRUD
# ============================================================

@extend_schema(methods=['POST'], request=OrganizationSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def organizations_list(request):
    if request.method == 'GET':
        if not _can_manage_org(request.user):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        orgs = _scoped_orgs(request.user)

        serializer = OrganizationSerializer(orgs, many=True)
        return Response({'success': True, 'organizations': serializer.data})

    # POST — only ORG_MANAGER / Admin / Manager can create orgs
    if not _can_write_org(request.user):
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = OrganizationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'success': True, 'organization': serializer.data}, status=status.HTTP_201_CREATED)
    return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['PUT'], request=OrganizationSerializer)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def organization_detail(request, pk):
    try:
        org = Organization.objects.get(pk=pk)
    except Organization.DoesNotExist:
        return Response({'success': False, 'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

    if not _can_manage_org(request.user):
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    # Tenant scoping: caller can only act on their own org (platform admins / org managers bypass)
    if not _scoped_orgs(request.user).filter(pk=org.pk).exists():
        return Response({'success': False, 'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'success': True, 'organization': OrganizationSerializer(org).data})

    if not _can_write_org(request.user):
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = OrganizationSerializer(org, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'organization': serializer.data})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not request.user.is_admin_user() and not request.user.is_org_manager_user():
            return Response({'success': False, 'error': 'Only administrators can delete organizations'}, status=status.HTTP_403_FORBIDDEN)
        org.is_active = False
        org.save()
        return Response({'success': True, 'message': 'Organization deactivated successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_org_admin(request, pk):
    """
    POST: Assign an ORG_ADMIN-role user as the admin of this organization.
    Only ORG_MANAGER can do this.
    Body: { "user_id": <int|null> }
    """
    if not request.user.is_org_manager_user():
        return Response({'error': 'Only Organization Managers can assign org admins'}, status=status.HTTP_403_FORBIDDEN)

    try:
        org = Organization.objects.get(pk=pk)
    except Organization.DoesNotExist:
        return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)

    user_id = request.data.get('user_id')

    # Clear any existing admin for this org
    User.objects.filter(managed_organization=org, role=User.ORG_ADMIN).update(managed_organization=None)

    if user_id is not None:
        try:
            admin_user = User.objects.get(pk=user_id, role=User.ORG_ADMIN)
        except User.DoesNotExist:
            return Response({'error': 'User not found or does not have the Administration role'}, status=status.HTTP_400_BAD_REQUEST)
        admin_user.managed_organization = org
        admin_user.save(update_fields=['managed_organization', 'updated_at'])

    return Response({'success': True, 'organization': OrganizationSerializer(org).data})


# ============================================================
# USER ASSIGNMENT (dept + position)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list_for_org(request):
    """List all active users with their department and position info."""
    if not _can_manage_org(request.user):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    users = User.objects.filter(is_active=True).select_related('department', 'position')

    if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
        org_id = get_user_org_id(request.user)
        if org_id is None:
            users = users.none()
        else:
            users = users.filter(organization_id=org_id)

    users = users.order_by('full_name')

    data = [{
        'id': u.id,
        'full_name': u.full_name,
        'employee_id': u.employee_id,
        'email': u.email,
        'role': u.role,
        'is_active': u.is_active,
        'department': u.department_id,
        'department_name': u.department.name if u.department else None,
        'position': u.position_id,
        'position_title': u.position.title if u.position else None,
    } for u in users]
    return Response({'success': True, 'users': data})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def assign_user(request, user_id):
    """PATCH: assign a user's department and/or position."""
    if not _can_manage_org(request.user):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Tenant scoping
    if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
        if get_user_org_id(user) != get_user_org_id(request.user):
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if 'department' in request.data:
        dept_id = request.data['department']
        if dept_id is None:
            user.department = None
        else:
            try:
                dept = Department.objects.get(pk=dept_id)
                # ORG_ADMIN: can only assign to their own org's departments
                if request.user.is_org_admin_user():
                    if dept.organization_id != request.user.managed_organization_id:
                        return Response({'error': 'You can only assign users to departments within your organization'}, status=status.HTTP_403_FORBIDDEN)
                user.department = dept
            except Department.DoesNotExist:
                return Response({'error': 'Department not found'}, status=status.HTTP_400_BAD_REQUEST)

    if 'position' in request.data:
        pos_id = request.data['position']
        if pos_id is None:
            user.position = None
        else:
            try:
                user.position = JobPosition.objects.get(pk=pos_id)
            except JobPosition.DoesNotExist:
                return Response({'error': 'Position not found'}, status=status.HTTP_400_BAD_REQUEST)

    user.save(update_fields=['department', 'position', 'updated_at'])
    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'full_name': user.full_name,
            'department': user.department_id,
            'department_name': user.department.name if user.department else None,
            'position': user.position_id,
            'position_title': user.position.title if user.position else None,
        }
    })


# Roles a caller is allowed to assign, keyed by the caller's own role.
# ADMIN (platform) is intentionally never assignable through this endpoint.
_ASSIGNABLE_BY_CALLER = {
    'ADMIN':       {'MANAGER', 'EMPLOYEE', 'ORG_MANAGER', 'ORG_ADMIN'},
    'ORG_MANAGER': {'ORG_ADMIN', 'MANAGER', 'EMPLOYEE'},
    'ORG_ADMIN':   {'MANAGER', 'EMPLOYEE'},
    'MANAGER':     {'EMPLOYEE'},
}


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def change_user_role(request, user_id):
    """
    PATCH /api/frontend/org-users/<id>/role/  Body: { "role": "MANAGER" }

    Restrictions:
      - Caller cannot change their own role
      - Cannot promote anyone to ADMIN through this endpoint
      - Caller can only assign roles inside _ASSIGNABLE_BY_CALLER for their own role
      - Caller cannot manage users whose current role is outside that set
      - Tenant scoping: target must be in caller's org (platform/org-manager bypass)
    """
    new_role = (request.data.get('role') or '').strip().upper()
    if not new_role:
        return Response({'error': 'role is required'}, status=status.HTTP_400_BAD_REQUEST)

    caller = request.user
    allowed = _ASSIGNABLE_BY_CALLER.get(getattr(caller, 'role', None), set())
    if not allowed:
        return Response({'error': 'You are not allowed to change roles'}, status=status.HTTP_403_FORBIDDEN)

    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if target.id == caller.id:
        return Response({'error': 'You cannot change your own role'}, status=status.HTTP_400_BAD_REQUEST)

    if not is_platform_admin(caller) and not caller.is_org_manager_user():
        if get_user_org_id(target) != get_user_org_id(caller):
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if not is_platform_admin(caller) and target.role not in allowed and target.role != new_role:
        return Response({'error': 'You cannot manage users with this role'}, status=status.HTTP_403_FORBIDDEN)

    if new_role not in allowed:
        return Response({'error': f'You cannot assign the {new_role} role'}, status=status.HTTP_403_FORBIDDEN)

    if target.role != new_role:
        target.role = new_role
        target.save(update_fields=['role', 'updated_at'])

    return Response({
        'success': True,
        'user': {
            'id': target.id,
            'full_name': target.full_name,
            'email': target.email,
            'role': target.role,
        }
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def set_user_active(request, user_id):
    """
    PATCH /api/frontend/org-users/<id>/active/  Body: { "is_active": true|false }

    Soft-disable a user so they keep their history but cannot log in.
    """
    is_active = request.data.get('is_active')
    if is_active is None:
        return Response({'error': 'is_active is required'}, status=status.HTTP_400_BAD_REQUEST)
    is_active = bool(is_active)

    caller = request.user
    allowed = _ASSIGNABLE_BY_CALLER.get(getattr(caller, 'role', None), set())
    if not allowed:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if target.id == caller.id:
        return Response({'error': 'You cannot deactivate your own account'}, status=status.HTTP_400_BAD_REQUEST)

    if not is_platform_admin(caller) and not caller.is_org_manager_user():
        if get_user_org_id(target) != get_user_org_id(caller):
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if not is_platform_admin(caller) and target.role not in allowed:
        return Response({'error': 'You cannot manage users with this role'}, status=status.HTTP_403_FORBIDDEN)

    if target.is_active != is_active:
        target.is_active = is_active
        target.save(update_fields=['is_active', 'updated_at'])

    return Response({
        'success': True,
        'user': {
            'id': target.id,
            'full_name': target.full_name,
            'email': target.email,
            'is_active': target.is_active,
        }
    })


@extend_schema(methods=['POST'], request=DepartmentSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def departments_list(request):
    """
    GET: List active departments (ORG_ADMIN sees only their org's depts)
    POST: Create department
    """
    if not _can_manage_org(request.user):
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        departments = Department.objects.filter(is_active=True)
        if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
            org_id = get_user_org_id(request.user) or getattr(request.user, 'managed_organization_id', None)
            if org_id is None:
                departments = departments.none()
            else:
                departments = departments.filter(organization_id=org_id)
        serializer = DepartmentSerializer(departments, many=True)
        return Response({'success': True, 'departments': serializer.data})

    # POST
    data = request.data.copy()
    # Tenant users: auto-set organization to their own org
    if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
        caller_org = get_user_org_id(request.user) or getattr(request.user, 'managed_organization_id', None)
        if not caller_org:
            return Response({'success': False, 'error': 'You are not assigned to any organization'}, status=status.HTTP_403_FORBIDDEN)
        data['organization'] = caller_org

    serializer = DepartmentSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response({'success': True, 'department': serializer.data}, status=status.HTTP_201_CREATED)
    return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['PUT'], request=DepartmentSerializer)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def department_detail(request, pk):
    try:
        department = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response({'success': False, 'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

    if not _can_manage_org(request.user):
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    # Tenant scoping
    if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
        caller_org = get_user_org_id(request.user) or getattr(request.user, 'managed_organization_id', None)
        if department.organization_id != caller_org:
            return Response({'success': False, 'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'success': True, 'department': DepartmentSerializer(department).data})

    if request.method == 'PUT':
        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'department': serializer.data})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        department.is_active = False
        department.save()
        return Response({'success': True, 'message': 'Department deactivated successfully'})


@extend_schema(methods=['POST'], request=JobPositionSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def job_positions_list(request):
    if not _can_manage_org(request.user):
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        positions = JobPosition.objects.filter(is_active=True)
        # Tenant users see global (org IS NULL) + their own org's positions
        if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
            org_id = get_user_org_id(request.user) or getattr(request.user, 'managed_organization_id', None)
            if org_id:
                from django.db.models import Q
                positions = positions.filter(Q(organization_id=org_id) | Q(organization__isnull=True))
            else:
                positions = positions.filter(organization__isnull=True)
        serializer = JobPositionSerializer(positions, many=True)
        return Response({'success': True, 'positions': serializer.data})

    # POST: tenant users always create positions inside their org
    data = request.data.copy()
    if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
        caller_org = get_user_org_id(request.user) or getattr(request.user, 'managed_organization_id', None)
        if not caller_org:
            return Response({'success': False, 'error': 'You are not assigned to any organization'}, status=status.HTTP_403_FORBIDDEN)
        data['organization'] = caller_org

    serializer = JobPositionSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response({'success': True, 'position': serializer.data}, status=status.HTTP_201_CREATED)
    return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['PUT'], request=JobPositionSerializer)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def job_position_detail(request, pk):
    try:
        position = JobPosition.objects.get(pk=pk)
    except JobPosition.DoesNotExist:
        return Response({'success': False, 'error': 'Job position not found'}, status=status.HTTP_404_NOT_FOUND)

    if not _can_manage_org(request.user):
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    # Tenant scoping (allow global positions to be read by anyone, but only mutated by platform)
    if not is_platform_admin(request.user) and not request.user.is_org_manager_user():
        caller_org = get_user_org_id(request.user) or getattr(request.user, 'managed_organization_id', None)
        if position.organization_id is None and request.method != 'GET':
            return Response({'success': False, 'error': 'Cannot modify global positions'}, status=status.HTTP_403_FORBIDDEN)
        if position.organization_id is not None and position.organization_id != caller_org:
            return Response({'success': False, 'error': 'Position not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'success': True, 'position': JobPositionSerializer(position).data})

    if request.method == 'PUT':
        serializer = JobPositionSerializer(position, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'position': serializer.data})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        position.is_active = False
        position.save()
        return Response({'success': True, 'message': 'Job position deactivated successfully'})
