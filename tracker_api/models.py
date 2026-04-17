from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import secrets
import string


class Organization(models.Model):
    """
    Top-level organization entity.
    An organization has a head (one user) and contains multiple departments.
    """
    name = models.CharField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    head_of_organization = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organizations_headed',
        help_text="Head / CEO of this organization"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Organizations'

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Department/Team model
    Examples: Sales, Engineering, HR, Marketing, Finance, etc.
    """
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True, help_text="Department description and responsibilities")
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments',
        help_text="Organization this department belongs to"
    )
    head_of_department = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments_headed',
        help_text="Manager/Head of this department"
    )
    is_active = models.BooleanField(default=True, help_text="Is this department currently active?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name


class JobPosition(models.Model):
    """
    Job Position/Title model
    Examples: Senior Developer, Sales Manager, HR Coordinator, etc.
    """
    title = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True, help_text="Position description and responsibilities")
    level = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Job level (Junior, Mid, Senior, Lead, Manager, etc.)"
    )
    is_active = models.BooleanField(default=True, help_text="Is this position currently available?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'Job Positions'

    def __str__(self):
        return self.title


class User(AbstractUser):
    """Custom User model combining authentication and employee information"""

    # Role choices
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    EMPLOYEE = 'EMPLOYEE'
    ORG_MANAGER = 'ORG_MANAGER'
    ORG_ADMIN = 'ORG_ADMIN'

    ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (MANAGER, 'Manager'),
        (EMPLOYEE, 'Employee'),
        (ORG_MANAGER, 'Organization Manager'),
        (ORG_ADMIN, 'Organization Admin'),
    ]

    # User role and employee details
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)
    employee_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique employee identifier")
    full_name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        help_text="Employee's department"
    )
    position = models.ForeignKey(
        JobPosition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        help_text="Employee's job position"
    )
    managed_organization = models.ForeignKey(
        'Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_users',
        help_text="Organization this user administers (only for ADMINISTRATION role)"
    )
    computer_name = models.CharField(max_length=100, blank=True, null=True)

    # Invitation system
    is_invited = models.BooleanField(default=False, help_text="Has invitation been sent?")
    invitation_sent_at = models.DateTimeField(null=True, blank=True)

    # One-Time Password for first login
    otp = models.CharField(max_length=20, blank=True, null=True, help_text="One-time password for first login")
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_used = models.BooleanField(default=False)

    # Password reset OTP
    reset_otp = models.CharField(max_length=20, blank=True, null=True)
    reset_otp_created_at = models.DateTimeField(null=True, blank=True)
    reset_otp_expires_at = models.DateTimeField(null=True, blank=True)

    # Timestamps (created_at, updated_at handled by Django User model's date_joined and last_login)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    def generate_otp(self, length=12):
        """Generate a secure one-time password"""
        characters = string.ascii_letters + string.digits
        otp = ''.join(secrets.choice(characters) for _ in range(length))

        self.otp = otp
        self.otp_created_at = timezone.now()
        self.otp_expires_at = timezone.now() + timezone.timedelta(days=7)
        self.otp_used = False
        self.save()

        return otp

    def is_otp_valid(self):
        """Check if OTP is valid and not expired"""
        if not self.otp or self.otp_used:
            return False
        if self.otp_expires_at and timezone.now() > self.otp_expires_at:
            return False
        return True

    def generate_reset_otp(self, length=6):
        """Generate OTP for password reset"""
        otp = ''.join(secrets.choice(string.digits) for _ in range(length))

        self.reset_otp = otp
        self.reset_otp_created_at = timezone.now()
        self.reset_otp_expires_at = timezone.now() + timezone.timedelta(minutes=15)
        self.save()

        return otp

    def is_reset_otp_valid(self, otp):
        """Verify password reset OTP"""
        if not self.reset_otp or self.reset_otp != otp:
            return False
        if self.reset_otp_expires_at and timezone.now() > self.reset_otp_expires_at:
            return False
        return True

    def is_admin_user(self):
        """Check if user is an administrator"""
        return self.role == self.ADMIN

    def is_manager_user(self):
        """Check if user is a manager"""
        return self.role == self.MANAGER

    def is_org_manager_user(self):
        """Check if user is an organization manager (org-only access)"""
        return self.role == self.ORG_MANAGER

    def is_org_admin_user(self):
        """Check if user is an org admin (scoped to one organization)"""
        return self.role == self.ORG_ADMIN


class Session(models.Model):
    """User session tracking - supports both logged-in users and anonymous metric tokens"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    metric_token = models.CharField(max_length=100, null=True, blank=True, db_index=True, help_text="Anonymous user identifier")
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_duration = models.IntegerField(default=0, help_text="Duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', '-start_time']),
            models.Index(fields=['metric_token', '-start_time']),
            models.Index(fields=['start_time']),
        ]

    def __str__(self):
        identifier = self.user.username if self.user else f"Metric {self.metric_token[:8]}"
        return f"Session {self.id} - {identifier} at {self.start_time}"

    def get_duration_hours(self):
        """Get session duration in hours"""
        if self.total_duration:
            return round(self.total_duration / 3600, 2)
        return 0


