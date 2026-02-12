from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .views import (
    UserViewSet, SessionViewSet, ActivityViewSet,
    upload_tracking_data, dashboard_stats, user_activity_report,
    merge_metric_token, recent_activities,
    # Productivity dashboard endpoints
    productivity_dashboard, productivity_employees_list,
    productivity_employee_detail, productivity_employee_apps,
    # App category management endpoints
    app_categories_list, app_category_detail, app_categories_suggestions,
    # Working shift endpoints
    working_shifts_by_user, working_shifts_set, working_shift_detail,
)
from .auth_views import (
    login_view, set_password_view, invite_staff_view,
    request_password_reset_view, reset_password_view, current_user_view
)


# Health check endpoint
@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({
        'status': 'ok',
        'message': 'Server is running'
    })


# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'sessions', SessionViewSet)
router.register(r'activities', ActivityViewSet)

urlpatterns = [
    # Health check
    path('health', health_check, name='health-check'),

    # Authentication endpoints
    path('auth/login/', login_view, name='login'),
    path('auth/set-password/', set_password_view, name='set-password'),
    path('auth/request-password-reset/', request_password_reset_view, name='request-password-reset'),
    path('auth/reset-password/', reset_password_view, name='reset-password'),
    path('auth/current-user/', current_user_view, name='current-user'),

    # Admin endpoints
    path('admin/invite-staff/', invite_staff_view, name='invite-staff'),

    # Router URLs
    path('', include(router.urls)),

    # Custom endpoints
    path('upload/', upload_tracking_data, name='upload-tracking-data'),
    path('merge-token/', merge_metric_token, name='merge-metric-token'),
    path('dashboard/', dashboard_stats, name='dashboard-stats'),
    path('users/<int:user_id>/report/', user_activity_report, name='user-report'),
    path('activities/recent/', recent_activities, name='recent-activities'),

    # Productivity Dashboard endpoints
    path('productivity/dashboard/', productivity_dashboard, name='productivity-dashboard'),
    path('productivity/employees/', productivity_employees_list, name='productivity-employees-list'),
    path('productivity/employees/<int:user_id>/', productivity_employee_detail, name='productivity-employee-detail'),
    path('productivity/employees/<int:user_id>/apps/', productivity_employee_apps, name='productivity-employee-apps'),

    # App Category Management endpoints
    path('app-categories/', app_categories_list, name='app-categories-list'),
    path('app-categories/<int:pk>/', app_category_detail, name='app-category-detail'),
    path('app-categories/suggestions/', app_categories_suggestions, name='app-categories-suggestions'),

    # Working Shift endpoints
    path('users/<int:user_id>/working-shifts/', working_shifts_by_user, name='working-shifts-by-user'),
    path('users/<int:user_id>/working-shifts/set/', working_shifts_set, name='working-shifts-set'),
    path('working-shifts/<int:pk>/', working_shift_detail, name='working-shift-detail'),
]
