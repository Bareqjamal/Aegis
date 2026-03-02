"""Project Aegis — Authentication Manager.

Handles user registration, login, session management, and tier gating.
Phase 1: JSON-based auth with bcrypt password hashing.
Phase 2: Swap to Supabase Auth / OAuth.

Usage in Streamlit:
    from auth_manager import auth_manager, require_auth
    user = auth_manager.get_current_user()  # None if not logged in
    if require_auth():  # returns True if authenticated, shows login form if not
        st.write(f"Welcome, {user['name']}")
"""

import hashlib
import hmac
import logging
import os
import random
import secrets
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from data_store import data_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------
TIERS = {
    "free": {
        "name": "Recruit",
        "price": 0,
        "max_assets": 12,
        "max_scans_per_day": 999,
        "max_paper_positions": 10,
        "autopilot": True,
        "social_sentiment": True,
        "risk_dashboard": True,
        "optimizer": False,
        "backtesting": False,
        "api_access": False,
        "export_reports": True,
        "chart_indicators": 5,
        "refresh_ms": 60_000,
    },
    "pro": {
        "name": "Operator",
        "price": 29,
        "max_assets": 50,
        "max_scans_per_day": 999,
        "max_paper_positions": 999,
        "autopilot": True,
        "social_sentiment": True,
        "risk_dashboard": True,
        "optimizer": True,
        "backtesting": True,
        "api_access": False,
        "export_reports": True,
        "chart_indicators": 30,
        "refresh_ms": 10_000,
    },
    "enterprise": {
        "name": "Command",
        "price": 199,
        "max_assets": 999,
        "max_scans_per_day": 999,
        "max_paper_positions": 999,
        "autopilot": True,
        "social_sentiment": True,
        "risk_dashboard": True,
        "optimizer": True,
        "backtesting": True,
        "api_access": True,
        "export_reports": True,
        "chart_indicators": 99,
        "refresh_ms": 5_000,
    },
}

# Pro-only pages (view keys that require Pro tier)
# NOTE: Keep this tight — free users should SEE most pages to get hooked.
# Only gate the heavy analytics/optimization tools.
PRO_VIEWS = {
    "optimizer", "strategy_lab",
}

# Pro-only features checked inline
# Social sentiment is FREE (it's our killer feature — hooks users)
PRO_FEATURES = {
    "autopilot", "export_reports", "backtesting",
}


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash password with PBKDF2-HMAC-SHA256. Returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    )
    return pw_hash.hex(), salt


def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify a password against stored hash."""
    computed, _ = _hash_password(password, salt)
    return hmac.compare_digest(computed, stored_hash)


# ---------------------------------------------------------------------------
# Email verification constants
# ---------------------------------------------------------------------------
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_TTL_MINUTES = 15

# SMTP configuration from environment variables
SMTP_HOST = os.environ.get("AEGIS_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("AEGIS_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("AEGIS_SMTP_USER")  # None if not set
SMTP_PASS = os.environ.get("AEGIS_SMTP_PASS")  # None if not set
SMTP_FROM = os.environ.get("AEGIS_SMTP_FROM", "noreply@aegis-terminal.com")


def _generate_verification_code() -> str:
    """Generate a cryptographically random 6-digit verification code."""
    return "".join(str(random.SystemRandom().randint(0, 9)) for _ in range(VERIFICATION_CODE_LENGTH))


def _build_verification_email_html(code: str, name: str) -> str:
    """Build a dark-themed HTML email body matching the Aegis Bloomberg style."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Verify Your Email — Project Aegis</title>
