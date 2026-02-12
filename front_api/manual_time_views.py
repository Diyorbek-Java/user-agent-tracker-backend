from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from tracker_api.models import ManualTimeEntry
from .serializers import ManualTimeEntrySerializer


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
