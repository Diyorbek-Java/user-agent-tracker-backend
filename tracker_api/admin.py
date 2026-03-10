from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Session, Activity, ApplicationUsageStats, NetworkActivity,
    AppCategory, DepartmentAppRule, ManualTimeEntry,
    Organization, Department, JobPosition, PositionAppWeight, ProductivitySettings,
    WorkingShift
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    list_display = ['username', 'employee_id', 'full_name', 'email', 'role', 'department', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'role', 'department', 'date_joined']
    search_fields = ['username', 'employee_id', 'full_name', 'email', 'computer_name']
    ordering = ['full_name']

    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('employee_id', 'full_name', 'email', 'role')
        }),
        ('Job Details', {
            'fields': ('department', 'position', 'computer_name')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Invitation & OTP', {
            'fields': ('is_invited', 'invitation_sent_at', 'otp', 'otp_created_at', 'otp_expires_at', 'otp_used'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'employee_id', 'full_name', 'email', 'password1', 'password2', 'role'),
        }),
    )

    readonly_fields = ['last_login', 'date_joined', 'updated_at', 'otp_created_at', 'otp_expires_at']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'head_of_organization', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'head_of_organization__full_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Department admin"""
    list_display = ['name', 'head_of_department', 'is_active', 'get_employee_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'head_of_department__full_name']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']

    def get_employee_count(self, obj):
        return obj.employees.count()
    get_employee_count.short_description = 'Employees'


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    """Job Position admin"""
    list_display = ['title', 'level', 'is_active', 'get_employee_count', 'created_at']
    list_filter = ['is_active', 'level', 'created_at']
    search_fields = ['title', 'description', 'level']
    ordering = ['title']
    readonly_fields = ['created_at', 'updated_at']

    def get_employee_count(self, obj):
        return obj.employees.count()
    get_employee_count.short_description = 'Employees'


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'start_time', 'end_time', 'is_active', 'get_duration_hours', 'created_at']
    list_filter = ['is_active', 'start_time', 'user']
    search_fields = ['user__username', 'user__employee_id', 'user__full_name']
    date_hierarchy = 'start_time'
    ordering = ['-start_time']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'process_name', 'window_title', 'activity_type', 'start_time', 'get_duration_minutes']
    list_filter = ['activity_type', 'process_name', 'start_time']
    search_fields = ['process_name', 'window_title', 'details']
    date_hierarchy = 'start_time'
    ordering = ['-start_time']


@admin.register(NetworkActivity)
class NetworkActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'domain', 'page_title', 'browser_process', 'start_time', 'get_duration_minutes']
    list_filter = ['browser_process', 'domain', 'start_time']
    search_fields = ['domain', 'url', 'page_title']
    date_hierarchy = 'start_time'
    ordering = ['-start_time']


@admin.register(ApplicationUsageStats)
class ApplicationUsageStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'process_name', 'date', 'get_duration_hours', 'switch_count']
    list_filter = ['date', 'process_name']
    search_fields = ['user__username', 'user__employee_id', 'user__full_name', 'process_name']
    date_hierarchy = 'date'
    ordering = ['-date', '-total_duration']


@admin.register(AppCategory)
class AppCategoryAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'process_name', 'category', 'is_global', 'created_by', 'created_at']
    list_filter = ['category', 'is_global', 'created_at']
    search_fields = ['display_name', 'process_name', 'description']
    ordering = ['display_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DepartmentAppRule)
class DepartmentAppRuleAdmin(admin.ModelAdmin):
    list_display = ['department', 'app_category', 'category_override', 'created_by', 'created_at']
    list_filter = ['department', 'category_override', 'created_at']
    search_fields = ['department', 'app_category__display_name', 'reason']
    ordering = ['department', 'app_category']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ManualTimeEntry)
class ManualTimeEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'start_time', 'end_time', 'duration_minutes', 'is_productive', 'created_at']
    list_filter = ['activity_type', 'is_productive', 'start_time', 'user']
    search_fields = ['user__username', 'user__full_name', 'description']
    date_hierarchy = 'start_time'
    ordering = ['-start_time']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PositionAppWeight)
class PositionAppWeightAdmin(admin.ModelAdmin):
    list_display = ['position', 'app_category', 'weight', 'reason', 'created_by', 'created_at']
    list_filter = ['position', 'weight', 'created_at']
    search_fields = ['position__title', 'app_category__display_name', 'app_category__process_name', 'reason']
    ordering = ['position', 'app_category']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WorkingShift)
class WorkingShiftAdmin(admin.ModelAdmin):
    list_display = ['user', 'day_of_week', 'start_time', 'end_time', 'is_day_off', 'get_duration_hours']
    list_filter = ['day_of_week', 'is_day_off', 'user']
    search_fields = ['user__username', 'user__full_name', 'user__employee_id']
    ordering = ['user', 'day_of_week']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProductivitySettings)
class ProductivitySettingsAdmin(admin.ModelAdmin):
    list_display = ['default_weight', 'productive_threshold', 'needs_improvement_threshold', 'updated_at']
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        # Only allow one instance
        return not ProductivitySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
