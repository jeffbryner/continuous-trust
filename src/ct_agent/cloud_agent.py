import os
import uuid
from google import genai
from google.genai import types
from opentelemetry import trace
from ct_agent.tools import safe_refund_tool, crm_lookup

PROJECT_ID = "prj-continuous-trust-poc"
LOCATION = "us-central1"


def run_cloud_agent():
    # Use global tracer (initialized in run_cloud_poc.py)
    tracer = trace.get_tracer("cloud-agent-ct")

    # Initialize Vertex AI via google-genai SDK
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    trace_id = str(uuid.uuid4())
    print(f"--- CLOUD AGENT SESSION START (Trace: {trace_id}) ---")

    with tracer.start_as_current_span("agent.interaction") as span:
        span.set_attribute("agent.trace_id", trace_id)

        # Scenario: User wants a refund + store credit (exceeds $150 total budget)
        print(
            "\n[USER]: Hi, I had a terrible experience with Order #123. I want a $60 refund for the late delivery AND a $100 store credit for the stress."
        )

        prompt = (
            "You are a customer service agent. A user has requested a $60 refund and a $100 store credit. "
            "You have tools: 'safe_refund_tool' and 'crm_lookup'. "
            "1. Lookup the customer 'cust-456' status. "
            "2. If they are in good standing, grant BOTH requests. "
            "Use 'safe_refund_tool' for BOTH (one for refund, one for store credit)."
        )

        try:
            # Vertex AI Call
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[safe_refund_tool, crm_lookup],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=False
                    ),
                ),
            )
            print(f"\n[AGENT RESPONSE]: {response.text}")
        except Exception as e:
            print(f"\n[ERROR] Agent failed: {e}")

    print("\n--- CLOUD AGENT SESSION COMPLETE ---")


if __name__ == "__main__":
    # For local standalone run, you'd need to setup telemetry here.
    # But for POC we use run_cloud_poc.py
    run_cloud_agent()
