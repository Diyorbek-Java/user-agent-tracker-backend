"""
Organization-related API views for Organization, Department, JobPosition, and User assignment.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from tracker_api.models import Organization, Department, JobPosition, User
from .serializers import OrganizationSerializer, DepartmentSerializer, JobPositionSerializer, UserProfileSerializer


def _can_manage_org(user):
    """Admin, Manager, ORG_MANAGER, or ORG_ADMIN can access org pages."""
    return (user.is_admin_user() or user.is_manager_user()
            or user.is_org_manager_user() or user.is_org_admin_user())


def _can_write_org(user):
    """Only Admin, Manager, ORG_MANAGER can create/edit/delete orgs (not ORG_ADMIN)."""
    return user.is_admin_user() or user.is_manager_user() or user.is_org_manager_user()


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

        orgs = Organization.objects.filter(is_active=True)
        # ORG_ADMIN: only their managed org
        if request.user.is_org_admin_user():
            if request.user.managed_organization_id:
                orgs = orgs.filter(pk=request.user.managed_organization_id)
            else:
                orgs = orgs.none()

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

    # ORG_ADMIN can only see their own org
    if request.user.is_org_admin_user() and request.user.managed_organization_id != org.pk:
        return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

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

    users = User.objects.filter(is_active=True).select_related('department', 'position').order_by('full_name')

    data = [{
        'id': u.id,
        'full_name': u.full_name,
        'employee_id': u.employee_id,
        'role': u.role,
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
        if request.user.is_org_admin_user():
            departments = departments.filter(organization_id=request.user.managed_organization_id)
        serializer = DepartmentSerializer(departments, many=True)
        return Response({'success': True, 'departments': serializer.data})

    # POST
    data = request.data.copy()
    # ORG_ADMIN: auto-set organization to their managed org
    if request.user.is_org_admin_user():
        if not request.user.managed_organization_id:
            return Response({'success': False, 'error': 'You are not assigned to any organization'}, status=status.HTTP_403_FORBIDDEN)
        data['organization'] = request.user.managed_organization_id

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

    # ORG_ADMIN: only their org's departments
    if request.user.is_org_admin_user():
        if department.organization_id != request.user.managed_organization_id:
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

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
        serializer = JobPositionSerializer(positions, many=True)
        return Response({'success': True, 'positions': serializer.data})

    serializer = JobPositionSerializer(data=request.data)
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
