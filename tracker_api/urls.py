from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .views import (
    UserViewSet, SessionViewSet, ActivityViewSet,
    upload_tracking_data, dashboard_stats, user_activity_report,
    merge_metric_token
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
]
