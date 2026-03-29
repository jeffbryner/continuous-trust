import os
import base64
import json
import logging
import functions_framework
from google.cloud import firestore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Firestore client
db = firestore.Client()
COLLECTION = "ct_sessions"
BUDGET_LIMIT = 150.0

@functions_framework.cloud_event
def shadow_judge_otel(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub topic (from Cloud Logging Sink).
    Evaluates the 'Continuous Trust' of an agentic session.
    """
    # 1. Decode Pub/Sub message
    try:
        data_bytes = base64.b64decode(cloud_event.data["message"]["data"])
        log_entry = json.loads(data_bytes)
    except Exception as e:
        logger.error(f"Failed to decode Pub/Sub message: {e}")
        return

    # 2. Extract trace and tool attributes
    attrs = log_entry.get("jsonPayload", {}).get("attributes", {})
    trace_id = attrs.get("trust.trace_id", "unknown")
    amount = float(attrs.get("trust.requested_amount", 0.0))
    tool_name = attrs.get("gen_ai.call.tool_name")

    if trace_id == "unknown":
        logger.warning("[JUDGE] No trace_id found in event. Skipping evaluation.")
        return

    # 3. Stateful Budget Check via Firestore
    doc_ref = db.collection(COLLECTION).document(trace_id)
    doc = doc_ref.get()
    
    current_total = doc.to_dict().get("total_amount", 0.0) if doc.exists else 0.0
    new_total = current_total + amount
    
    logger.info(f"[JUDGE] Evaluating Trace: {trace_id} | Tool: {tool_name} | Amount: {amount} | Projected: {new_total}")

    # 4. Violation Check
    if new_total > BUDGET_LIMIT:
        logger.error(f"!!! [TRUST_VIOLATION] Budget of {BUDGET_LIMIT} exceeded for {trace_id} !!!")
        status = "VIOLATION"
    else:
        status = "OK"

    doc_ref.set({
        "total_amount": new_total,
        "status": status,
        "last_tool": tool_name,
        "updated_at": firestore.SERVER_TIMESTAMP
    }, merge=True)

    return "Processed"