class Activity(models.Model):
    """Activity tracking - tracks application usage for both logged-in users and anonymous metric tokens"""

    ACTIVITY_TYPES = (
        (0, 'Window Change'),
        (1, 'Application Change'),
        (2, 'Input'),
        (3, 'Idle'),
        (4, 'Custom'),
    )

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
    metric_token = models.CharField(max_length=100, null=True, blank=True, db_index=True, help_text="Anonymous user identifier")
    activity_type = models.IntegerField(choices=ACTIVITY_TYPES, default=0)
    window_title = models.CharField(max_length=500, blank=True, null=True)
    process_name = models.CharField(max_length=200, db_index=True)
    details = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['session', '-start_time']),
            models.Index(fields=['metric_token', '-start_time']),
            models.Index(fields=['process_name']),
            models.Index(fields=['start_time']),
        ]

    def __str__(self):
        return f"{self.process_name} - {self.start_time}"

    def get_duration_minutes(self):
        """Get activity duration in minutes"""
        if self.duration:
            return round(self.duration / 60, 2)
        return 0


class NetworkActivity(models.Model):
    """Tracks website/URL visits detected from browser window titles"""
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='network_activities', null=True, blank=True)
    metric_token = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    url = models.URLField(max_length=2000, null=True, blank=True)
    domain = models.CharField(max_length=500, db_index=True)
    page_title = models.CharField(max_length=500, null=True, blank=True)
    browser_process = models.CharField(max_length=200, db_index=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in seconds")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['session', '-start_time']),
            models.Index(fields=['metric_token', '-start_time']),
            models.Index(fields=['domain']),
            models.Index(fields=['start_time']),
        ]

    def __str__(self):
        return f"{self.domain} - {self.browser_process} at {self.start_time}"

    def get_duration_minutes(self):
        if self.duration:
            return round(self.duration / 60, 2)
        return 0


