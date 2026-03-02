"""
Project Aegis — Sentry Error Tracking Setup
=============================================
Add these lines to the TOP of dashboard/app.py (after imports) to enable
automatic error tracking.

Install: pip install sentry-sdk
Signup:  https://sentry.io (free tier: 5k errors/month)

After signing up, replace the DSN below with your project DSN.
"""

import os

import sentry_sdk

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Performance monitoring — sample 10% of transactions
        traces_sample_rate=0.1,
        # Only send errors from our code, not library internals
        in_app_include=["src", "dashboard"],
        # Attach server name for multi-server identification
        server_name="aegis-terminal",
        # Environment tag
        environment=os.environ.get("AEGIS_ENV", "production"),
    )
    print("[Sentry] Error tracking enabled")
else:
    print("[Sentry] No DSN configured — error tracking disabled")
