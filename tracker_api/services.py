"""
Productivity calculation services for the dashboard.
Handles all productivity-related business logic using weighted scoring.
"""
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

from .models import (
    User, Activity, AppCategory, DepartmentAppRule, Session,
    PositionAppWeight, ProductivitySettings, WorkingShift
)


class ProductivityService:
    """Service class for productivity calculations"""

    @staticmethod
    def _get_settings():
        """Get cached productivity settings"""
        return ProductivitySettings.get_settings()

    @staticmethod
    def get_app_category(process_name: str, department=None) -> str:
        """
        Get the category for an application by its process name.
        Kept for backwards compatibility (dashboard summary top apps display).
        """
        if department:
            dept_rule = DepartmentAppRule.objects.filter(
                department=department,
                app_category__process_name=process_name
            ).first()
            if dept_rule:
                return dept_rule.category_override

        app_cat = AppCategory.objects.filter(
            Q(process_name__iexact=process_name) |
            Q(process_name__iexact=process_name.replace('.exe', ''))
        ).first()

        if app_cat:
            return app_cat.category

        return AppCategory.NEUTRAL

    @staticmethod
    def get_app_weight(process_name: str, position=None) -> float:
        """
        Get the productivity weight (0.0-1.0) for an application.
        Resolution order:
        1. Position-specific weight (PositionAppWeight)
        2. Fall back to category-based default (PRODUCTIVE=1.0, NON_PRODUCTIVE=0.0, NEUTRAL=default_weight)
        3. Uncategorized apps use configurable default_weight
        """
        settings = ProductivityService._get_settings()

        # Find the AppCategory for this process
        app_cat = AppCategory.objects.filter(
            Q(process_name__iexact=process_name) |
            Q(process_name__iexact=process_name.replace('.exe', ''))
        ).first()

        if not app_cat:
            return settings.default_weight  # uncategorized apps

        # Check position-specific weight
        if position:
            pos_weight = PositionAppWeight.objects.filter(
                position=position, app_category=app_cat
            ).first()
            if pos_weight:
                return pos_weight.weight

        # Fall back to category-based default
        if app_cat.category == 'PRODUCTIVE':
            return 1.0
        elif app_cat.category == 'NON_PRODUCTIVE':
            return 0.0
        else:
            return settings.default_weight  # NEUTRAL

    @staticmethod
    def _get_shift_filter(user, date_from, date_to):
        """
        Build a Q filter and total shift seconds for a user's working shifts
        within a date range. Only activities within shift hours will be counted.
        Returns: (Q_filter, total_shift_seconds, has_shifts)
        """
        shifts = {s.day_of_week: s for s in WorkingShift.objects.filter(user=user)}
        if not shifts:
            return Q(), 0, False

        shift_q = Q()
        total_shift_seconds = 0

        current_date = date_from.date() if hasattr(date_from, 'date') else date_from
        end_date = date_to.date() if hasattr(date_to, 'date') else date_to

        while current_date <= end_date:
            dow = current_date.weekday()  # 0=Monday
            shift = shifts.get(dow)

            if shift and not shift.is_day_off and shift.start_time and shift.end_time:
                day_shift_start = timezone.make_aware(
                    timezone.datetime.combine(current_date, shift.start_time)
                )
                day_shift_end = timezone.make_aware(
                    timezone.datetime.combine(current_date, shift.end_time)
                )
                # Handle overnight shifts
                if day_shift_end <= day_shift_start:
                    day_shift_end += timedelta(days=1)

                shift_q |= Q(start_time__gte=day_shift_start, start_time__lt=day_shift_end)
                gross_seconds = int((day_shift_end - day_shift_start).total_seconds())
                # Deduct lunch break from working hours
                lunch_seconds = (shift.lunch_break_minutes or 0) * 60
                total_shift_seconds += max(gross_seconds - lunch_seconds, 0)

            current_date += timedelta(days=1)

        return shift_q, total_shift_seconds, True

    @staticmethod
    def get_today_shift_hours(user):
        """Get shift duration in hours for today. Returns 8 as fallback."""
        today_dow = timezone.now().weekday()
        shift = WorkingShift.objects.filter(user=user, day_of_week=today_dow).first()
        if shift and not shift.is_day_off and shift.start_time and shift.end_time:
            return shift.get_duration_hours()
        return 8  # fallback

    @staticmethod
    def calculate_user_productivity(user: User, date_from, date_to, position=None) -> dict:
        """
        Calculate productivity metrics for a single user within a date range.
        Only activities within the user's working shift hours are counted.
        Score = weighted_productive_seconds / total_shift_seconds * 100
        Falls back to total_tracked if no shifts are defined.
        """
        # Build shift-aware filter
        shift_q, total_shift_seconds, has_shifts = ProductivityService._get_shift_filter(
            user, date_from, date_to
        )

        # Base queryset
        base_qs = Activity.objects.filter(
            session__user=user,
            start_time__gte=date_from,
            start_time__lte=date_to
        )

        # Apply shift filter if shifts exist
        if has_shifts and shift_q:
            base_qs = base_qs.filter(shift_q)

        activities = base_qs.values('process_name').annotate(
            total_duration=Sum('duration'),
            count=Count('id')
        )

        weighted_seconds = 0
        total_seconds = 0
        app_durations = defaultdict(lambda: {'duration': 0, 'category': None, 'weight': 0.5, 'count': 0})

        for activity in activities:
            process_name = activity['process_name']
            duration = activity['total_duration'] or 0
            count = activity['count'] or 0
            weight = ProductivityService.get_app_weight(process_name, position)
            # Keep category for display purposes
            category = ProductivityService.get_app_category(process_name, user.department)

            app_durations[process_name]['duration'] = duration
            app_durations[process_name]['category'] = category
            app_durations[process_name]['weight'] = weight
            app_durations[process_name]['count'] = count

            weighted_seconds += duration * weight
            total_seconds += duration

        # Calculate productivity score against shift hours (or tracked hours as fallback)
        denominator = total_shift_seconds if (has_shifts and total_shift_seconds > 0) else total_seconds
        if denominator > 0:
            productivity_score = round((weighted_seconds / denominator) * 100, 1)
        else:
            productivity_score = 0.0

        # Derive approximate productive/neutral/non_productive for backwards compat
        productive_seconds = 0
        neutral_seconds = 0
        non_productive_seconds = 0
        for data in app_durations.values():
            w = data['weight']
            d = data['duration']
            if w >= 0.7:
                productive_seconds += d
            elif w <= 0.3:
                non_productive_seconds += d
            else:
                neutral_seconds += d

        # Get top apps by duration
        top_apps = sorted(
            [
                {
                    'name': name,
                    'category': data['category'],
                    'weight': data['weight'],
                    'hours': round(data['duration'] / 3600, 2),
                    'seconds': data['duration'],
                    'count': data['count']
                }
                for name, data in app_durations.items()
            ],
            key=lambda x: x['seconds'],
            reverse=True
        )[:10]

        return {
            'productive_seconds': productive_seconds,
            'neutral_seconds': neutral_seconds,
            'non_productive_seconds': non_productive_seconds,
            'weighted_productive_seconds': round(weighted_seconds),
            'productive_hours': round(productive_seconds / 3600, 2),
            'neutral_hours': round(neutral_seconds / 3600, 2),
            'non_productive_hours': round(non_productive_seconds / 3600, 2),
            'total_tracked_hours': round(total_seconds / 3600, 2),
            'total_shift_hours': round(total_shift_seconds / 3600, 2) if has_shifts else None,
            'productivity_score': productivity_score,
            'top_apps': top_apps
        }

    @staticmethod
    def get_productivity_status(score: float) -> str:
        """Get status label based on productivity score (uses configurable thresholds)"""
        settings = ProductivityService._get_settings()
        if score >= settings.productive_threshold:
            return 'productive'
        elif score >= settings.needs_improvement_threshold:
            return 'needs_improvement'
        else:
            return 'unproductive'

    @staticmethod
    def get_all_employees_productivity(date_from, date_to) -> list:
        """
        Get productivity data for all employees within a date range.
        Returns list of all employees with their productivity scores.
        """
        users_with_activity = User.objects.filter(
            sessions__start_time__gte=date_from,
            sessions__start_time__lte=date_to,
            is_active=True
        ).distinct()

        employees_data = []

        for user in users_with_activity:
            productivity = ProductivityService.calculate_user_productivity(
                user, date_from, date_to, user.position
            )

            employees_data.append({
                'id': user.id,
                'employee_id': user.employee_id,
                'name': user.full_name,
                'department': user.department.name if user.department else None,
                'department_id': user.department.id if user.department else None,
                'productivity_score': productivity['productivity_score'],
                'productive_hours': productivity['productive_hours'],
                'neutral_hours': productivity['neutral_hours'],
                'non_productive_hours': productivity['non_productive_hours'],
                'total_tracked_hours': productivity['total_tracked_hours'],
                'status': ProductivityService.get_productivity_status(productivity['productivity_score']),
                'top_apps': productivity['top_apps'][:3]
            })

        employees_data.sort(key=lambda x: x['productivity_score'], reverse=True)

        return employees_data

    @staticmethod
    def get_dashboard_summary(date_from, date_to) -> dict:
        """
        Get overall dashboard summary with aggregated stats.
        """
        settings = ProductivityService._get_settings()
        employees_data = ProductivityService.get_all_employees_productivity(date_from, date_to)

        total_employees = len(employees_data)
        productive_employees = sum(1 for e in employees_data if e['status'] == 'productive')

        if total_employees > 0:
            average_productivity = round(
                sum(e['productivity_score'] for e in employees_data) / total_employees, 1
            )
        else:
            average_productivity = 0.0

        # Top performers
        top_performers = [
            {
                'id': e['id'],
                'name': e['name'],
                'score': e['productivity_score'],
                'productive_hours': e['productive_hours']
            }
            for e in employees_data[:5]
            if e['productivity_score'] >= settings.productive_threshold
        ]

        # Needs attention
        needs_attention = []
        for e in reversed(employees_data):
            if e['productivity_score'] < settings.needs_improvement_threshold:
                top_distraction = None
                for app in e.get('top_apps', []):
                    if app.get('weight', 0.5) <= 0.3:
                        top_distraction = app['name']
                        break

                needs_attention.append({
                    'id': e['id'],
                    'name': e['name'],
                    'score': e['productivity_score'],
                    'top_distraction': top_distraction
                })

                if len(needs_attention) >= 5:
                    break

        # Get top apps across all employees
        all_activities = Activity.objects.filter(
            session__user__is_active=True,
            start_time__gte=date_from,
            start_time__lte=date_to
        ).values('process_name').annotate(
            total_duration=Sum('duration')
        ).order_by('-total_duration')

        top_productive_apps = []
        top_unproductive_apps = []

        for activity in all_activities:
            process_name = activity['process_name']
            total_hours = round((activity['total_duration'] or 0) / 3600, 2)
            category = ProductivityService.get_app_category(process_name)

            if category == AppCategory.PRODUCTIVE and len(top_productive_apps) < 5:
                top_productive_apps.append({
                    'name': process_name,
                    'total_hours': total_hours
                })
            elif category == AppCategory.NON_PRODUCTIVE and len(top_unproductive_apps) < 5:
                top_unproductive_apps.append({
                    'name': process_name,
                    'total_hours': total_hours
                })

            if len(top_productive_apps) >= 5 and len(top_unproductive_apps) >= 5:
                break

        return {
            'summary': {
                'total_employees': total_employees,
                'productive_employees': productive_employees,
                'average_productivity': average_productivity
            },
            'top_performers': top_performers,
            'needs_attention': needs_attention,
            'top_productive_apps': top_productive_apps,
            'top_unproductive_apps': top_unproductive_apps
        }

    @staticmethod
    def get_user_daily_trend(user: User, date_from, date_to) -> list:
        """Get daily productivity trend for a user (shift-aware)"""
        trends = []
        current_date = date_from.date() if hasattr(date_from, 'date') else date_from
        end_date = date_to.date() if hasattr(date_to, 'date') else date_to

        while current_date <= end_date:
            day_start = timezone.make_aware(
                timezone.datetime.combine(current_date, timezone.datetime.min.time())
            )
            day_end = timezone.make_aware(
                timezone.datetime.combine(current_date, timezone.datetime.max.time())
            )

            day_productivity = ProductivityService.calculate_user_productivity(
                user, day_start, day_end, user.position
            )

            if day_productivity['total_tracked_hours'] > 0:
                entry = {
                    'date': current_date.isoformat(),
                    'score': day_productivity['productivity_score'],
                    'hours': day_productivity['total_tracked_hours'],
                }
                if day_productivity.get('total_shift_hours') is not None:
                    entry['shift_hours'] = day_productivity['total_shift_hours']
                trends.append(entry)

            current_date += timedelta(days=1)

        return trends

    @staticmethod
    def get_uncategorized_apps(limit: int = 20) -> list:
        """
        Get apps from activity data that are not yet categorized.
        Returns suggestions for categorization.
        """
        categorized = set(
            AppCategory.objects.values_list('process_name', flat=True)
        )

        uncategorized_activities = Activity.objects.exclude(
            process_name__in=categorized
        ).values('process_name').annotate(
            total_duration=Sum('duration'),
            users_count=Count('session__user', distinct=True)
        ).order_by('-total_duration')[:limit]

        suggestions = []
        for activity in uncategorized_activities:
            process_name = activity['process_name']
            display_name = process_name.replace('.exe', '').replace('_', ' ').title()

            suggestions.append({
                'process_name': process_name,
                'display_name': display_name,
                'total_hours': round((activity['total_duration'] or 0) / 3600, 2),
                'users_count': activity['users_count'] or 0
            })

        return suggestions