class ApplicationUsageStats(models.Model):
    """Aggregated statistics for application usage per user per day"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='app_stats')
    process_name = models.CharField(max_length=200, db_index=True)
    date = models.DateField(db_index=True)
    total_duration = models.IntegerField(default=0, help_text="Total duration in seconds")
    switch_count = models.IntegerField(default=0, help_text="Number of times switched to this app")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-total_duration']
        unique_together = ['user', 'process_name', 'date']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.process_name} on {self.date}"

    def get_duration_hours(self):
        """Get usage duration in hours"""
        return round(self.total_duration / 3600, 2)


class AppCategory(models.Model):
    """
    Application categorization for productivity tracking
    Defines whether an application is productive, neutral, or non-productive
    """
    PRODUCTIVE = 'PRODUCTIVE'
    NEUTRAL = 'NEUTRAL'
    NON_PRODUCTIVE = 'NON_PRODUCTIVE'

    CATEGORY_CHOICES = [
        (PRODUCTIVE, 'Productive'),
        (NEUTRAL, 'Neutral'),
        (NON_PRODUCTIVE, 'Non-Productive'),
    ]

    process_name = models.CharField(max_length=200, db_index=True, help_text="Application process name (e.g., chrome.exe)")
    display_name = models.CharField(max_length=200, help_text="Human-readable name (e.g., Google Chrome)")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=NEUTRAL)
    description = models.TextField(blank=True, null=True, help_text="Why this app is categorized this way")
    is_global = models.BooleanField(default=True, help_text="Applies to all departments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_app_categories')

    class Meta:
        ordering = ['display_name']
        verbose_name_plural = 'App Categories'

    def __str__(self):
        return f"{self.display_name} ({self.category})"


class DepartmentAppRule(models.Model):
    """
    Department-specific application categorization rules
    Overrides global app categories for specific departments
    Example: Telegram is productive for Sales but non-productive for Accounting
    """
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='app_rules',
        help_text="Department this rule applies to"
    )
    app_category = models.ForeignKey(AppCategory, on_delete=models.CASCADE, related_name='department_rules')
    category_override = models.CharField(
        max_length=20,
        choices=AppCategory.CATEGORY_CHOICES,
        help_text="Override category for this department"
    )
    reason = models.TextField(blank=True, null=True, help_text="Why this department has different rules")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_dept_rules')

    class Meta:
        unique_together = ['department', 'app_category']
        ordering = ['department', 'app_category']
        verbose_name_plural = 'Department App Rules'

    def __str__(self):
        return f"{self.department.name}: {self.app_category.display_name} -> {self.category_override}"


class ManualTimeEntry(models.Model):
    """
    Manual time entry for non-computer activities
    Allows employees to log meetings, calls, field work, etc.
    """
    MEETING = 'MEETING'
    PHONE_CALL = 'PHONE_CALL'
    FIELD_WORK = 'FIELD_WORK'
    TRAINING = 'TRAINING'
    BREAK = 'BREAK'
    OTHER = 'OTHER'

    ACTIVITY_TYPE_CHOICES = [
        (MEETING, 'Meeting'),
        (PHONE_CALL, 'Phone Call'),
        (FIELD_WORK, 'Field Work'),
        (TRAINING, 'Training'),
        (BREAK, 'Break'),
        (OTHER, 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='manual_time_entries')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    description = models.TextField(help_text="Description of the activity")
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField(help_text="Duration in minutes")
    is_productive = models.BooleanField(
        default=True,
        help_text="Whether this activity counts as productive time"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', '-start_time']),
            models.Index(fields=['start_time']),
        ]
        verbose_name_plural = 'Manual Time Entries'

    def __str__(self):
        return f"{self.user.full_name}: {self.activity_type} - {self.duration_minutes}min"

    def save(self, *args, **kwargs):
        # Auto-calculate duration if not provided
        if not self.duration_minutes and self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        super().save(*args, **kwargs)


class PositionAppWeight(models.Model):
    """
    Position-specific application productivity weight.
    Links a JobPosition + AppCategory with a weight (0.0-1.0).
    Example: Developer + Visual Studio = 1.0, Developer + Chrome = 0.5
    """
    position = models.ForeignKey(
        JobPosition,
        on_delete=models.CASCADE,
        related_name='app_weights',
        help_text="Job position this weight applies to"
    )
    app_category = models.ForeignKey(
        AppCategory,
        on_delete=models.CASCADE,
        related_name='position_weights',
        help_text="Application this weight is for"
    )
    weight = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Productivity weight (0.0 = fully unproductive, 1.0 = fully productive)"
    )
    reason = models.TextField(blank=True, null=True, help_text="Why this weight was assigned")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_position_weights')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['position', 'app_category']
        ordering = ['position', 'app_category']
        verbose_name_plural = 'Position App Weights'

    def __str__(self):
        return f"{self.position.title}: {self.app_category.display_name} = {self.weight}"


class WorkingShift(models.Model):
    """
    Per-day working shift schedule for each employee.
    Each employee can have different start/end times for each day of the week.
    Example: Monday 9:00-18:00, Tuesday 10:00-19:00, Saturday is_day_off=True
    """
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    DAY_CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
        (SUNDAY, 'Sunday'),
    ]

    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='working_shifts',
        help_text="Employee this shift belongs to"
    )
    day_of_week = models.IntegerField(
        choices=DAY_CHOICES,
        help_text="Day of the week (0=Monday, 6=Sunday)"
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Shift start time (e.g. 09:00)"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Shift end time (e.g. 18:00)"
    )
    is_day_off = models.BooleanField(
        default=False,
        help_text="If True, employee does not work this day"
    )
    lunch_break_minutes = models.IntegerField(
        default=60,
        help_text="Lunch break duration in minutes (deducted from working hours)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'day_of_week']
        ordering = ['user', 'day_of_week']
        verbose_name = 'Working Shift'
        verbose_name_plural = 'Working Shifts'

    def __str__(self):
        day_name = self.get_day_of_week_display()
        if self.is_day_off:
            return f"{self.user.full_name} - {day_name}: Day Off"
        return f"{self.user.full_name} - {day_name}: {self.start_time} to {self.end_time}"

    def get_duration_hours(self):
        """Get shift duration in hours (lunch break deducted)"""
        if self.is_day_off or not self.start_time or not self.end_time:
            return 0
        from datetime import datetime, timedelta
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        total_seconds = (end_dt - start_dt).total_seconds()
        # Deduct lunch break
        lunch_seconds = (self.lunch_break_minutes or 0) * 60
        net_seconds = max(total_seconds - lunch_seconds, 0)
        return round(net_seconds / 3600, 2)


class ProductivitySettings(models.Model):
    """
    Singleton model for global productivity settings.
    Stores configurable defaults for the productivity calculation.
    """
    default_weight = models.FloatField(
        default=0.3,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Default weight for uncategorized apps (0.0-1.0)"
    )
    productive_threshold = models.IntegerField(
        default=75,
        help_text="Score >= this is 'productive' (%)"
    )
    needs_improvement_threshold = models.IntegerField(
        default=60,
        help_text="Score >= this is 'needs improvement', below is 'unproductive' (%)"
    )
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Productivity Settings'

    def __str__(self):
        return f"Productivity Settings (default_weight={self.default_weight})"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
