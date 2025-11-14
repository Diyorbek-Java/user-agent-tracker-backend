from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from datetime import datetime, timedelta
from .models import User, Session, Activity, ApplicationUsageStats
from .serializers import (
    UserSerializer, SessionSerializer, ActivitySerializer,
    SessionWithActivitiesSerializer, ApplicationUsageStatsSerializer,
    BulkDataUploadSerializer
)


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
    serializer = BulkDataUploadSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user_id = data.get('user_id')
    metric_token = data.get('metric_token')

    # Either user_id or metric_token must be provided
    if not user_id and not metric_token:
        return Response({
            'error': 'Either user_id or metric_token must be provided'
        }, status=status.HTTP_400_BAD_REQUEST)

    user = None
    if user_id:
        # Get or create user
        user, created = User.objects.get_or_create(
            employee_id=user_id,
            defaults={
                'username': user_id,
                'full_name': user_id,  # Default to user_id, can be updated later
                'email': f"{user_id}@company.com",  # Placeholder email
                'computer_name': data.get('computer_name', '')
            }
        )

        if not created and data.get('computer_name'):
            user.computer_name = data['computer_name']
            user.save()

    # Create or update session
    session_defaults = {
        'end_time': data.get('session_end'),
        'is_active': data.get('session_end') is None
    }

    if user:
        session, session_created = Session.objects.get_or_create(
            user=user,
            start_time=data['session_start'],
            defaults=session_defaults
        )
    else:
        # Metric token session
        session, session_created = Session.objects.get_or_create(
            metric_token=metric_token,
            start_time=data['session_start'],
            defaults=session_defaults
        )

    if not session_created:
        # Update existing session
        if data.get('session_end'):
            session.end_time = data['session_end']
            session.is_active = False
        session.save()

    # Create activities
    activities_created = []
    for activity_data in data.get('activities', []):
        activity = Activity.objects.create(
            session=session,
            metric_token=metric_token if not user else None,
            activity_type=activity_data.get('activity_type', 0),
            window_title=activity_data.get('window_title', ''),
            process_name=activity_data.get('process_name', 'Unknown'),
            details=activity_data.get('details', ''),
            start_time=activity_data['start_time'],
            end_time=activity_data.get('end_time'),
            duration=activity_data.get('duration', 0)
        )
        activities_created.append(activity.id)

    # Calculate session duration
    if session.end_time:
        duration = (session.end_time - session.start_time).total_seconds()
        session.total_duration = int(duration)
        session.save()

    response_data = {
        'status': 'success',
        'session_id': session.id,
        'activities_created': len(activities_created),
    }

    if user:
        response_data['user_id'] = user.id
        response_data['message'] = f'Successfully uploaded data for {user.employee_id}'
    else:
        response_data['metric_token'] = metric_token
        response_data['message'] = f'Successfully uploaded data for metric token'

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
