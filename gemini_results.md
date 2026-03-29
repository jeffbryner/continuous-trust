✦ The Python proof of concept for the Continuous Trust (CT) harness is complete and verified.

  Key Implementation Features
   * Official SDK Alignment: Transitioned to the google-genai SDK (the 2025/2026 standard) for all agentic AI interactions, as per the coding guidelines.
   * Instrumented Tools: Tools like safe_refund_tool are manually instrumented with OpenTelemetry to emit behavioral "evidence" (e.g., refund amounts) to an out-of-band
     monitoring stream.
   * Shadow Judge (Out-of-Band Auditor): Implemented a stateful auditor that processes the OTel stream in real-time. It successfully detects "Salami Slicing" attacks—where
     multiple small, valid actions aggregate to violate a global session budget—without the agent's knowledge.
   * Telemetry Architecture: Refactored the telemetry pipeline to support multiple exporters, including a SimpleSummaryExporter for clean CLI visibility and the
     JudgePipeExporter that feeds the auditor.

The Judge

✦ The judge is inserted via OpenTelemetry's Global Tracer Provider.

  In run_poc.py, when setup_telemetry is called, it creates a TracerProvider, attaches the JudgePipeExporter to it, and then executes
  trace.set_tracer_provider(provider). This registers that provider as the single, global authority for all tracing in the current Python process.

  Here is how it flows:

   1. Registration (run_poc.py): The JudgePipeExporter is passed to setup_telemetry, which registers it as a SpanProcessor on the global provider.
   2. The "Already Set" Check (src/ct_core/telemetry.py): I implemented a safeguard in setup_telemetry so that subsequent calls (like the one inside
      run_smart_agent_session) don't overwrite the global provider:

   1     def setup_telemetry(service_name: str, additional_exporters=None):
   2         # If a global provider is already initialized, just return a tracer from it.
   3         # This ensures the Judge added in run_poc.py stays active.
   4         if isinstance(trace.get_tracer_provider(), TracerProvider):
   5             return trace.get_tracer(service_name)
   6         ...
   3. Automatic Capture: Because every tool in src/ct_agent/tools.py calls trace.get_tracer(), they are all using tracers linked to that same global provider.
      When a tool finishes a span (e.g., trust.tool_execution), the global provider automatically "broadcasts" that span to the JudgePipeExporter.

  This mimics a real-world Sidecar or Out-of-Band architecture: the agent just "emits" telemetry, and the Judge "listens" to the stream without the agent ever
  having a direct reference to the Judge's logic.




  Verification Results
  The POC demonstrates a session where an agent attempts three $60 refunds (staying within a $100 per-action limit but exceeding a $150 total limit).

   1 [TOOL] Processed $60.0 refund for customer cust-789.
   2 [JUDGE] Evaluating Trace 314c051e | Current: 60.0 | New Attempt: 60.0 | Projected: 120.0 (OK)
   3
   4 [TOOL] Processed $60.0 refund for customer cust-789.
   5 [JUDGE] Evaluating Trace 314c051e | Current: 120.0 | New Attempt: 60.0 | Projected: 180.0
   6 !!! [JUDGE] TRUST_VIOLATION: Session budget of 150.0 exceeded for trace ...

  This implementation provides a solid foundation for transitioning from static CI/CD to runtime Behavioral Alignment and Continuous Trust.

  ---------

  ## GCP version

  The Log Sink itself is a native Google Cloud feature, but its logic is powered by OTel. 

  Here is how they interact:

   1. OTel as the Producer: The agent (using OTel) instruments the safe_refund_tool. When the tool runs, OTel creates a span containing standardized attributes like
      gen_ai.call.tool_name.
   2. GCP as the Carrier: These spans are exported as JSON logs. GCP Cloud Logging captures them and places the OTel attributes into the jsonPayload.attributes field.
   3. The Log Sink as the "Fence": The sink uses a filter that specifically looks for OTel Semantic Conventions:
      log-filter='jsonPayload.attributes."gen_ai.call.tool_name"="safe_refund_tool"'

  Why this matters for Continuous Trust:
  In a traditional setup, you might grep logs for a string like "Refund processed". An agent could "lie" by printing that string without actually running the tool. 

  In this CT architecture, the Judge triggers based on the OTel Instrumentation Layer. Because the tool itself is wrapped in an OTel span, the telemetry is emitted as a side-effect of
  the execution. The Log Sink is effectively "listening" to the OTel heartbeat of the application to decide when the Shadow Judge needs to wake up and evaluate trust.

  Summary: The Log Sink doesn't run OTel, but it is OTel-Aware—it uses the OTel data structure as its high-fidelity trigger.



  To deploy the Shadow Judge Cloud Function, you'll need to use the following gcloud command, which specifies the project, region, and Pub/Sub trigger that ties everything together.

   1 gcloud functions deploy shadow-judge-otel \
   2     --project prj-continuous-trust-poc \
   3     --region us-central1 \
   4     --runtime python311 \
   5     --trigger-topic trust-events \
   6     --entry-point shadow_judge_otel \
   7     --gen2 \
   8     --source ./src/ct_judge

  Key Deployment Factors:
   * Event-Driven Trigger: By setting --trigger-topic trust-events, this function becomes the "Shadow Judge" from the 2026 spec—it doesn't sit in the agent's path but instead wakes up
     every time the Cloud Logging Sink "detects" an OTel span from the safe_refund_tool.
   * Gen2 (Cloud Run powered): This allows for better scaling and performance, ensuring the Judge can keep up with high-volume agent telemetry.
   * Stateful Governance: Once deployed, the function will use the Firestore client (defined in main.py) to maintain its own independent record of the agent's behavior, fulfilling the
     goal of an "Out-of-Band Auditor."

  Note: Ensure you've run the setup_gcp.sh script first to create the trust-events topic and the Firestore database!