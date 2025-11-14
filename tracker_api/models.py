from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import secrets
import string


class User(AbstractUser):
    """Custom User model combining authentication and employee information"""

    # Role choices
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    EMPLOYEE = 'EMPLOYEE'

    ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (MANAGER, 'Manager'),
        (EMPLOYEE, 'Employee'),
    ]

    # User role and employee details
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)
    employee_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique employee identifier")
    full_name = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
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
