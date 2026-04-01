#!/bin/bash
# Continuous Trust GCP Setup Script

PROJECT_ID="prj-continuous-trust-poc"
REGION="us-central1"

echo "Setting up GCP Project: $PROJECT_ID"

# 1. Enable APIs
gcloud services enable \
    aiplatform.googleapis.com \
    eventarc.googleapis.com \
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
#To deploy the Shadow Judge Cloud Function, you'll need to use the following gcloud command, which specifies the project, region, and Pub/Sub trigger that ties everything together.

gcloud projects add-iam-policy-binding prj-continuous-trust-poc \
 --member=serviceAccount:561283385503-compute@developer.gserviceaccount.com \
 --role=roles/cloudbuild.builds.builder

gcloud functions deploy shadow-judge-otel \
--project prj-continuous-trust-poc \
--region us-central1 \
--runtime python311 \
--trigger-topic trust-events \
--entry-point shadow_judge_otel \
--gen2 \
--source ./src/ct_judge    

#permissions
gcloud projects add-iam-policy-binding prj-continuous-trust-poc \
 --member=serviceAccount:service-561283385503@gcp-sa-logging.iam.gserviceaccount.com \
 --role=roles/pubsub.publisher 
# 5. Grant the identity used by the Pub/Sub subscription the Invoker rights
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting Service Account ($DEFAULT_SA) Invoker rights on the Shadow Judge..."

gcloud run services add-iam-policy-binding shadow-judge-otel \
    --member="serviceAccount:$DEFAULT_SA" \
    --role="roles/run.invoker" \
    --region $REGION \
    --project $PROJECT_ID

# 6. Grant Firestore and Trace permissions to the Shadow Judge identity
echo "Granting Firestore User and Cloud Trace Agent rights to $DEFAULT_SA..."

for ROLE in "roles/datastore.user" "roles/cloudtrace.agent"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$DEFAULT_SA" \
        --role="$ROLE" \
        --no-user-output-enabled
done

echo "GCP Setup Complete. The Shadow Judge is now fully authorized for Telemetry, Trace, and State (Firestore)."
