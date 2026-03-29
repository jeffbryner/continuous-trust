#!/bin/bash
# Continuous Trust GCP Setup Script

PROJECT_ID="prj-continuous-trust-poc"
REGION="us-central1"

echo "Setting up GCP Project: $PROJECT_ID"

# 1. Enable APIs
gcloud services enable \
    aiplatform.googleapis.com \
    cloudtrace.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com \
    run.googleapis.com \
    --project $PROJECT_ID

# 2. Create Firestore Database (Native mode)
gcloud firestore databases create --location=$REGION --project $PROJECT_ID

# 3. Create a Pub/Sub Topic for Trust Events
gcloud pubsub topics create trust-events --project $PROJECT_ID

# 4. Create Log Sink to trigger the Judge
# This filter catches our OTel spans if they are exported to Cloud Logging
gcloud logging sinks create judge-trigger-sink \
    pubsub.googleapis.com/projects/$PROJECT_ID/topics/trust-events \
    --log-filter='jsonPayload.attributes."gen_ai.call.tool_name"="safe_refund_tool"' \
    --project $PROJECT_ID

echo "GCP Setup Complete. Note: You may need to grant Pub/Sub Publisher role to the Logging service account."
