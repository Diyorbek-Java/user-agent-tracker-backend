"""
Authentication views for email-based login, OTP, and staff invitation
"""
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import User


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login with email and password (or OTP for first-time login)

    POST /api/auth/login/
    Body: {
        "email": "user@example.com",
        "password": "password_or_otp"
    }
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({
            'success': False,
            'error': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email.lower())
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Check if account is active
    if not user.is_active:
        return Response({
            'success': False,
            'error': 'Your account has been deactivated. Please contact your administrator.'
        }, status=status.HTTP_403_FORBIDDEN)

    # Check if this is first-time login with OTP
    if user.otp and not user.otp_used and user.is_otp_valid():
        if password == user.otp:
            # OTP login successful - mark OTP as used
            user.otp_used = True
            user.last_login = timezone.now()
            user.save()

            return Response({
                'success': True,
                'first_login': True,
                'message': 'OTP verified. Please set a new password.',
                'user': {
                    'id': user.id,
                    'employee_id': user.employee_id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                }
            })

    # Regular login with Django User authentication
    authenticated_user = authenticate(username=user.username, password=password)

    if authenticated_user is not None:
        # Update last login
        user.last_login = timezone.now()
        user.save()

        # Get or create token
        token, created = Token.objects.get_or_create(user=authenticated_user)

        return Response({
            'success': True,
            'first_login': False,
            'token': token.key,
            'user': {
                'id': user.id,
                'employee_id': user.employee_id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_admin': user.is_admin_user(),
                'department': user.department,
                'position': user.position,
            }
        })

    return Response({
        'success': False,
        'error': 'Invalid email or password'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def set_password_view(request):
    """
    Set password after first-time OTP login

    POST /api/auth/set-password/
    Body: {
        "email": "user@example.com",
        "new_password": "NewSecurePassword123!"
    }
    """
    email = request.data.get('email')
    new_password = request.data.get('new_password')

    if not email or not new_password:
        return Response({
            'success': False,
            'error': 'Email and new password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate password strength
    if len(new_password) < 8:
        return Response({
            'success': False,
            'error': 'Password must be at least 8 characters long'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email.lower())
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Check if OTP was used (first login completed)
    if not user.otp_used:
        return Response({
            'success': False,
            'error': 'Please login with OTP first'
        }, status=status.HTTP_403_FORBIDDEN)

    # Update user password
    user.set_password(new_password)
    user.save()

    # Clear OTP fields
    user.otp = None
    user.otp_created_at = None
    user.otp_expires_at = None
    user.save()

    # Create token for immediate login
    token, created = Token.objects.get_or_create(user=user)

    return Response({
        'success': True,
        'message': 'Password set successfully. You can now login.',
        'token': token.key,
        'user': {
            'id': user.id,
            'employee_id': user.employee_id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_staff_view(request):
    """
    Admin-only: Invite new staff member (Simplified version)

    POST /api/admin/invite-staff/
    """
    # Check if user is admin
    if not request.user.is_admin_user():
        return Response({
            'success': False,
            'error': 'Only administrators can invite staff members'
        }, status=status.HTTP_403_FORBIDDEN)

    # Get data from request
    email = request.data.get('email', '').lower()
    full_name = request.data.get('full_name')
    employee_id = request.data.get('employee_id')
    department = request.data.get('department', '')
    position = request.data.get('position', '')
    role = request.data.get('role', User.EMPLOYEE)

    # Validation
    if not all([email, full_name, employee_id]):
        return Response({
            'success': False,
            'error': 'Email, full name, and employee ID are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if email or employee ID already exists
    if User.objects.filter(email=email).exists():
        return Response({
            'success': False,
            'error': 'A user with this email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(employee_id=employee_id).exists():
        return Response({
            'success': False,
            'error': 'A user with this employee ID already exists'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Create user with OTP
    new_user = User.objects.create_user(
        username=email.split('@')[0] + employee_id,
        email=email,
        employee_id=employee_id,
        full_name=full_name,
        department=department,
        position=position,
        role=role,
        is_active=True,
        is_invited=False
    )

    # Generate OTP
    otp = new_user.generate_otp()
    new_user.is_invited = True
    new_user.invitation_sent_at = timezone.now()
    new_user.save()

    return Response({
        'success': True,
        'message': f'User created for {email}',
        'user': {
            'id': new_user.id,
            'employee_id': new_user.employee_id,
            'email': new_user.email,
            'full_name': new_user.full_name,
            'role': new_user.role,
            'otp': otp,  # Return OTP for testing
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset_view(request):
    """
    Request password reset OTP

    POST /api/auth/request-password-reset/
    Body: {
        "email": "user@example.com"
    }
    """
    email = request.data.get('email', '').lower()

    if not email:
        return Response({
            'success': False,
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal if email exists
        return Response({
            'success': True,
            'message': 'If the email exists, a password reset OTP has been sent'
        })

    # Generate reset OTP
    reset_otp = user.generate_reset_otp()

    return Response({
        'success': True,
        'message': 'If the email exists, a password reset OTP has been sent',
        'otp': reset_otp  # For testing only
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_view(request):
    """
    Reset password using OTP

    POST /api/auth/reset-password/
    Body: {
        "email": "user@example.com",
        "otp": "123456",
        "new_password": "NewPassword123!"
    }
    """
    email = request.data.get('email', '').lower()
    otp = request.data.get('otp')
    new_password = request.data.get('new_password')

    if not all([email, otp, new_password]):
        return Response({
            'success': False,
            'error': 'Email, OTP, and new password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate password
    if len(new_password) < 8:
        return Response({
            'success': False,
            'error': 'Password must be at least 8 characters long'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid email or OTP'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Verify OTP
    if not user.is_reset_otp_valid(otp):
        return Response({
            'success': False,
            'error': 'Invalid or expired OTP'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Update password
    user.set_password(new_password)
    user.save()

    # Clear reset OTP
    user.reset_otp = None
    user.reset_otp_created_at = None
    user.reset_otp_expires_at = None
    user.save()

    return Response({
        'success': True,
        'message': 'Password reset successfully. You can now login with your new password.'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """Get current logged-in user details"""
    user = request.user
    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'employee_id': user.employee_id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'is_admin': user.is_admin_user(),
            'department': user.department,
            'position': user.position,
            'last_login': user.last_login,
        }
    })
