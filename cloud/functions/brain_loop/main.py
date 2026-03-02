"""Cloud Function: Run Aegis Brain autonomous scan loop.

Triggered by Cloud Scheduler every 30 minutes.
Performs: market scan, news sentiment, news impact, auto-trade, predictions.
Stores all results in Google Cloud Storage.

Cost: ~$8/month (48 invocations/day, ~2min each)
"""

import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import functions_framework
from google.cloud import storage

# Add src/ to path so we can import aegis modules
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

BUCKET_NAME = "aegis-market-data"


def upload_to_gcs(data: dict, blob_name: str) -> None:
    """Upload JSON data to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        json.dumps(data, indent=2, default=str),
        content_type="application/json",
    )


@functions_framework.http
def brain_loop(request):
    """HTTP-triggered Cloud Function. Runs the full brain scan cycle.

    This is a simplified version of aegis_brain.py's main loop,
    adapted for serverless execution.
    """
    start = time.time()
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps_completed": [],
        "errors": [],
        "scan_results": [],
    }

    try:
        # Step 1: Market scan
        from market_scanner import scan_all
        scan_results = scan_all()
        report["steps_completed"].append("market_scan")
        report["scan_count"] = len(scan_results)

        # Upload scan results to GCS
        scan_summary = {}
        for r in scan_results:
            name = r.get("name", "Unknown")
            scan_summary[name] = r
        upload_to_gcs(scan_summary, "scan/watchlist_summary.json")

    except Exception as e:
        report["errors"].append(f"market_scan: {str(e)}")

    try:
        # Step 2: News impact analysis
        from news_impact import NewsImpactEngine
        engine = NewsImpactEngine()
        impact_count = 0
        for sr in scan_results if 'scan_results' in dir() else []:
            try:
                engine.analyze(sr.get("name", ""), news_data=sr.get("news"))
                impact_count += 1
            except Exception:
                pass
        if impact_count > 0:
            report["steps_completed"].append("news_impact")
            report["impact_count"] = impact_count

    except Exception as e:
        report["errors"].append(f"news_impact: {str(e)}")

    try:
        # Step 3: Prediction validation
        from market_learner import MarketLearner
        learner = MarketLearner()
        validated = learner.validate_predictions()
        report["steps_completed"].append("prediction_validation")
        report["predictions_validated"] = validated

    except Exception as e:
        report["errors"].append(f"prediction_validation: {str(e)}")

    # Upload brain report
    report["duration_s"] = round(time.time() - start, 2)
    try:
        upload_to_gcs(report, "brain/last_cycle_report.json")
    except Exception as e:
        report["errors"].append(f"report_upload: {str(e)}")

    status = "ok" if not report["errors"] else "partial"
    return json.dumps({
        "status": status,
        "steps": report["steps_completed"],
        "errors": report["errors"],
        "duration_s": report["duration_s"],
    })