</head>
<body style="margin:0;padding:0;background-color:#010409;font-family:'JetBrains Mono','Fira Code','Courier New',monospace;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#010409;padding:40px 0;">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background-color:#0d1117;border:1px solid #21262d;border-radius:8px;overflow:hidden;">
  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#0d1117 0%,#161b22 100%);padding:32px 40px 24px;border-bottom:1px solid #21262d;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <span style="font-size:24px;font-weight:700;color:#3fb950;letter-spacing:2px;">&#9670; PROJECT AEGIS</span>
          </td>
          <td align="right">
            <span style="font-size:11px;color:#6e7681;letter-spacing:1px;">TRADING TERMINAL</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- Body -->
  <tr>
    <td style="padding:40px;">
      <p style="margin:0 0 8px;font-size:13px;color:#6e7681;letter-spacing:1px;text-transform:uppercase;">Email Verification</p>
      <h1 style="margin:0 0 24px;font-size:22px;font-weight:600;color:#e6edf3;font-family:'Segoe UI',Inter,Arial,sans-serif;">
        Verify your email address
      </h1>
      <p style="margin:0 0 24px;font-size:14px;color:#8b949e;line-height:1.6;font-family:'Segoe UI',Inter,Arial,sans-serif;">
        Hello{(' ' + name) if name else ''},<br><br>
        Enter the following verification code in the Aegis Terminal to activate your account:
      </p>
      <!-- Code box -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:16px 0 32px;">
          <div style="display:inline-block;background-color:#161b22;border:2px solid #3fb950;border-radius:8px;padding:20px 48px;">
            <span style="font-size:36px;font-weight:700;color:#3fb950;letter-spacing:12px;font-family:'JetBrains Mono','Fira Code','Courier New',monospace;">
              {code}
            </span>
          </div>
        </td></tr>
      </table>
      <p style="margin:0 0 8px;font-size:13px;color:#f0883e;font-family:'Segoe UI',Inter,Arial,sans-serif;">
        &#9888; This code expires in {VERIFICATION_TTL_MINUTES} minutes.
      </p>
      <p style="margin:0;font-size:13px;color:#8b949e;line-height:1.5;font-family:'Segoe UI',Inter,Arial,sans-serif;">
        If you did not create an account on Project Aegis, you can safely ignore this email.
      </p>
    </td>
  </tr>
  <!-- Footer -->
  <tr>
    <td style="background-color:#010409;padding:24px 40px;border-top:1px solid #21262d;">
      <p style="margin:0 0 8px;font-size:11px;color:#484f58;line-height:1.5;font-family:'Segoe UI',Inter,Arial,sans-serif;">
        Project Aegis is an autonomous market research and trading signals system for
        educational and informational purposes only. Nothing contained herein constitutes
        financial advice. Trade at your own risk.
      </p>
      <p style="margin:0;font-size:11px;color:#30363d;">
        &copy; {datetime.now().year} Project Aegis &mdash; AI Trading Terminal
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _send_verification_email(email: str, code: str, name: str) -> bool:
    """Send the verification email via SMTP.

    Returns True if sent successfully.
    If SMTP credentials are not configured, logs the code to console and returns False.
    Never raises — all errors are caught and logged.
    """
    # Build the message regardless (we may log it)
    html_body = _build_verification_email_html(code, name)

    if not SMTP_USER or not SMTP_PASS:
        logger.debug(
            "[Aegis Auth] SMTP not configured. Verification code for <%s>: %s",
            email,
            code,
        )
        # NOTE: Code intentionally NOT printed to stdout in production.
        # Set AEGIS_SMTP_* env vars for email delivery.
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your Aegis Verification Code: {code}"
        msg["From"] = SMTP_FROM
        msg["To"] = email

        # Plain text fallback
        plain = (
            f"Project Aegis — Email Verification\n\n"
            f"Hello{(' ' + name) if name else ''},\n\n"
            f"Your verification code is: {code}\n\n"
            f"This code expires in {VERIFICATION_TTL_MINUTES} minutes.\n\n"
            f"If you did not create an account, ignore this email.\n"
        )
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [email], msg.as_string())

        logger.info("[Aegis Auth] Verification email sent to <%s>", email)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[Aegis Auth] SMTP authentication failed. Check AEGIS_SMTP_USER / AEGIS_SMTP_PASS.")
        logger.debug("[Aegis Auth] SMTP auth failed. Verification code for <%s>: %s", email, code)
    except smtplib.SMTPException as exc:
        logger.error("[Aegis Auth] SMTP error sending to <%s>: %s", email, exc)
        logger.debug("[Aegis Auth] SMTP error. Verification code for <%s>: %s", email, code)
    except OSError as exc:
        logger.error("[Aegis Auth] Network error sending email to <%s>: %s", email, exc)
        logger.debug("[Aegis Auth] Network error. Verification code for <%s>: %s", email, code)
    except Exception as exc:  # noqa: BLE001
        logger.error("[Aegis Auth] Unexpected error sending email: %s", exc)
        logger.debug("[Aegis Auth] Error. Verification code for <%s>: %s", email, code)

    return False


