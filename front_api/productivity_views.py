"""
Views for productivity tracking features:
- Application categorization
- Manual time entries
- Enhanced productivity reports
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta

from tracker_api.models import AppCategory, DepartmentAppRule, ManualTimeEntry, Activity
from .serializers import (
    AppCategorySerializer,
    DepartmentAppRuleSerializer,
    ManualTimeEntrySerializer
)


# ============================================================================
# APP CATEGORIZATION ENDPOINTS
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def app_categories_list(request):
    """
    GET: List all app categories
    POST: Create new app category (Admin/Manager only)
    """
    if request.method == 'GET':
        categories = AppCategory.objects.all()
        serializer = AppCategorySerializer(categories, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # Only admin/manager can create
        if not (request.user.is_admin_user() or request.user.is_manager_user()):
            return Response({
                'error': 'Only administrators and managers can create app categories'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = AppCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def app_category_detail(request, pk):
    """
    GET: Get app category details
    PUT: Update app category (Admin/Manager only)
    DELETE: Delete app category (Admin/Manager only)
    """
    try:
        category = AppCategory.objects.get(pk=pk)
    except AppCategory.DoesNotExist:
        return Response({'error': 'App category not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = AppCategorySerializer(category)
        return Response(serializer.data)

    elif request.method in ['PUT', 'DELETE']:
        # Only admin/manager can modify
        if not (request.user.is_admin_user() or request.user.is_manager_user()):
            return Response({
                'error': 'Only administrators and managers can modify app categories'
            }, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'PUT':
            serializer = AppCategorySerializer(category, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            category.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def department_app_rules_list(request):
    """
    GET: List department-specific app rules
    POST: Create new department rule (Admin/Manager only)
    """
    if request.method == 'GET':
        # Filter by department if specified
        department = request.GET.get('department')
        if department:
            rules = DepartmentAppRule.objects.filter(department=department)
        else:
            rules = DepartmentAppRule.objects.all()

        serializer = DepartmentAppRuleSerializer(rules, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # Only admin/manager can create
        if not (request.user.is_admin_user() or request.user.is_manager_user()):
            return Response({
                'error': 'Only administrators and managers can create department rules'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = DepartmentAppRuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def department_app_rule_detail(request, pk):
    """
    GET: Get department rule details
    PUT: Update department rule (Admin/Manager only)
    DELETE: Delete department rule (Admin/Manager only)
    """
    try:
        rule = DepartmentAppRule.objects.get(pk=pk)
    except DepartmentAppRule.DoesNotExist:
        return Response({'error': 'Department rule not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = DepartmentAppRuleSerializer(rule)
        return Response(serializer.data)

    elif request.method in ['PUT', 'DELETE']:
        # Only admin/manager can modify
        if not (request.user.is_admin_user() or request.user.is_manager_user()):
            return Response({
                'error': 'Only administrators and managers can modify department rules'
            }, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'PUT':
            serializer = DepartmentAppRuleSerializer(rule, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            rule.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================
# MANUAL TIME ENTRY ENDPOINTS
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manual_time_entries_list(request):
    """
    GET: List manual time entries for current user (or all users for Admin/Manager)
    POST: Create new manual time entry
    """
    if request.method == 'GET':
        # Admin/Manager can view all users' entries, employees only their own
        if request.user.is_admin_user() or request.user.is_manager_user():
            user_id = request.GET.get('user_id')
            if user_id:
                entries = ManualTimeEntry.objects.filter(user_id=user_id)
            else:
                entries = ManualTimeEntry.objects.all()
        else:
            entries = ManualTimeEntry.objects.filter(user=request.user)

        # Filter by date range if provided
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date:
            entries = entries.filter(start_time__gte=start_date)
        if end_date:
            entries = entries.filter(end_time__lte=end_date)

        serializer = ManualTimeEntrySerializer(entries, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ManualTimeEntrySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def manual_time_entry_detail(request, pk):
    """
    GET: Get manual time entry details
    PUT: Update manual time entry (own entries only, or Admin/Manager can update any)
    DELETE: Delete manual time entry (own entries only, or Admin/Manager can delete any)
    """
    try:
        entry = ManualTimeEntry.objects.get(pk=pk)
    except ManualTimeEntry.DoesNotExist:
        return Response({'error': 'Time entry not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check permissions
    if not (request.user.is_admin_user() or request.user.is_manager_user() or entry.user == request.user):
        return Response({
            'error': 'You do not have permission to access this entry'
        }, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = ManualTimeEntrySerializer(entry)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Only allow updating own entries
        if entry.user != request.user and not (request.user.is_admin_user() or request.user.is_manager_user()):
            return Response({
                'error': 'You can only update your own time entries'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = ManualTimeEntrySerializer(entry, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Only allow deleting own entries
        if entry.user != request.user and not (request.user.is_admin_user() or request.user.is_manager_user()):
            return Response({
                'error': 'You can only delete your own time entries'
            }, status=status.HTTP_403_FORBIDDEN)

        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================
# ENHANCED PRODUCTIVITY REPORT
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enhanced_productivity_report(request):
    """
    Get enhanced productivity report including:
    - Computer time (categorized by app type)
    - Manual time entries
    - Combined productivity score
    """
    # Get target user
    user_id = request.GET.get('user_id')
    if user_id:
        # Check permission
        if not (request.user.is_admin_user() or request.user.is_manager_user()):
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        from tracker_api.models import User
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        target_user = request.user

    # Get date range
    days = int(request.GET.get('days', 7))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get computer activities
    activities = Activity.objects.filter(
        session__user=target_user,
        start_time__gte=start_date
    )

    # Categorize activities
    productive_time = 0
    neutral_time = 0
    non_productive_time = 0

    for activity in activities:
        category = get_app_category_for_user(activity.process_name, target_user.department)
        duration = activity.duration or 0

        if category == AppCategory.PRODUCTIVE:
            productive_time += duration
        elif category == AppCategory.NON_PRODUCTIVE:
            non_productive_time += duration
        else:
            neutral_time += duration

    # Get manual time entries
    manual_entries = ManualTimeEntry.objects.filter(
        user=target_user,
        start_time__gte=start_date
    )

    manual_productive = sum(
        entry.duration_minutes for entry in manual_entries if entry.is_productive
    ) * 60  # Convert to seconds

    manual_non_productive = sum(
        entry.duration_minutes for entry in manual_entries if not entry.is_productive
    ) * 60

    # Calculate totals
    total_computer_time = productive_time + neutral_time + non_productive_time
    total_productive_time = productive_time + manual_productive
    total_time = total_computer_time + manual_productive + manual_non_productive

    # Calculate productivity score
    if total_time > 0:
        productivity_score = round((total_productive_time / total_time) * 100, 2)
    else:
        productivity_score = 0

    return Response({
        'computer_time': {
            'productive_hours': round(productive_time / 3600, 2),
            'neutral_hours': round(neutral_time / 3600, 2),
            'non_productive_hours': round(non_productive_time / 3600, 2),
            'total_hours': round(total_computer_time / 3600, 2),
        },
        'manual_time': {
            'productive_hours': round(manual_productive / 3600, 2),
            'non_productive_hours': round(manual_non_productive / 3600, 2),
            'total_hours': round((manual_productive + manual_non_productive) / 3600, 2),
        },
        'summary': {
            'total_productive_hours': round(total_productive_time / 3600, 2),
            'total_hours': round(total_time / 3600, 2),
            'productivity_score': productivity_score,
        }
    })


def get_app_category_for_user(process_name, department):
    """Helper function to get app category for a user's department"""
    # First check for department-specific rule
    if department:
        dept_rule = DepartmentAppRule.objects.filter(
            department=department,
            app_category__process_name=process_name
        ).first()
        if dept_rule:
            return dept_rule.category_override

    # Fall back to global app category
    app_cat = AppCategory.objects.filter(process_name=process_name).first()
    if app_cat:
        return app_cat.category

    # Default to neutral
    return AppCategory.NEUTRAL
