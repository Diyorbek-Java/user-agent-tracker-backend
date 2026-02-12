from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from tracker_api.models import User, WorkingShift
from tracker_api.serializers import WorkingShiftSerializer, BulkWorkingShiftSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_shifts(request, user_id):
    """
    GET: Get all working shifts for an employee.
    Admin/Manager can view any user, employees can only view their own.
    """
    requesting_user = request.user

    # Permission check
    if not (requesting_user.is_admin_user() or requesting_user.is_manager_user()):
        if requesting_user.id != user_id:
            return Response(
                {'error': 'You do not have permission to view other users\' shifts'},
                status=status.HTTP_403_FORBIDDEN
            )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    shifts = WorkingShift.objects.filter(user=user)
    serializer = WorkingShiftSerializer(shifts, many=True)

    total_weekly_hours = sum(s.get_duration_hours() for s in shifts)

    return Response({
        'user': {
            'id': user.id,
            'name': user.full_name,
            'employee_id': user.employee_id,
        },
        'total_weekly_hours': round(total_weekly_hours, 2),
        'shifts': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_user_shifts(request, user_id):
    """
    POST: Bulk set working shifts for an employee (Admin/Manager only).
    Replaces existing shifts for the specified days.

    Expected payload:
    {
        "shifts": [
            {"day_of_week": 0, "start_time": "09:00", "end_time": "18:00", "is_day_off": false},
            {"day_of_week": 5, "is_day_off": true}
        ]
    }
    """
    if not (request.user.is_admin_user() or request.user.is_manager_user()):
        return Response(
            {'error': 'Only administrators and managers can set working shifts'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = BulkWorkingShiftSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    shifts_data = serializer.validated_data['shifts']

    # Delete existing shifts for days being set
    days_to_set = [s['day_of_week'] for s in shifts_data]
    WorkingShift.objects.filter(user=user, day_of_week__in=days_to_set).delete()

    # Create new shifts
    created_shifts = []
    for shift_data in shifts_data:
        shift = WorkingShift.objects.create(
            user=user,
            day_of_week=shift_data['day_of_week'],
            start_time=shift_data.get('start_time'),
            end_time=shift_data.get('end_time'),
            is_day_off=shift_data.get('is_day_off', False),
            lunch_break_minutes=shift_data.get('lunch_break_minutes', 60),
        )
        created_shifts.append(shift)

    all_shifts = WorkingShift.objects.filter(user=user)
    total_weekly_hours = sum(s.get_duration_hours() for s in all_shifts)

    return Response({
        'status': 'success',
        'message': f'Set {len(created_shifts)} working shifts for {user.full_name}',
        'total_weekly_hours': round(total_weekly_hours, 2),
        'shifts': WorkingShiftSerializer(all_shifts, many=True).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_users_shifts(request):
    """
    GET: Get shift summary for all employees (Admin/Manager only).
    Returns each user with their total weekly hours and shift count.
    """
    if not (request.user.is_admin_user() or request.user.is_manager_user()):
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    users = User.objects.filter(is_active=True).order_by('full_name')
    results = []

    for user in users:
        shifts = WorkingShift.objects.filter(user=user)
        total_weekly_hours = sum(s.get_duration_hours() for s in shifts)
        working_days = shifts.filter(is_day_off=False).count()
        days_off = shifts.filter(is_day_off=True).count()

        results.append({
            'id': user.id,
            'full_name': user.full_name,
            'employee_id': user.employee_id,
            'department': user.department.name if user.department else None,
            'role': user.role,
            'total_weekly_hours': round(total_weekly_hours, 2),
            'working_days': working_days,
            'days_off': days_off,
            'has_shifts': shifts.exists(),
        })

    return Response(results)
