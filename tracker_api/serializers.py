from rest_framework import serializers
from .models import User, Session, Activity, ApplicationUsageStats, AppCategory, WorkingShift, NetworkActivity


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'employee_id', 'full_name', 'email', 'role', 'department',
            'position', 'computer_name', 'is_active', 'date_joined', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'updated_at']
        extra_kwargs = {'password': {'write_only': True}}


class ActivitySerializer(serializers.ModelSerializer):
    """Serializer for Activity model"""
    duration_minutes = serializers.ReadOnlyField(source='get_duration_minutes')

    class Meta:
        model = Activity
        fields = [
            'id', 'session', 'metric_token', 'activity_type', 'window_title', 'process_name',
            'details', 'start_time', 'end_time', 'duration', 'duration_minutes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model"""
    duration_hours = serializers.ReadOnlyField(source='get_duration_hours')
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)

    class Meta:
        model = Session
        fields = [
            'id', 'user', 'user_name', 'username', 'metric_token', 'start_time', 'end_time',
            'is_active', 'total_duration', 'duration_hours', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SessionWithActivitiesSerializer(serializers.ModelSerializer):
    """Session serializer with nested activities"""
    activities = ActivitySerializer(many=True, read_only=True)
    duration_hours = serializers.ReadOnlyField(source='get_duration_hours')
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)

    class Meta:
        model = Session
        fields = [
            'id', 'user', 'user_name', 'username', 'metric_token', 'start_time', 'end_time',
            'is_active', 'total_duration', 'duration_hours', 'activities', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ApplicationUsageStatsSerializer(serializers.ModelSerializer):
    """Serializer for ApplicationUsageStats model"""
    duration_hours = serializers.ReadOnlyField(source='get_duration_hours')
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ApplicationUsageStats
        fields = [
            'id', 'user', 'user_name', 'username', 'process_name', 'date',
            'total_duration', 'duration_hours', 'switch_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NetworkActivitySerializer(serializers.ModelSerializer):
    """Serializer for NetworkActivity model"""
    duration_minutes = serializers.ReadOnlyField(source='get_duration_minutes')

    class Meta:
        model = NetworkActivity
        fields = [
            'id', 'session', 'metric_token', 'url', 'domain', 'page_title',
            'browser_process', 'start_time', 'end_time', 'duration',
            'duration_minutes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BulkDataUploadSerializer(serializers.Serializer):
    """Serializer for bulk data upload from C++ client"""
    user_id = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    metric_token = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    computer_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    session_start = serializers.DateTimeField()
    session_end = serializers.DateTimeField(required=False, allow_null=True)
    activities = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    network_activities = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True,
        required=False,
        default=list
    )

    def validate(self, data):
        """Validate that either user_id or metric_token is provided"""
        if not data.get('user_id') and not data.get('metric_token'):
            raise serializers.ValidationError("Either user_id or metric_token must be provided")
        return data

    def validate_activities(self, value):
        """Validate activities data"""
        for activity in value:
            if 'process_name' not in activity:
                raise serializers.ValidationError("Each activity must have a process_name")
            if 'start_time' not in activity:
                raise serializers.ValidationError("Each activity must have a start_time")
        return value

    def validate_network_activities(self, value):
        """Validate network activities data"""
        for item in value:
            if 'domain' not in item:
                raise serializers.ValidationError("Each network activity must have a domain")
            if 'start_time' not in item:
                raise serializers.ValidationError("Each network activity must have a start_time")
            if 'browser_process' not in item:
                raise serializers.ValidationError("Each network activity must have a browser_process")
        return value


class AppCategorySerializer(serializers.ModelSerializer):
    """Serializer for AppCategory model"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = AppCategory
        fields = [
            'id', 'process_name', 'display_name', 'category', 'description',
            'is_global', 'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class AppCategoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AppCategory"""

    class Meta:
        model = AppCategory
        fields = ['process_name', 'display_name', 'category', 'description']

    def validate_process_name(self, value):
        """Check for duplicate process names (case-insensitive)"""
        if AppCategory.objects.filter(process_name__iexact=value).exists():
            raise serializers.ValidationError("An app category with this process name already exists.")
        return value


class WorkingShiftSerializer(serializers.ModelSerializer):
    """Serializer for WorkingShift model"""
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    duration_hours = serializers.ReadOnlyField(source='get_duration_hours')
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = WorkingShift
        fields = [
            'id', 'user', 'user_name', 'day_of_week', 'day_name',
            'start_time', 'end_time', 'is_day_off', 'lunch_break_minutes',
            'duration_hours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        is_day_off = data.get('is_day_off', False)
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if not is_day_off:
            if not start_time or not end_time:
                raise serializers.ValidationError(
                    "start_time and end_time are required when is_day_off is False."
                )
        return data


class SingleShiftInputSerializer(serializers.Serializer):
    """Input schema for a single day shift entry"""
    day_of_week = serializers.IntegerField(
        min_value=0, max_value=6,
        help_text="0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday"
    )
    start_time = serializers.TimeField(
        required=False, allow_null=True,
        help_text="Work start time in HH:MM format, e.g. 09:00"
    )
    end_time = serializers.TimeField(
        required=False, allow_null=True,
        help_text="Work end time in HH:MM format, e.g. 18:00"
    )
    is_day_off = serializers.BooleanField(
        default=False,
        help_text="Set to true for days off (weekend, holiday). start_time/end_time not required."
    )
    lunch_break_minutes = serializers.IntegerField(
        default=60, required=False, min_value=0,
        help_text="Lunch break duration in minutes (default 60)"
    )

    def validate(self, data):
        if not data.get('is_day_off', False):
            if not data.get('start_time') or not data.get('end_time'):
                raise serializers.ValidationError(
                    "start_time and end_time are required when is_day_off is false."
                )
        return data


class BulkWorkingShiftSerializer(serializers.Serializer):
    """Serializer for bulk-setting all working shifts for a user at once"""
    shifts = serializers.ListField(
        child=SingleShiftInputSerializer(),
        min_length=1,
        max_length=7,
        help_text="List of shift entries. You can submit 1-7 days. Any day not included is left unchanged."
    )

    def validate_shifts(self, value):
        days_seen = set()
        for shift in value:
            day = shift.get('day_of_week')
            if day in days_seen:
                raise serializers.ValidationError(f"Duplicate day_of_week: {day}.")
            days_seen.add(day)
        return value
