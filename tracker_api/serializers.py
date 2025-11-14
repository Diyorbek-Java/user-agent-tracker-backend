from rest_framework import serializers
from .models import User, Session, Activity, ApplicationUsageStats


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