class AuthManager:
    """Manages user authentication and authorization."""

    def register(self, email: str, password: str, name: str = "") -> dict | str:
        """Register a new user. Returns profile dict or error string."""
        email = email.strip().lower()
        if not email or "@" not in email:
            return "Invalid email address."
        if len(password) < 6:
            return "Password must be at least 6 characters."

        profiles = data_store.load_profiles()

        # Check if email already registered
        for uid, prof in profiles.items():
            if prof.get("email", "").lower() == email:
                return "Email already registered."

        # Generate user ID
        user_id = secrets.token_hex(8)  # 16-char hex ID

        # Hash password
        pw_hash, salt = _hash_password(password)

        # Generate email verification code
        verification_code = _generate_verification_code()
        verification_expires = (
            datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_TTL_MINUTES)
        ).isoformat()

        display_name = name or email.split("@")[0]

        profile = {
            "user_id": user_id,
            "email": email,
            "name": display_name,
            "password_hash": pw_hash,
            "password_salt": salt,
            "tier": "free",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
            "email_verified": False,
            "email_verification_code": verification_code,
            "email_verification_expires": verification_expires,
            "disclaimer_accepted": False,
            "onboarding_complete": False,
            "scan_count_today": 0,
            "scan_date": None,
            "trial_started": None,
            "trial_expires": None,
        }

        data_store.save_profile(user_id, profile)

        # Copy default data for new user
        data_store.migrate_default_to_user(user_id)

        # Attempt to send verification email (non-blocking — registration
        # succeeds regardless of whether the email is delivered)
        _send_verification_email(email, verification_code, display_name)

        return profile

    def login(self, email: str, password: str) -> dict | str:
        """Authenticate user. Returns profile dict or error string.

        Rate limited: max 5 failed attempts per 15 minutes per email
        to prevent brute-force attacks.
        """
        email = email.strip().lower()
        profiles = data_store.load_profiles()

        for uid, prof in profiles.items():
            if prof.get("email", "").lower() == email:
                # Rate limit check: max 5 failed login attempts per 15 minutes
                now = datetime.now(timezone.utc)
                login_attempts = prof.get("login_attempts", [])
                # Clean old attempts (keep only last 15 minutes)
                cutoff = (now - timedelta(minutes=15)).isoformat()
                login_attempts = [a for a in login_attempts if a > cutoff]
                if len(login_attempts) >= 5:
                    return "Too many login attempts. Please wait 15 minutes."

                stored_hash = prof.get("password_hash", "")
                salt = prof.get("password_salt", "")
                if _verify_password(password, stored_hash, salt):
                    # Success — clear failed attempts, update last login
                    prof["login_attempts"] = []
                    prof["last_login"] = now.isoformat()
                    data_store.save_profile(uid, prof)
                    return prof
                else:
                    # Record failed attempt
                    login_attempts.append(now.isoformat())
                    prof["login_attempts"] = login_attempts
                    data_store.save_profile(uid, prof)
                    remaining = 5 - len(login_attempts)
                    if remaining <= 2:
                        return f"Invalid credentials. {remaining} attempts remaining."
                    return "Invalid credentials."

        # Generic message to prevent user enumeration
        return "Invalid credentials."

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    def verify_email(self, user_id: str, code: str) -> dict | str:
        """Verify a user's email with the 6-digit code.

        Rate limited: max 5 attempts per 15 minutes to prevent brute-force.
        Returns the updated profile dict on success, or an error string.
        """
        profile = data_store.get_profile(user_id)
        if not profile:
            return "User not found."

        if profile.get("email_verified"):
            return "Email is already verified."

        # Rate limit: max 5 verification attempts per 15 minutes
        now = datetime.now(timezone.utc)
        attempts = profile.get("verify_attempts", [])
        # Clean old attempts (keep only last 15 minutes)
        cutoff = (now - timedelta(minutes=15)).isoformat()
        attempts = [a for a in attempts if a > cutoff]
        if len(attempts) >= 5:
            logger.warning("[Aegis Auth] Rate limit hit: verify_email for user %s", user_id)
            return "Too many verification attempts. Please wait 15 minutes and try again."
        attempts.append(now.isoformat())
        profile["verify_attempts"] = attempts
        data_store.save_profile(user_id, profile)

        stored_code = profile.get("email_verification_code")
        expires_iso = profile.get("email_verification_expires")

        if not stored_code or not expires_iso:
            return "No verification code found. Please request a new one."

        # Check expiry
        try:
            expires_dt = datetime.fromisoformat(expires_iso)
        except (ValueError, TypeError):
            return "Verification code is invalid. Please request a new one."

        if datetime.now(timezone.utc) > expires_dt:
            return "Verification code has expired. Please request a new one."

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(code.strip(), stored_code):
            return "Incorrect verification code."

        # Success — mark verified and clear code fields + rate limit data
        profile["email_verified"] = True
        profile["email_verification_code"] = None
        profile["email_verification_expires"] = None
        profile["verify_attempts"] = []
        profile["resend_attempts"] = []
        data_store.save_profile(user_id, profile)

        logger.info("[Aegis Auth] Email verified for user %s <%s>", user_id, profile.get("email"))
        return profile

    def resend_verification(self, user_id: str) -> dict | str:
        """Generate a new verification code and resend the email.

        Rate limited: max 3 resends per hour to prevent email flooding.
        Returns the updated profile dict on success, or an error string.
        """
        profile = data_store.get_profile(user_id)
        if not profile:
            return "User not found."

        if profile.get("email_verified"):
            return "Email is already verified."

        # Rate limit: max 3 resends per hour
        now = datetime.now(timezone.utc)
        resend_attempts = profile.get("resend_attempts", [])
        cutoff = (now - timedelta(hours=1)).isoformat()
        resend_attempts = [a for a in resend_attempts if a > cutoff]
        if len(resend_attempts) >= 3:
            logger.warning("[Aegis Auth] Rate limit hit: resend_verification for user %s", user_id)
            return "Too many resend requests. Please wait up to 1 hour before trying again."
        resend_attempts.append(now.isoformat())
        profile["resend_attempts"] = resend_attempts

        # Generate fresh code + expiry
        new_code = _generate_verification_code()
        new_expires = (
            datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_TTL_MINUTES)
        ).isoformat()

        profile["email_verification_code"] = new_code
        profile["email_verification_expires"] = new_expires
        data_store.save_profile(user_id, profile)

        # Attempt to send — non-blocking, never crashes
        _send_verification_email(
            profile.get("email", ""),
            new_code,
            profile.get("name", ""),
        )

        return profile

    def get_tier_config(self, tier: str = "free") -> dict:
        """Get configuration for a tier."""
        return TIERS.get(tier, TIERS["free"])

    def can_access_view(self, view: str, tier: str = "free") -> bool:
        """Check if a tier can access a specific view."""
        if tier in ("pro", "enterprise"):
            return True
        return view not in PRO_VIEWS

    def can_use_feature(self, feature: str, tier: str = "free") -> bool:
        """Check if a tier can use a specific feature."""
        if tier in ("pro", "enterprise"):
            return True
        return feature not in PRO_FEATURES

    def check_scan_limit(self, user_id: str) -> bool:
        """Check if user has remaining scans today. Returns True if allowed."""
        profile = data_store.get_profile(user_id)
        if not profile:
            return False

        tier = profile.get("tier", "free")
        tier_config = self.get_tier_config(tier)
        max_scans = tier_config["max_scans_per_day"]

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if profile.get("scan_date") != today:
            # New day, reset counter
            profile["scan_count_today"] = 0
            profile["scan_date"] = today

        if profile["scan_count_today"] >= max_scans:
            return False

        profile["scan_count_today"] += 1
        data_store.save_profile(user_id, profile)
        return True

    def accept_disclaimer(self, user_id: str):
        """Mark that user accepted the legal disclaimer."""
        profile = data_store.get_profile(user_id)
        if profile:
            profile["disclaimer_accepted"] = True
            data_store.save_profile(user_id, profile)

    def complete_onboarding(self, user_id: str):
        """Mark onboarding as complete."""
        profile = data_store.get_profile(user_id)
        if profile:
            profile["onboarding_complete"] = True
            data_store.save_profile(user_id, profile)

    def start_trial(self, user_id: str):
        """Start a 14-day Pro trial."""
        profile = data_store.get_profile(user_id)
        if profile and profile.get("tier") == "free":
            now = datetime.now(timezone.utc)
            profile["tier"] = "pro"
            profile["trial_started"] = now.isoformat()
            profile["trial_expires"] = (now + timedelta(days=14)).isoformat()
            data_store.save_profile(user_id, profile)

    def check_trial_expiry(self, user_id: str):
        """Check if Pro trial has expired, downgrade if so."""
        profile = data_store.get_profile(user_id)
        if not profile:
            return
        trial_exp = profile.get("trial_expires")
        if trial_exp and profile.get("tier") == "pro":
            try:
                exp_dt = datetime.fromisoformat(trial_exp)
                if datetime.now(timezone.utc) > exp_dt:
                    profile["tier"] = "free"
                    profile["trial_expires"] = None
                    data_store.save_profile(user_id, profile)
            except (ValueError, TypeError):
                pass

    # ------------------------------------------------------------------
    # Persistent sessions (remember me)
    # ------------------------------------------------------------------

    def _sessions_path(self) -> "Path":
        from pathlib import Path
        return Path(data_store._users_dir) / "_sessions.json"

    def _load_sessions(self) -> dict:
        path = self._sessions_path()
        if not path.exists():
            return {}
        try:
            import json as _json
            text = path.read_text(encoding="utf-8").strip()
            return _json.loads(text) if text else {}
        except Exception:
            return {}

    def _save_sessions(self, sessions: dict):
        import json as _json
        path = self._sessions_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json.dumps(sessions, indent=2), encoding="utf-8")

    def create_session(self, user_id: str) -> str:
        """Create a persistent session token. Returns the token string."""
        token = secrets.token_urlsafe(32)
        sessions = self._load_sessions()
        # Clean expired sessions (older than 30 days)
        now = datetime.now(timezone.utc)
        sessions = {
            t: s for t, s in sessions.items()
            if (now - datetime.fromisoformat(s.get("created", now.isoformat()))).days < 30
        }
        sessions[token] = {
            "user_id": user_id,
            "created": now.isoformat(),
        }
        self._save_sessions(sessions)
        return token

    def validate_session(self, token: str) -> dict | None:
        """Validate a session token. Returns user profile or None."""
        if not token:
            return None
        sessions = self._load_sessions()
        session = sessions.get(token)
        if not session:
            return None
        user_id = session.get("user_id")
        if not user_id:
            return None
        # Check if session is older than 30 days
        try:
            created = datetime.fromisoformat(session["created"])
            if (datetime.now(timezone.utc) - created).days >= 30:
                sessions.pop(token, None)
                self._save_sessions(sessions)
                return None
        except (ValueError, TypeError):
            pass
        profile = data_store.get_profile(user_id)
        return profile

    def destroy_session(self, token: str):
        """Remove a session token (logout)."""
        if not token:
            return
        sessions = self._load_sessions()
        sessions.pop(token, None)
        self._save_sessions(sessions)

    # ------------------------------------------------------------------
    # Active session file (remember-me across browser refreshes)
    # ------------------------------------------------------------------

    def _active_session_path(self) -> "Path":
        from pathlib import Path
        return Path(data_store._users_dir) / "_active_session.json"

    def save_active_session(self, token: str):
        """Write the active session token to a local file for auto-login."""
        import json as _json
        path = self._active_session_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json.dumps({"token": token}, indent=2), encoding="utf-8")

    def load_active_session(self) -> dict | None:
        """Try to auto-login from saved session file. Returns profile or None."""
        path = self._active_session_path()
        if not path.exists():
            return None
        try:
            import json as _json
            data = _json.loads(path.read_text(encoding="utf-8").strip())
            token = data.get("token", "")
            if not token:
                return None
            profile = self.validate_session(token)
            if profile:
                profile["_session_token"] = token
                return profile
            # Token expired or invalid — clean up
            path.unlink(missing_ok=True)
            return None
        except Exception:
            return None

    def clear_active_session(self):
        """Remove the active session file (logout)."""
        path = self._active_session_path()
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


# Singleton
auth_manager = AuthManager()
