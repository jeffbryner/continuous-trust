import os
from ct_core.telemetry import setup_telemetry, GCPLoggingExporter
from ct_agent.cloud_agent import run_cloud_agent

# GCP Configuration
PROJECT_ID = "prj-continuous-trust-poc"

def run_integrated_cloud_poc():
    """
    Runs the Continuous Trust POC using live Google Cloud infrastructure.
    
    This script:
    1. Initializes OTel with the GCPLoggingExporter.
    2. Runs a Smart Agent using Vertex AI.
    3. Tool calls trigger the live Cloud Function (Shadow Judge) via Log Sinks.
    """
    print("==================================================")
    print("   CONTINUOUS TRUST: CLOUD DEPLOYMENT DEMO        ")
    print("==================================================")
    print(f"Project: {PROJECT_ID}")
    print("Judge: Cloud Function (shadow-judge-otel)")
    print("State: Firestore (ct_sessions)")
    print("==================================================\n")

    # 1. Setup Telemetry to route Evidence to Cloud Logging
    gcp_exporter = GCPLoggingExporter(project_id=PROJECT_ID)
    setup_telemetry("continuous-trust-cloud-poc", additional_exporters=[gcp_exporter])
    
    # 2. Run the Cloud Agent
    # This agent will autonomously decide to process a refund and store credit,
    # which will aggregate to a budget violation caught by the Cloud Judge.
    run_cloud_agent()

    print("\n==================================================")
    print("   CLOUD POC COMPLETE                             ")
    print("   Check Firestore for Trace evaluation results.  ")
    print("==================================================")

if __name__ == "__main__":
    # Ensure GCP Credentials are set:
    # export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
    run_integrated_cloud_poc()
