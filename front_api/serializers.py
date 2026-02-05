from rest_framework import serializers
from tracker_api.models import (
    User, Session, Activity, ApplicationUsageStats,
    AppCategory, DepartmentAppRule, ManualTimeEntry,
    Department, JobPosition, PositionAppWeight, ProductivitySettings
)
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""
    head_name = serializers.CharField(source='head_of_department.full_name', read_only=True)
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'head_of_department', 'head_name',
                  'is_active', 'employee_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_employee_count(self, obj):
        return obj.employees.count()


class JobPositionSerializer(serializers.ModelSerializer):
    """Serializer for JobPosition model"""
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = JobPosition
        fields = ['id', 'title', 'description', 'level', 'is_active',
                  'employee_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_employee_count(self, obj):
        return obj.employees.count()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""
    is_admin = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'employee_id',
                  'role', 'department', 'department_name', 'position', 'position_title',
                  'computer_name', 'is_admin', 'last_login', 'date_joined']
        read_only_fields = ['id', 'is_admin', 'last_login', 'date_joined']

    def get_is_admin(self, obj):
        return obj.is_admin_user()


class SessionListSerializer(serializers.ModelSerializer):
    """Serializer for session list"""
    duration_hours = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Session
        fields = ['id', 'username', 'start_time', 'end_time', 'is_active',
                  'total_duration', 'duration_hours']

    def get_duration_hours(self, obj):
        return obj.get_duration_hours()


class ActivityListSerializer(serializers.ModelSerializer):
    """Serializer for activity list"""
    duration_minutes = serializers.SerializerMethodField()
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)

    class Meta:
        model = Activity
        fields = ['id', 'activity_type', 'activity_type_display', 'window_title',
                  'process_name', 'start_time', 'end_time', 'duration', 'duration_minutes']

    def get_duration_minutes(self, obj):
        return obj.get_duration_minutes()


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_sessions = serializers.IntegerField()
    total_active_time = serializers.FloatField()
    total_activities = serializers.IntegerField()
    top_applications = serializers.ListField()
    recent_sessions = SessionListSerializer(many=True)
    productivity_score = serializers.FloatField()
    today_active_time = serializers.FloatField()
    week_active_time = serializers.FloatField()


class ApplicationUsageSerializer(serializers.ModelSerializer):
    """Serializer for application usage statistics"""
    duration_hours = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ApplicationUsageStats
        fields = ['id', 'username', 'process_name', 'date', 'total_duration',
                  'duration_hours', 'switch_count']

    def get_duration_hours(self, obj):
        return obj.get_duration_hours()


class ActivityTimelineSerializer(serializers.Serializer):
    """Serializer for activity timeline data"""
    hour = serializers.IntegerField()
    total_duration = serializers.IntegerField()
    activity_count = serializers.IntegerField()


class ProductivityReportSerializer(serializers.Serializer):
    """Serializer for productivity report"""
    date = serializers.DateField()
    total_active_hours = serializers.FloatField()
    total_sessions = serializers.IntegerField()
    top_app = serializers.CharField()
    productivity_score = serializers.FloatField()


class UserActivitySummarySerializer(serializers.Serializer):
    """Serializer for user activity summary"""
    user = UserProfileSerializer()
    total_sessions = serializers.IntegerField()
    total_active_hours = serializers.FloatField()
    total_activities = serializers.IntegerField()
    last_active = serializers.DateTimeField()
    top_applications = serializers.ListField()


class AppCategorySerializer(serializers.ModelSerializer):
    """Serializer for application category"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = AppCategory
        fields = ['id', 'process_name', 'display_name', 'category', 'description',
                  'is_global', 'created_at', 'updated_at', 'created_by', 'created_by_name']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class DepartmentAppRuleSerializer(serializers.ModelSerializer):
    """Serializer for department-specific app rules"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    app_display_name = serializers.CharField(source='app_category.display_name', read_only=True)
    app_process_name = serializers.CharField(source='app_category.process_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = DepartmentAppRule
        fields = ['id', 'department', 'department_name', 'app_category', 'app_display_name', 'app_process_name',
                  'category_override', 'reason', 'created_at', 'updated_at', 'created_by', 'created_by_name']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class ManualTimeEntrySerializer(serializers.ModelSerializer):
    """Serializer for manual time entries"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)

    class Meta:
        model = ManualTimeEntry
        fields = ['id', 'user', 'user_name', 'activity_type', 'activity_type_display',
                  'description', 'start_time', 'end_time', 'duration_minutes',
                  'is_productive', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def create(self, validated_data):
        # Auto-set user from request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PositionAppWeightSerializer(serializers.ModelSerializer):
    """Serializer for position-specific app productivity weights"""
    position_title = serializers.CharField(source='position.title', read_only=True)
    app_display_name = serializers.CharField(source='app_category.display_name', read_only=True)
    app_process_name = serializers.CharField(source='app_category.process_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = PositionAppWeight
        fields = ['id', 'position', 'position_title', 'app_category', 'app_display_name',
                  'app_process_name', 'weight', 'reason', 'created_at', 'updated_at',
                  'created_by', 'created_by_name']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class ProductivitySettingsSerializer(serializers.ModelSerializer):
    """Serializer for global productivity settings (singleton)"""

    class Meta:
        model = ProductivitySettings
        fields = ['default_weight', 'productive_threshold', 'needs_improvement_threshold', 'updated_at']
        read_only_fields = ['updated_at']
