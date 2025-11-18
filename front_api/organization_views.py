"""
Organization-related API views for Department and JobPosition management
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from tracker_api.models import Department, JobPosition, User
from .serializers import DepartmentSerializer, JobPositionSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def departments_list(request):
    """
    GET: List all active departments
    POST: Create new department (Admin/Manager only)
    """
    if request.method == 'GET':
        departments = Department.objects.filter(is_active=True)
        serializer = DepartmentSerializer(departments, many=True)
        return Response({
            'success': True,
            'departments': serializer.data
        })

    elif request.method == 'POST':
        # Only Admin and Manager can create departments
        if not request.user.is_admin_user() and not request.user.is_manager_user():
            return Response({
                'success': False,
                'error': 'Only administrators and managers can create departments'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'department': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def department_detail(request, pk):
    """
    GET: Retrieve department details
    PUT: Update department (Admin/Manager only)
    DELETE: Soft delete department (Admin only)
    """
    try:
        department = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Department not found'
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = DepartmentSerializer(department)
        return Response({
            'success': True,
            'department': serializer.data
        })

    elif request.method == 'PUT':
        # Only Admin and Manager can update departments
        if not request.user.is_admin_user() and not request.user.is_manager_user():
            return Response({
                'success': False,
                'error': 'Only administrators and managers can update departments'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'department': serializer.data
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Only Admin can delete departments
        if not request.user.is_admin_user():
            return Response({
                'success': False,
                'error': 'Only administrators can delete departments'
            }, status=status.HTTP_403_FORBIDDEN)

        # Soft delete - just mark as inactive
        department.is_active = False
        department.save()

        return Response({
            'success': True,
            'message': 'Department deactivated successfully'
        })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def job_positions_list(request):
    """
    GET: List all active job positions
    POST: Create new job position (Admin/Manager only)
    """
    if request.method == 'GET':
        positions = JobPosition.objects.filter(is_active=True)
        serializer = JobPositionSerializer(positions, many=True)
        return Response({
            'success': True,
            'positions': serializer.data
        })

    elif request.method == 'POST':
        # Only Admin and Manager can create positions
        if not request.user.is_admin_user() and not request.user.is_manager_user():
            return Response({
                'success': False,
                'error': 'Only administrators and managers can create job positions'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = JobPositionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'position': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def job_position_detail(request, pk):
    """
    GET: Retrieve job position details
    PUT: Update job position (Admin/Manager only)
    DELETE: Soft delete job position (Admin only)
    """
    try:
        position = JobPosition.objects.get(pk=pk)
    except JobPosition.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Job position not found'
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = JobPositionSerializer(position)
        return Response({
            'success': True,
            'position': serializer.data
        })

    elif request.method == 'PUT':
        # Only Admin and Manager can update positions
        if not request.user.is_admin_user() and not request.user.is_manager_user():
            return Response({
                'success': False,
                'error': 'Only administrators and managers can update job positions'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = JobPositionSerializer(position, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'position': serializer.data
            })

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Only Admin can delete positions
        if not request.user.is_admin_user():
            return Response({
                'success': False,
                'error': 'Only administrators can delete job positions'
            }, status=status.HTTP_403_FORBIDDEN)

        # Soft delete - just mark as inactive
        position.is_active = False
        position.save()

        return Response({
            'success': True,
            'message': 'Job position deactivated successfully'
        })
