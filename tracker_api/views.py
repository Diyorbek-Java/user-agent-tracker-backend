from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from datetime import datetime, timedelta
import logging
from .models import User, Session, Activity, ApplicationUsageStats, AppCategory
from .serializers import (
    UserSerializer, SessionSerializer, ActivitySerializer,
    SessionWithActivitiesSerializer, ApplicationUsageStatsSerializer,
    BulkDataUploadSerializer, AppCategorySerializer, AppCategoryCreateSerializer
)
from .services import ProductivityService
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for managing users/employees"""
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get all sessions for a user"""
        user = self.get_object()
        sessions = Session.objects.filter(user=user)
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get statistics for a user"""
        user = self.get_object()
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)

        stats_query = ApplicationUsageStats.objects.filter(user=user)
        if date_from:
            stats_query = stats_query.filter(date__gte=date_from)
        if date_to:
            stats_query = stats_query.filter(date__lte=date_to)

        stats = ApplicationUsageStatsSerializer(stats_query, many=True)
        return Response(stats.data)


class SessionViewSet(viewsets.ModelViewSet):
    """API endpoint for managing sessions"""
    queryset = Session.objects.all()
    serializer_class = SessionSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SessionWithActivitiesSerializer
        return SessionSerializer

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active sessions"""
        active_sessions = Session.objects.filter(is_active=True)
        serializer = self.get_serializer(active_sessions, many=True)
        return Response(serializer.data)


class ActivityViewSet(viewsets.ModelViewSet):
    """API endpoint for managing activities"""
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer

    def get_queryset(self):
        queryset = Activity.objects.all()
        session_id = self.request.query_params.get('session', None)
        process_name = self.request.query_params.get('process', None)

        if session_id:
            queryset = queryset.filter(session_id=session_id)
        if process_name:
            queryset = queryset.filter(process_name__icontains=process_name)

        return queryset


