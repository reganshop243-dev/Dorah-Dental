"""
OTP Service for two-factor authentication
"""

import hashlib
import logging
import secrets
from datetime import timedelta

from django.utils import timezone

from notifications.yoola_sms import YoolaSMS

logger = logging.getLogger(__name__)


class OTPService:
    """Handles OTP generation, sending, and verification."""

    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    MAX_ATTEMPTS = 3

    def generate_otp(self):
        """Generate a secure 6-digit OTP."""
        return f"{secrets.randbelow(1_000_000):06d}"

    def hash_otp(self, otp_code):
        """Return the SHA-256 hash used for storing the OTP."""
        return hashlib.sha256(
            otp_code.encode("utf-8")
        ).hexdigest()

    def send_otp_sms(self, phone_number, otp_code):
        """Send OTP via SMS using Yoola."""
        try:
            yoola = YoolaSMS()

            message = (
                f"Dora's Dental Gem: Your OTP is {otp_code}. "
                f"It expires in 5 minutes. Do not share it."
            )

            try:
                result = yoola.send_sms(phone_number, message)
            except Exception as exc:
                logger.error(
                    "Yoola SMS error for %s: %s",
                    phone_number,
                    exc,
                    exc_info=True,
                )
                return False

            if result and result.get("success"):
                logger.info(
                    "OTP sent successfully to %s",
                    phone_number,
                )
                return True

            error = result.get("error") if result else "Unknown SMS error"

            logger.error(
                "Failed to send OTP to %s: %s",
                phone_number,
                error,
            )

            return False

        except Exception as exc:
            logger.error(
                "Error sending OTP: %s",
                exc,
                exc_info=True,
            )
            return False

    def create_and_send_otp(self, user):
        """Generate an OTP, store its hash, and send the OTP by SMS."""

        profile = user.profile

        # ---------------------------------------------------------
        # Existing trusted verification
        # ---------------------------------------------------------
        if (
            profile.phone_verified
            and profile.otp_verified_at
            and timezone.now() - profile.otp_verified_at
            < timedelta(hours=24)
        ):
            return (
                False,
                "OTP verification is still valid for this user. "
                "Please sign in normally.",
            )

        # ---------------------------------------------------------
        # Phone number check
        # ---------------------------------------------------------
        if not profile.phone:
            logger.error(
                "User %s has no phone number",
                user.username,
            )

            return (
                False,
                "No phone number registered. "
                "Please contact administrator.",
            )

        # ---------------------------------------------------------
        # Existing OTP still valid
        # ---------------------------------------------------------
        if profile.otp_code and profile.otp_created_at:

            age = timezone.now() - profile.otp_created_at

            if age.total_seconds() <= self.OTP_EXPIRY_SECONDS:
                return (
                    False,
                    "A verification code was already sent. "
                    "Please check your phone.",
                )

        # ---------------------------------------------------------
        # Rate-limit OTP requests
        # ---------------------------------------------------------
        if not profile.can_request_otp():
            return (
                False,
                "Please wait before requesting another "
                "verification code.",
            )

        # ---------------------------------------------------------
        # Generate OTP
        # ---------------------------------------------------------
        otp = self.generate_otp()

        # Store HASHED OTP, never the plain OTP.
        hashed_otp = self.hash_otp(otp)

        profile.otp_code = hashed_otp
        profile.otp_created_at = timezone.now()
        profile.otp_attempts = 0

        profile.save(
            update_fields=[
                "otp_code",
                "otp_created_at",
                "otp_attempts",
                "updated_at",
            ]
        )

        # ---------------------------------------------------------
        # Send SMS
        # ---------------------------------------------------------
        success = self.send_otp_sms(
            profile.phone,
            otp,
        )

        if success:

            profile.last_otp_sent = timezone.now()

            profile.save(
                update_fields=[
                    "last_otp_sent",
                    "updated_at",
                ]
            )

            logger.info(
                "OTP sent to %s for user %s",
                profile.phone,
                user.username,
            )

            return True, "OTP sent successfully"

        # ---------------------------------------------------------
        # SMS failed
        #
        # IMPORTANT:
        # otp_code must NOT be None because the database field
        # is NOT NULL.
        # ---------------------------------------------------------
        profile.otp_code = ""
        profile.otp_created_at = None
        profile.otp_attempts = 0

        profile.save(
            update_fields=[
                "otp_code",
                "otp_created_at",
                "otp_attempts",
                "updated_at",
            ]
        )

        logger.warning(
            "SMS delivery failed for user %s; OTP invalidated",
            user.username,
        )

        return (
            False,
            "We could not send the verification code. "
            "Please try again shortly.",
        )

    def verify_otp(self, user, otp_code):
        """Verify a submitted OTP."""

        profile = user.profile

        # ---------------------------------------------------------
        # Basic validation
        # ---------------------------------------------------------
        otp_code = str(otp_code or "").strip()

        if not otp_code:
            return False, "Please enter the verification code."

        if not otp_code.isdigit() or len(otp_code) != 6:
            return False, "Invalid OTP code."

        # ---------------------------------------------------------
        # OTP exists
        # ---------------------------------------------------------
        if not profile.otp_code:
            return False, "No OTP requested."

        # ---------------------------------------------------------
        # OTP creation time exists
        # ---------------------------------------------------------
        if not profile.otp_created_at:
            return False, "OTP has expired. Please request a new code."

        # ---------------------------------------------------------
        # Check expiry
        # ---------------------------------------------------------
        age = timezone.now() - profile.otp_created_at

        if age.total_seconds() > self.OTP_EXPIRY_SECONDS:

            # IMPORTANT:
            # Use empty string, NOT None.
            profile.otp_code = ""
            profile.otp_created_at = None
            profile.otp_attempts = 0

            profile.save(
                update_fields=[
                    "otp_code",
                    "otp_created_at",
                    "otp_attempts",
                    "updated_at",
                ]
            )

            return (
                False,
                "OTP has expired. Please request a new code.",
            )

        # ---------------------------------------------------------
        # Check attempts
        # ---------------------------------------------------------
        if profile.otp_attempts >= self.MAX_ATTEMPTS:
            return (
                False,
                "Too many failed attempts. "
                "Please request a new OTP.",
            )

        # ---------------------------------------------------------
        # Increment attempt count
        # ---------------------------------------------------------
        profile.otp_attempts += 1

        profile.save(
            update_fields=[
                "otp_attempts",
                "updated_at",
            ]
        )

        # ---------------------------------------------------------
        # Hash submitted OTP
        # ---------------------------------------------------------
        submitted_hash = self.hash_otp(otp_code)

        # ---------------------------------------------------------
        # Secure comparison
        # ---------------------------------------------------------
        valid = hmac_compare(
            submitted_hash,
            profile.otp_code,
        )

        if valid:

            # -----------------------------------------------------
            # SUCCESS
            #
            # IMPORTANT:
            # Never use None for otp_code.
            # The database field is NOT NULL.
            # -----------------------------------------------------
            profile.otp_code = ""
            profile.otp_created_at = None
            profile.otp_attempts = 0
            profile.phone_verified = True
            profile.otp_verified_at = timezone.now()

            profile.save(
                update_fields=[
                    "otp_code",
                    "otp_created_at",
                    "otp_attempts",
                    "phone_verified",
                    "otp_verified_at",
                    "updated_at",
                ]
            )

            logger.info(
                "OTP verified successfully for user %s",
                user.username,
            )

            return True, "OTP verified successfully"

        # ---------------------------------------------------------
        # Failed OTP
        # ---------------------------------------------------------
        remaining = self.MAX_ATTEMPTS - profile.otp_attempts

        if remaining <= 0:
            return (
                False,
                "Too many failed attempts. "
                "Please request a new OTP.",
            )

        return (
            False,
            f"Invalid OTP code. {remaining} attempt(s) remaining.",
        )


def hmac_compare(value1, value2):
    """
    Constant-time comparison for OTP hashes.
    """

    if not value1 or not value2:
        return False

    return secrets.compare_digest(
        value1,
        value2,
    )