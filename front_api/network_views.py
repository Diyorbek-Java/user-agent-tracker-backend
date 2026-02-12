from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from tracker_api.models import NetworkActivity
from .serializers import NetworkActivityListSerializer
from .views import get_target_user


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def network_activities(request):
    """
    Get paginated list of network activities with filters.
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    - start_date, end_date: date range filter
    - domain: filter by domain
    - browser: filter by browser process name
    - page, page_size: pagination
    """
    user, error = get_target_user(request)
    if error:
        return error

    qs = NetworkActivity.objects.filter(session__user=user)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    domain = request.GET.get('domain')
    browser = request.GET.get('browser')

    if start_date:
        qs = qs.filter(start_time__gte=start_date)
    if end_date:
        qs = qs.filter(start_time__lte=end_date)
    if domain:
        qs = qs.filter(domain__icontains=domain)
    if browser:
        qs = qs.filter(browser_process__icontains=browser)

    qs = qs.order_by('-start_time')

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size

    total = qs.count()
    items = qs[start:end]

    serializer = NetworkActivityListSerializer(items, many=True)

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def network_domain_summary(request):
    """
    Get aggregated browsing time per domain.
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    - days: number of days to include (default: 7)
    """
    user, error = get_target_user(request)
    if error:
        return error

    days = int(request.GET.get('days', 7))
    date_from = timezone.now() - timedelta(days=days)

    qs = NetworkActivity.objects.filter(
        session__user=user,
        start_time__gte=date_from
    )

    domain_stats = qs.values('domain').annotate(
        total_duration=Sum('duration'),
        visit_count=Count('id')
    ).order_by('-total_duration')

    results = []
    for item in domain_stats:
        total_secs = item['total_duration'] or 0
        results.append({
            'domain': item['domain'],
            'total_duration': total_secs,
            'total_duration_hours': round(total_secs / 3600, 2),
            'visit_count': item['visit_count'],
        })

    return Response({
        'days': days,
        'domains': results
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def network_top_sites(request):
    """
    Get top N sites, browser distribution, and total browsing hours.
    Query params:
    - user_id (optional): For ADMIN/MANAGER to view specific user's data
    - days: number of days to include (default: 7)
    - limit: number of top sites to return (default: 10)
    """
    user, error = get_target_user(request)
    if error:
        return error

    days = int(request.GET.get('days', 7))
    limit = int(request.GET.get('limit', 10))
    date_from = timezone.now() - timedelta(days=days)

    qs = NetworkActivity.objects.filter(
        session__user=user,
        start_time__gte=date_from
    )

    # Top sites
    top_sites = qs.values('domain').annotate(
        total_duration=Sum('duration'),
        visit_count=Count('id')
    ).order_by('-total_duration')[:limit]

    top_sites_list = []
    for site in top_sites:
        total_secs = site['total_duration'] or 0
        top_sites_list.append({
            'domain': site['domain'],
            'total_duration': total_secs,
            'total_duration_hours': round(total_secs / 3600, 2),
            'visit_count': site['visit_count'],
        })

    # Browser distribution
    browser_stats = qs.values('browser_process').annotate(
        total_duration=Sum('duration'),
        visit_count=Count('id')
    ).order_by('-total_duration')

    browser_list = []
    for b in browser_stats:
        total_secs = b['total_duration'] or 0
        browser_list.append({
            'browser': b['browser_process'],
            'total_duration': total_secs,
            'total_duration_hours': round(total_secs / 3600, 2),
            'visit_count': b['visit_count'],
        })

    # Total browsing hours
    total_seconds = qs.aggregate(total=Sum('duration'))['total'] or 0

    return Response({
        'days': days,
        'total_browsing_seconds': total_seconds,
        'total_browsing_hours': round(total_seconds / 3600, 2),
        'top_sites': top_sites_list,
        'browser_stats': browser_list
    })
