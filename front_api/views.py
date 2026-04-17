from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, Http404
from datetime import timedelta, datetime
import os
from decouple import config
from tracker_api.models import User, Session, Activity, ApplicationUsageStats
from tracker_api.services import ProductivityService
from .serializers import (
    UserProfileSerializer, SessionListSerializer, ActivityListSerializer,
    DashboardStatsSerializer, ApplicationUsageSerializer,
    ActivityTimelineSerializer, ProductivityReportSerializer,
    UserActivitySummarySerializer
)


def get_target_user(request):
    """
    Helper function to determine which user's data to retrieve.
    - For ADMIN/MANAGER: Can specify user_id in query params to view any user's data
    - For EMPLOYEE: Always returns their own data

    Returns: (user_object, error_response)
    - If successful: (User, None)
    - If error: (None, Response)
    """
    requesting_user = request.user
    user_id = request.GET.get('user_id')

    # If no user_id specified, return the requesting user
    if not user_id:
        return requesting_user, None

    # Check if requesting user has permission to view other users' data
    if not requesting_user.is_admin_user() and not requesting_user.is_manager_user():
        return None, Response(
            {'error': 'You do not have permission to view other users\' data'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Admin/Manager can view specified user's data
    try:
        target_user = User.objects.get(id=user_id)
        return target_user, None
    except User.DoesNotExist:
        return None, Response(
            {'error': f'User with id {user_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user profile"""
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update current user profile"""
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_overview(request):
    """
    Get dashboard overview statistics
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    """
    user, error = get_target_user(request)
    if error:
        return error

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Get user's sessions
    sessions = Session.objects.filter(user=user)
    today_sessions = sessions.filter(start_time__gte=today_start)
    week_sessions = sessions.filter(start_time__gte=week_start)

    # Calculate total active time
    total_active_time = sessions.aggregate(
        total=Sum('total_duration')
    )['total'] or 0
    total_active_time = round(total_active_time / 3600, 2)  # Convert to hours

    today_active_time = today_sessions.aggregate(
        total=Sum('total_duration')
    )['total'] or 0
    today_active_time = round(today_active_time / 3600, 2)

    week_active_time = week_sessions.aggregate(
        total=Sum('total_duration')
    )['total'] or 0
    week_active_time = round(week_active_time / 3600, 2)

    # Get total activities
    total_activities = Activity.objects.filter(
        session__user=user
    ).count()

    # Get top applications (last 7 days)
    top_apps = Activity.objects.filter(
        session__user=user,
        start_time__gte=week_start
    ).values('process_name').annotate(
        total_duration=Sum('duration'),
        count=Count('id')
    ).order_by('-total_duration')[:5]

    top_applications = [
        {
            'name': app['process_name'],
            'duration': round(app['total_duration'] / 3600, 2),
            'count': app['count']
        }
        for app in top_apps
    ]

    # Get recent sessions
    recent_sessions = sessions.order_by('-start_time')[:5]

    # Calculate productivity score based on actual shift hours (fallback to 8hr)
    shift_hours = ProductivityService.get_today_shift_hours(user)
    productivity_score = min(round((today_active_time / shift_hours) * 100, 2), 100) if shift_hours > 0 else 0

    data = {
        'total_sessions': sessions.count(),
        'total_active_time': total_active_time,
        'total_activities': total_activities,
        'top_applications': top_applications,
        'recent_sessions': recent_sessions,  # Pass queryset, not serialized data
        'productivity_score': productivity_score,
        'today_active_time': today_active_time,
        'week_active_time': week_active_time,
    }

    serializer = DashboardStatsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_sessions(request):
    """
    Get user's sessions
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    """
    user, error = get_target_user(request)
    if error:
        return error

    sessions = Session.objects.filter(user=user).order_by('-start_time')

    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    start = (page - 1) * page_size
    end = start + page_size

    total = sessions.count()
    sessions_page = sessions[start:end]

    serializer = SessionListSerializer(sessions_page, many=True)

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_activities(request):
    """
    Get user's activities
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    """
    user, error = get_target_user(request)
    if error:
        return error

    # Filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    process_name = request.GET.get('process_name')

    activities = Activity.objects.filter(session__user=user)

    if start_date:
        activities = activities.filter(start_time__gte=start_date)
    if end_date:
        activities = activities.filter(start_time__lte=end_date)
    if process_name:
        activities = activities.filter(process_name__icontains=process_name)

    activities = activities.order_by('-start_time')

    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size

    total = activities.count()
    activities_page = activities[start:end]

    serializer = ActivityListSerializer(activities_page, many=True)

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_timeline(request):
    """
    Get activity timeline grouped by hour
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    - date (optional): Date to view timeline for (ISO format)
    """
    user, error = get_target_user(request)
    if error:
        return error

    date_str = request.GET.get('date', timezone.now().date().isoformat())
    target_date = datetime.fromisoformat(date_str).date()

    # Get activities for the target date
    activities = Activity.objects.filter(
        session__user=user,
        start_time__date=target_date
    )

    # Group by hour
    timeline_data = []
    for hour in range(24):
        hour_activities = activities.filter(start_time__hour=hour)
        total_duration = hour_activities.aggregate(
            total=Sum('duration')
        )['total'] or 0

        timeline_data.append({
            'hour': hour,
            'total_duration': total_duration,
            'activity_count': hour_activities.count()
        })

    serializer = ActivityTimelineSerializer(timeline_data, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def productivity_report(request):
    """
    Get productivity report for a date range
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    - days (optional): Number of days to include in report (default: 7)
    """
    user, error = get_target_user(request)
    if error:
        return error

    # Get date range from query params
    days = int(request.GET.get('days', 7))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    # Get sessions for each day
    report_data = []
    current_date = start_date

    while current_date <= end_date:
        day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))

        day_sessions = Session.objects.filter(
            user=user,
            start_time__range=(day_start, day_end)
        )

        total_active_time = day_sessions.aggregate(
            total=Sum('total_duration')
        )['total'] or 0
        total_active_hours = round(total_active_time / 3600, 2)

        # Get top app for the day
        top_app = Activity.objects.filter(
            session__user=user,
            start_time__range=(day_start, day_end)
        ).values('process_name').annotate(
            total_duration=Sum('duration')
        ).order_by('-total_duration').first()

        top_app_name = top_app['process_name'] if top_app else 'N/A'

        # Calculate productivity score
        productivity_score = min(round((total_active_hours / 8) * 100, 2), 100)

        report_data.append({
            'date': current_date,
            'total_active_hours': total_active_hours,
            'total_sessions': day_sessions.count(),
            'top_app': top_app_name,
            'productivity_score': productivity_score
        })

        current_date += timedelta(days=1)

    serializer = ProductivityReportSerializer(report_data, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def application_usage_stats(request):
    """
    Get application usage statistics
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    - days (optional): Number of days to include (default: 7)
    """
    user, error = get_target_user(request)
    if error:
        return error

    # Get date range
    days = int(request.GET.get('days', 7))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    stats = ApplicationUsageStats.objects.filter(
        user=user,
        date__range=(start_date, end_date)
    ).order_by('-total_duration')

    serializer = ApplicationUsageSerializer(stats, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def day_app_summary(request):
    """
    Return per-app duration totals for a specific employee on a specific day.

    Query params:
    - date      (required) : ISO date, e.g. 2026-02-15
    - user_id   (optional) : For ADMIN/MANAGER to view another user's data

    Response:
    [
      { "process_name": "idea64.exe", "total_seconds": 6342, "session_count": 4 },
      ...
    ]
    sorted by total_seconds descending.
    """
    user, error = get_target_user(request)
    if error:
        return error

    date_str = request.GET.get('date')
    if not date_str:
        return Response({'error': 'date parameter is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    # Aggregate all activities for that user on that exact calendar day
    rows = (
        Activity.objects
        .filter(session__user=user, start_time__date=target_date)
        .values('process_name')
        .annotate(
            total_seconds=Sum('duration'),
            session_count=Count('session', distinct=True)
        )
        .order_by('-total_seconds')
    )

    return Response(list(rows))


# Admin-only endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    """
    Get list of all users for selection (Admin/Manager only)
    Returns simplified user data for dropdown selection
    """
    if not request.user.is_admin_user() and not request.user.is_manager_user():
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    users = User.objects.filter(is_active=True).select_related('department', 'position')

    # Managers only see users in their own department
    if request.user.is_manager_user() and not request.user.is_admin_user():
        users = users.filter(department=request.user.department)

    data = [
        {
            'id': u.id,
            'employee_id': u.employee_id,
            'full_name': u.full_name,
            'email': u.email,
            'role': u.role,
            'department': u.department_id,
            'department_name': u.department.name if u.department else None,
            'position': {'id': u.position_id, 'name': u.position.title} if u.position else None,
        }
        for u in users.order_by('full_name')
    ]

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_users_summary(request):
    """Get summary of all users (Admin/Manager only)"""
    if not request.user.is_admin_user() and not request.user.is_manager_user():
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    users = User.objects.filter(is_active=True, role=User.EMPLOYEE)
    summaries = []

    for user in users:
        sessions = Session.objects.filter(user=user)
        activities = Activity.objects.filter(session__user=user)

        total_active_time = sessions.aggregate(
            total=Sum('total_duration')
        )['total'] or 0
        total_active_hours = round(total_active_time / 3600, 2)

        last_session = sessions.order_by('-start_time').first()
        last_active = last_session.start_time if last_session else None

        # Get top apps
        top_apps = activities.values('process_name').annotate(
            total_duration=Sum('duration')
        ).order_by('-total_duration')[:3]

        top_applications = [
            {
                'name': app['process_name'],
                'duration': round(app['total_duration'] / 3600, 2)
            }
            for app in top_apps
        ]

        summaries.append({
            'user': user,
            'total_sessions': sessions.count(),
            'total_active_hours': total_active_hours,
            'total_activities': activities.count(),
            'last_active': last_active,
            'top_applications': top_applications
        })

    serializer = UserActivitySummarySerializer(summaries, many=True)
    return Response(serializer.data)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail_report(request, user_id):
    """Get detailed report or delete a specific user (Admin/Manager only)"""
    if not request.user.is_admin_user() and not request.user.is_manager_user():
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'DELETE':
        if not request.user.is_admin_user():
            return Response({'error': 'Only admins can delete users'}, status=status.HTTP_403_FORBIDDEN)
        if user.id == request.user.id:
            return Response({'error': 'You cannot delete your own account'}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({'success': True, 'message': 'User deleted successfully'}, status=status.HTTP_200_OK)

    # Get date range
    days = int(request.GET.get('days', 7))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    sessions = Session.objects.filter(
        user=user,
        start_time__gte=start_date
    )

    activities = Activity.objects.filter(
        session__user=user,
        start_time__gte=start_date
    )

    # Statistics
    total_active_time = sessions.aggregate(
        total=Sum('total_duration')
    )['total'] or 0
    total_active_hours = round(total_active_time / 3600, 2)

    # Top applications
    top_apps = activities.values('process_name').annotate(
        total_duration=Sum('duration'),
        count=Count('id')
    ).order_by('-total_duration')[:10]

    top_applications = [
        {
            'name': app['process_name'],
            'duration': round(app['total_duration'] / 3600, 2),
            'count': app['count']
        }
        for app in top_apps
    ]

    # Recent sessions
    recent_sessions = sessions.order_by('-start_time')[:10]

    data = {
        'user': UserProfileSerializer(user).data,
        'total_sessions': sessions.count(),
        'total_active_hours': total_active_hours,
        'total_activities': activities.count(),
        'top_applications': top_applications,
        'recent_sessions': SessionListSerializer(recent_sessions, many=True).data,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def download_agent(request):
    exe_path = config('AGENT_EXE_PATH', default='')
    if not exe_path or not os.path.isfile(exe_path):
        raise Http404('Agent installer not available')
    filename = os.path.basename(exe_path)
    response = FileResponse(open(exe_path, 'rb'), as_attachment=True, filename=filename)
    return response
