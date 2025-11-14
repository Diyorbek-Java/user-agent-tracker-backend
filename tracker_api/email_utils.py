"""
Email utility functions for sending invitations and OTP
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_staff_invitation_email(employee, otp, download_link=None):
    """
    Send invitation email to new staff member with OTP and download link

    Args:
        employee: Employee instance
        otp: One-time password for first login
        download_link: URL to download the tracker application

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = 'Welcome to Employee Monitoring System'

    # Default download link if not provided
    if not download_link:
        download_link = settings.TRACKER_DOWNLOAD_URL if hasattr(settings, 'TRACKER_DOWNLOAD_URL') else '#'

    # Email context
    context = {
        'employee_name': employee.full_name,
        'employee_id': employee.employee_id,
        'email': employee.email,
        'otp': otp,
        'download_link': download_link,
        'company_name': getattr(settings, 'COMPANY_NAME', 'Your Company'),
        'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@example.com'),
    }

    # HTML email content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background: #f9f9f9; }}
            .otp-box {{ background: #fff; border: 2px solid #4CAF50; padding: 20px; margin: 20px 0; text-align: center; }}
            .otp {{ font-size: 24px; font-weight: bold; color: #4CAF50; letter-spacing: 2px; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            .steps {{ background: #fff; padding: 20px; margin: 20px 0; border-left: 4px solid #4CAF50; }}
            .step {{ margin: 10px 0; padding-left: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to {context['company_name']}</h1>
            </div>

            <div class="content">
                <h2>Hello {context['employee_name']},</h2>

                <p>Your account has been created in our Employee Monitoring System. You can now download and install the tracker application.</p>

                <div class="otp-box">
                    <p><strong>Your One-Time Password (OTP):</strong></p>
                    <p class="otp">{context['otp']}</p>
                    <p><small>Valid for 7 days. Use this for your first login.</small></p>
                </div>

                <div class="steps">
                    <h3>Getting Started:</h3>

                    <div class="step">
                        <strong>Step 1:</strong> Download the Tracker Application
                        <br>
                        <a href="{context['download_link']}" class="button">Download Tracker App</a>
                    </div>

                    <div class="step">
                        <strong>Step 2:</strong> Install the application on your computer
                    </div>

                    <div class="step">
                        <strong>Step 3:</strong> Launch the application
                    </div>

                    <div class="step">
                        <strong>Step 4:</strong> Login with:
                        <ul>
                            <li><strong>Email:</strong> {context['email']}</li>
                            <li><strong>Password:</strong> Use the OTP above</li>
                        </ul>
                    </div>

                    <div class="step">
                        <strong>Step 5:</strong> You'll be prompted to set a new password
                    </div>
                </div>

                <p><strong>Your Account Details:</strong></p>
                <ul>
                    <li><strong>Employee ID:</strong> {context['employee_id']}</li>
                    <li><strong>Email:</strong> {context['email']}</li>
                    <li><strong>Role:</strong> Staff Member</li>
                </ul>

                <p><strong>Important Notes:</strong></p>
                <ul>
                    <li>Keep your OTP secure and don't share it with anyone</li>
                    <li>The OTP expires in 7 days</li>
                    <li>After first login, set a strong password</li>
                    <li>The tracker application monitors your work activity</li>
                </ul>

                <p>If you have any questions or need assistance, please contact support at
                   <a href="mailto:{context['support_email']}">{context['support_email']}</a></p>
            </div>

            <div class="footer">
                <p>&copy; 2025 {context['company_name']}. All rights reserved.</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version (fallback)
    plain_message = f"""
    Welcome to {context['company_name']}!

    Hello {context['employee_name']},

    Your account has been created in our Employee Monitoring System.

    YOUR ONE-TIME PASSWORD (OTP): {context['otp']}
    Valid for 7 days. Use this for your first login.

    GETTING STARTED:

    1. Download the Tracker Application: {context['download_link']}
    2. Install the application on your computer
    3. Launch the application
    4. Login with:
       - Email: {context['email']}
       - Password: Use the OTP above
    5. You'll be prompted to set a new password

    Your Account Details:
    - Employee ID: {context['employee_id']}
    - Email: {context['email']}
    - Role: Staff Member

    Important Notes:
    - Keep your OTP secure and don't share it with anyone
    - The OTP expires in 7 days
    - After first login, set a strong password
    - The tracker application monitors your work activity

    If you have any questions, contact: {context['support_email']}

    © 2025 {context['company_name']}. All rights reserved.
    """

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending invitation email: {str(e)}")
        return False


def send_password_reset_email(employee, otp):
    """
    Send password reset OTP email

    Args:
        employee: Employee instance
        otp: Password reset OTP (6 digits)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = 'Password Reset Request'

    context = {
        'employee_name': employee.full_name,
        'otp': otp,
        'company_name': getattr(settings, 'COMPANY_NAME', 'Your Company'),
    }

    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #2196F3; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background: #f9f9f9; }}
            .otp-box {{ background: #fff; border: 2px solid #2196F3; padding: 20px; margin: 20px 0; text-align: center; }}
            .otp {{ font-size: 32px; font-weight: bold; color: #2196F3; letter-spacing: 4px; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>

            <div class="content">
                <h2>Hello {context['employee_name']},</h2>

                <p>We received a request to reset your password. Use the following OTP to reset your password:</p>

                <div class="otp-box">
                    <p class="otp">{context['otp']}</p>
                    <p><small>This OTP is valid for 15 minutes</small></p>
                </div>

                <p><strong>If you didn't request this password reset, please ignore this email.</strong></p>

                <p>Your password will remain unchanged until you create a new one using this OTP.</p>
            </div>

            <div class="footer">
                <p>&copy; 2025 {context['company_name']}. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    plain_message = f"""
    Password Reset Request

    Hello {context['employee_name']},

    We received a request to reset your password.

    Your Password Reset OTP: {context['otp']}

    This OTP is valid for 15 minutes.

    If you didn't request this password reset, please ignore this email.

    © 2025 {context['company_name']}
    """

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        return False


def send_welcome_email(employee):
    """Send welcome email after successful account activation"""
    subject = f'Welcome to {getattr(settings, "COMPANY_NAME", "Employee Monitoring System")}!'

    message = f"""
    Hello {employee.full_name},

    Your account has been successfully activated!

    You can now log in to the tracker application using your email and the password you set.

    Thank you for joining us!

    Best regards,
    {getattr(settings, "COMPANY_NAME", "The Team")}
    """

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        return False
