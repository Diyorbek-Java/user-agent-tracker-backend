from django.urls import path
from . import views
from . import productivity_views
from . import organization_views
from . import network_views
from . import manual_time_views
from . import shift_views

urlpatterns = [
    # User profile endpoints
    path('profile/', views.user_profile, name='user-profile'),
    path('profile/update/', views.update_profile, name='update-profile'),

    # Dashboard endpoints
    path('dashboard/', views.dashboard_overview, name='dashboard-overview'),
    path('sessions/', views.my_sessions, name='my-sessions'),
    path('activities/', views.my_activities, name='my-activities'),
    path('timeline/', views.activity_timeline, name='activity-timeline'),
    path('productivity/', views.productivity_report, name='productivity-report'),
    path('app-usage/', views.application_usage_stats, name='app-usage-stats'),

    # Admin endpoints
    path('users/list/', views.user_list, name='user-list'),
    path('admin/users/', views.all_users_summary, name='all-users-summary'),
    path('admin/users/<int:user_id>/', views.user_detail_report, name='user-detail-report'),

    # Organization endpoints (Department & Job Position)
    path('departments/', organization_views.departments_list, name='departments-list'),
    path('departments/<int:pk>/', organization_views.department_detail, name='department-detail'),
    path('positions/', organization_views.job_positions_list, name='positions-list'),
    path('positions/<int:pk>/', organization_views.job_position_detail, name='position-detail'),

    # App categorization endpoints
    path('app-categories/', productivity_views.app_categories_list, name='app-categories-list'),
    path('app-categories/<int:pk>/', productivity_views.app_category_detail, name='app-category-detail'),
    path('department-rules/', productivity_views.department_app_rules_list, name='department-rules-list'),
    path('department-rules/<int:pk>/', productivity_views.department_app_rule_detail, name='department-rule-detail'),

    # Manual time entry endpoints
    path('manual-time/', manual_time_views.manual_time_entries_list, name='manual-time-list'),
    path('manual-time/<int:pk>/', manual_time_views.manual_time_entry_detail, name='manual-time-detail'),

    # Enhanced productivity report
    path('enhanced-productivity/', productivity_views.enhanced_productivity_report, name='enhanced-productivity'),

    # Position app weights endpoints
    path('position-weights/', productivity_views.position_weights_list, name='position-weights-list'),
    path('position-weights/<int:pk>/', productivity_views.position_weight_detail, name='position-weight-detail'),

    # Productivity settings endpoint
    path('productivity-settings/', productivity_views.productivity_settings_view, name='productivity-settings'),

    # Working shift endpoints
    path('shifts/', shift_views.all_users_shifts, name='all-users-shifts'),
    path('shifts/<int:user_id>/', shift_views.user_shifts, name='user-shifts'),
    path('shifts/<int:user_id>/set/', shift_views.set_user_shifts, name='set-user-shifts'),

    # Network activity endpoints
    path('network-activities/', network_views.network_activities, name='network-activities'),
    path('network/domains/', network_views.network_domain_summary, name='network-domain-summary'),
    path('network/top-sites/', network_views.network_top_sites, name='network-top-sites'),
]
