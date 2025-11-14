from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Session, Activity, ApplicationUsageStats


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
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
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


@admin.register(ApplicationUsageStats)
class ApplicationUsageStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'process_name', 'date', 'get_duration_hours', 'switch_count']
    list_filter = ['date', 'process_name']
    search_fields = ['user__username', 'user__employee_id', 'user__full_name', 'process_name']
    date_hierarchy = 'date'
    ordering = ['-date', '-total_duration']