@api_view(['POST'])
def upload_tracking_data(request):
    """
    Endpoint for C++ client to upload tracking data
    Supports both logged-in users (user_id) and anonymous tracking (metric_token)

    Expected payload:
    {
        "user_id": "employee123",  # optional - for logged-in users
        "metric_token": "uuid-string",  # optional - for anonymous tracking
        "computer_name": "DESKTOP-XYZ",
        "session_start": "2025-11-11T10:00:00Z",
        "session_end": "2025-11-11T18:00:00Z",  # optional
        "activities": [
            {
                "activity_type": 0,
                "window_title": "Visual Studio Code",
                "process_name": "Code.exe",
                "details": "Application: Code.exe, Window: Visual Studio Code",
                "start_time": "2025-11-11T10:05:00Z",
                "end_time": "2025-11-11T10:15:00Z",  # optional
                "duration": 600  # seconds
            }
        ]
    }
    """
    logger.info(f"Received tracking data upload request from {request.META.get('REMOTE_ADDR')}")

    serializer = BulkDataUploadSerializer(data=request.data)

    if not serializer.is_valid():
        logger.error(f"Invalid data in upload request: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user_id = data.get('user_id')
    metric_token = data.get('metric_token')

    logger.info(f"Processing upload for user_id={user_id}, metric_token={metric_token}, activities={len(data.get('activities', []))}")

    # Either user_id or metric_token must be provided
    if not user_id and not metric_token:
        return Response({
            'error': 'Either user_id or metric_token must be provided'
        }, status=status.HTTP_400_BAD_REQUEST)

    user = None
    if user_id:
        # Get or create user - handle race condition with username/employee_id uniqueness
        try:
            user = User.objects.get(employee_id=user_id)
        except User.DoesNotExist:
            # Try to get by username as fallback (since we use user_id as username)
            try:
                user = User.objects.get(username=user_id)
                # Update employee_id if it was missing or different
                if not user.employee_id or user.employee_id != user_id:
                    user.employee_id = user_id
                    user.save(update_fields=['employee_id'])
            except User.DoesNotExist:
                # Create new user
                try:
                    user = User.objects.create(
                        employee_id=user_id,
                        username=user_id,
                        full_name=user_id,  # Default to user_id, can be updated later
                        email=f"{user_id}@company.com",  # Placeholder email
                        computer_name=data.get('computer_name', '')
                    )
                except IntegrityError:
                    # Race condition: another request created the user, fetch it
                    user = User.objects.get(Q(employee_id=user_id) | Q(username=user_id))

        if data.get('computer_name') and user.computer_name != data.get('computer_name'):
            user.computer_name = data['computer_name']
            user.save(update_fields=['computer_name'])

    # Helper function to get or create daily session for a specific date
    def get_daily_session(activity_date, user_obj, metric_tok):
        day_start = timezone.make_aware(datetime.combine(activity_date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(activity_date, datetime.max.time()))

        session_defaults = {
            'end_time': day_end,
            'is_active': True
        }

        if user_obj:
            sess, _ = Session.objects.get_or_create(
                user=user_obj,
                start_time=day_start,
                defaults=session_defaults
            )
        else:
            sess, _ = Session.objects.get_or_create(
                metric_token=metric_tok,
                start_time=day_start,
                defaults=session_defaults
            )
        return sess

    # Create activities - group by date from activity's start_time
    activities_created = []
    sessions_updated = {}  # Track sessions and their activity durations

    for activity_data in data.get('activities', []):
        # Get the activity's start time
        activity_start = activity_data['start_time']
        if isinstance(activity_start, str):
            activity_start = parse_datetime(activity_start)

        # Get the date from the activity's start_time (handles midnight correctly)
        activity_date = activity_start.date()

        # Get or create the daily session for this activity's date
        session = get_daily_session(activity_date, user, metric_token)

        # Track session for duration update
        if session.id not in sessions_updated:
            sessions_updated[session.id] = {'session': session, 'duration': 0}

        # Calculate duration if not provided
        duration = activity_data.get('duration', 0)
        if duration == 0 and activity_data.get('end_time'):
            start = activity_start
            end = activity_data['end_time']

            if isinstance(end, str):
                end = parse_datetime(end)

            if start and end:
                duration = int((end - start).total_seconds())

        activity = Activity.objects.create(
            session=session,
            metric_token=metric_token if not user else None,
            activity_type=activity_data.get('activity_type', 0),
            window_title=activity_data.get('window_title', ''),
            process_name=activity_data.get('process_name', 'Unknown'),
            details=activity_data.get('details', ''),
            start_time=activity_start,
            end_time=activity_data.get('end_time'),
            duration=duration
        )
        activities_created.append(activity.id)
        sessions_updated[session.id]['duration'] += duration

    # Update durations for all affected sessions
    for session_data in sessions_updated.values():
        session = session_data['session']
        activity_duration = session_data['duration']

        # Aggregate total duration from all activities in this session
        total_duration = Activity.objects.filter(session=session).aggregate(
            total=Sum('duration')
        )['total'] or 0

        session.total_duration = total_duration
        session.save(update_fields=['total_duration'])

    # Log successful upload
    session_ids = list(sessions_updated.keys())
    logger.info(f"Successfully created {len(activities_created)} activities across {len(session_ids)} session(s)")
    for sid, sdata in sessions_updated.items():
        logger.info(f"Session {sid} total duration: {sdata['session'].total_duration} seconds")

    # Calculate total duration across all sessions
    total_duration_all = sum(s['session'].total_duration for s in sessions_updated.values())

    response_data = {
        'status': 'success',
        'session_ids': session_ids,
        'sessions_count': len(session_ids),
        'activities_created': len(activities_created),
        'total_duration_seconds': total_duration_all,
        'total_duration_minutes': round(total_duration_all / 60, 2),
    }

    if user:
        response_data['user_id'] = user.id
        response_data['employee_id'] = user.employee_id
        response_data['message'] = f'Successfully uploaded {len(activities_created)} activities for {user.employee_id} across {len(session_ids)} daily session(s)'
        logger.info(f"Upload for user: {user.employee_id}")
    else:
        response_data['metric_token'] = metric_token
        response_data['message'] = f'Successfully uploaded {len(activities_created)} activities across {len(session_ids)} daily session(s)'
        logger.info(f"Upload for metric token: {metric_token[:8]}...")

    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def dashboard_stats(request):
    """
    Get dashboard statistics
    Returns overall stats for the monitoring system
    """
    # Get date range from query params
    days = int(request.query_params.get('days', 7))
    date_from = timezone.now() - timedelta(days=days)

    # Active users
    active_users = User.objects.filter(is_active=True).count()

    # Active sessions
    active_sessions = Session.objects.filter(is_active=True).count()

    # Total sessions in date range
    total_sessions = Session.objects.filter(start_time__gte=date_from).count()

    # Total activities in date range
    total_activities = Activity.objects.filter(start_time__gte=date_from).count()

    # Top applications
    top_apps = Activity.objects.filter(
        start_time__gte=date_from
    ).values('process_name').annotate(
        total_count=Count('id'),
        total_duration=Sum('duration')
    ).order_by('-total_duration')[:10]

    return Response({
        'active_users': active_users,
        'active_sessions': active_sessions,
        'total_sessions': total_sessions,
        'total_activities': total_activities,
        'date_range_days': days,
        'top_applications': list(top_apps)
    })


@api_view(['GET'])
def user_activity_report(request, user_id):
    """
    Get detailed activity report for a user
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get date range
    date_from = request.query_params.get('date_from', None)
    date_to = request.query_params.get('date_to', None)

    sessions_query = Session.objects.filter(user=user)
    if date_from:
        sessions_query = sessions_query.filter(start_time__gte=date_from)
    if date_to:
        sessions_query = sessions_query.filter(start_time__lte=date_to)

    # Session statistics
    sessions = sessions_query
    total_time_seconds = sessions.aggregate(total=Sum('total_duration'))['total'] or 0
    total_time_hours = round(total_time_seconds / 3600, 2)

    # Application usage
    activities = Activity.objects.filter(session__in=sessions)
    app_usage = activities.values('process_name').annotate(
        count=Count('id'),
        total_time=Sum('duration')
    ).order_by('-total_time')

    return Response({
        'user': UserSerializer(user).data,
        'total_sessions': sessions.count(),
        'total_time_hours': total_time_hours,
        'application_usage': list(app_usage),
        'sessions': SessionSerializer(sessions, many=True).data
    })


@api_view(['POST'])
def merge_metric_token(request):
    """
    Merge metric token activities with user account on login

    Expected payload:
    {
        "metric_token": "uuid-string",
        "user_id": "employee123"
    }

    Transfers all sessions and activities from metric_token to the user
    """
    metric_token = request.data.get('metric_token')
    user_id = request.data.get('user_id')

    if not metric_token or not user_id:
        return Response({
            'error': 'Both metric_token and user_id are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get user
    try:
        user = User.objects.get(employee_id=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Find all sessions with metric_token
    metric_sessions = Session.objects.filter(metric_token=metric_token)
    sessions_updated = metric_sessions.count()

    # Find all activities with metric_token (including those without sessions)
    metric_activities = Activity.objects.filter(metric_token=metric_token)
    activities_updated = metric_activities.count()

    logger.info(f"Merging {sessions_updated} sessions and {activities_updated} activities from token {metric_token[:8]}... to user {user.employee_id}")

    # Transfer sessions to user
    metric_sessions.update(user=user, metric_token=None)

    # Transfer activities to user sessions
    # For activities with sessions, clear metric_token (they're now linked via session)
    # For activities without sessions, we keep them but clear metric_token
    metric_activities.update(metric_token=None)

    return Response({
        'status': 'success',
        'message': f'Successfully merged {sessions_updated} sessions and {activities_updated} activities',
        'sessions_merged': sessions_updated,
        'activities_merged': activities_updated,
        'user_id': user.id,
        'employee_id': user.employee_id
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def recent_activities(request):
    """
    Get recent activities for debugging
    Query params:
    - limit: number of activities to return (default: 50)
    - user_id: filter by user employee_id
    - metric_token: filter by metric token
    - process: filter by process name
    """
    limit = int(request.query_params.get('limit', 50))
    user_id = request.query_params.get('user_id')
    metric_token = request.query_params.get('metric_token')
    process = request.query_params.get('process')

    activities = Activity.objects.all()

    if user_id:
        activities = activities.filter(session__user__employee_id=user_id)
    if metric_token:
        activities = activities.filter(metric_token=metric_token)
    if process:
        activities = activities.filter(process_name__icontains=process)

    activities = activities.order_by('-start_time')[:limit]

    return Response({
        'count': activities.count(),
        'activities': ActivitySerializer(activities, many=True).data
    })


# ============================================================================
# PRODUCTIVITY DASHBOARD ENDPOINTS
# ============================================================================

@api_view(['GET'])
def productivity_dashboard(request):
    """
    Get overall productivity dashboard stats + employee rankings.
    Query params:
    - days: number of days to include (default: 7)
    """
    days = int(request.query_params.get('days', 7))
    date_to = timezone.now()
    date_from = date_to - timedelta(days=days)

    dashboard_data = ProductivityService.get_dashboard_summary(date_from, date_to)

    return Response({
        'period': {
            'from': date_from.date().isoformat(),
            'to': date_to.date().isoformat()
        },
        **dashboard_data
    })


@api_view(['GET'])
def productivity_employees_list(request):
    """
    Get all employees with their productivity scores.
    Query params:
    - days: number of days to include (default: 7)
    - department: filter by department ID
    - status: filter by productivity status (productive, needs_improvement, unproductive)
    """
    days = int(request.query_params.get('days', 7))
    department = request.query_params.get('department')
    status_filter = request.query_params.get('status')

    date_to = timezone.now()
    date_from = date_to - timedelta(days=days)

    employees_data = ProductivityService.get_all_employees_productivity(date_from, date_to)

    # Apply filters
    if department:
        employees_data = [e for e in employees_data if str(e.get('department_id')) == department]

    if status_filter:
        employees_data = [e for e in employees_data if e.get('status') == status_filter]

    return Response({
        'period': {
            'from': date_from.date().isoformat(),
            'to': date_to.date().isoformat()
        },
        'employees': employees_data
    })


@api_view(['GET'])
def productivity_employee_detail(request, user_id):
    """
    Get detailed productivity data for a single employee.
    Query params:
    - days: number of days to include (default: 7)
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    days = int(request.query_params.get('days', 7))
    date_to = timezone.now()
    date_from = date_to - timedelta(days=days)

    productivity = ProductivityService.calculate_user_productivity(user, date_from, date_to)
    daily_trend = ProductivityService.get_user_daily_trend(user, date_from, date_to)

    total_hours = productivity['total_tracked_hours']
    productive_pct = round((productivity['productive_hours'] / total_hours * 100), 1) if total_hours > 0 else 0
    neutral_pct = round((productivity['neutral_hours'] / total_hours * 100), 1) if total_hours > 0 else 0
    non_productive_pct = round((productivity['non_productive_hours'] / total_hours * 100), 1) if total_hours > 0 else 0

    return Response({
        'user': {
            'id': user.id,
            'name': user.full_name,
            'employee_id': user.employee_id,
            'department': user.department.name if user.department else None
        },
        'period': {
            'from': date_from.date().isoformat(),
            'to': date_to.date().isoformat()
        },
        'productivity_score': productivity['productivity_score'],
        'status': ProductivityService.get_productivity_status(productivity['productivity_score']),
        'breakdown': {
            'productive': {
                'hours': productivity['productive_hours'],
                'percentage': productive_pct
            },
            'neutral': {
                'hours': productivity['neutral_hours'],
                'percentage': neutral_pct
            },
            'non_productive': {
                'hours': productivity['non_productive_hours'],
                'percentage': non_productive_pct
            }
        },
        'total_tracked_hours': total_hours,
        'daily_trend': daily_trend,
        'top_apps': productivity['top_apps']
    })


@api_view(['GET'])
def productivity_employee_apps(request, user_id):
    """
    Get top apps usage for an employee.
    Query params:
    - days: number of days to include (default: 7)
    - category: filter by category (PRODUCTIVE, NEUTRAL, NON_PRODUCTIVE)
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    days = int(request.query_params.get('days', 7))
    category_filter = request.query_params.get('category')

    date_to = timezone.now()
    date_from = date_to - timedelta(days=days)

    productivity = ProductivityService.calculate_user_productivity(user, date_from, date_to)
    apps = productivity['top_apps']

    if category_filter:
        apps = [app for app in apps if app['category'] == category_filter]

    return Response({
        'user': {
            'id': user.id,
            'name': user.full_name
        },
        'period': {
            'from': date_from.date().isoformat(),
            'to': date_to.date().isoformat()
        },
        'apps': apps
    })


# ============================================================================
# APP CATEGORY MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['GET', 'POST'])
def app_categories_list(request):
    """
    GET: List all app categories
    POST: Create new app category
    """
    if request.method == 'GET':
        category_filter = request.query_params.get('category')
        categories = AppCategory.objects.all()

        if category_filter:
            categories = categories.filter(category=category_filter)

        serializer = AppCategorySerializer(categories, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = AppCategoryCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Set created_by if user is authenticated
            created_by = request.user if request.user.is_authenticated else None
            category = serializer.save(created_by=created_by, is_global=True)
            return Response(
                AppCategorySerializer(category).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def app_category_detail(request, pk):
    """
    GET: Get app category details
    PUT: Update app category
    DELETE: Delete app category
    """
    try:
        category = AppCategory.objects.get(pk=pk)
    except AppCategory.DoesNotExist:
        return Response({'error': 'App category not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = AppCategorySerializer(category)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = AppCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def app_categories_suggestions(request):
    """
    Get suggestions for uncategorized apps based on activity data.
    Query params:
    - limit: maximum number of suggestions (default: 20)
    """
    limit = int(request.query_params.get('limit', 20))
    suggestions = ProductivityService.get_uncategorized_apps(limit=limit)

    return Response({
        'uncategorized_apps': suggestions
    })
