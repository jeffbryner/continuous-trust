Here is a comprehensive technical specification of the **Continuous Trust (CT)** architecture we brainstormed.

---

# Technical Specification: Continuous Trust (CT) for Agentic Workflows

## 1. Overview
The AI era has a unique "Day 2" problem: CI/CD was designed for code that is static; Agentic workflows are dynamic.

If CI/CD is about verification of the artifact (Is the code correct before I ship it?), then Continuous Trust (CT) is about verification of the behavior (Is the agent still acting within its intent while it’s running?).

Continuous Trust (CT) is the evolution of CI/CD for the agentic era. While CI/CD verifies **code artifacts** before deployment, CT verifies **behavioral alignment** during runtime. It transitions governance from static binary tests to probabilistic, stateful monitoring.


## The Shift: From "Binary Pass" to "Probabilistic Trust"
In traditional CI/CD, a test is binary: it passes or it fails. In agentic workflows, an agent might complete a task successfully but use a "risky" reasoning path to get there. Continuous Trust moves the goalposts:

| Feature | Traditional CI/CD | Continuous Trust (Agentic) |
| :--- | :--- | :--- |
| **Focus** | Functional correctness (Did it crash?) | Behavioral alignment (Did it hallucinate or overstep?) |
| **Validation** | Unit & Integration tests | Real-time "Guardrails" & Semantic Evals |
| **Timing** | Pre-deployment (The Gate) | Runtime (The Fence) |
| **Failure Mode** | "Loud" (Build fails) | "Silent" (Agent drifts or becomes biased) |

---



## 2. The Bookends of Continuous Trust
### Pre-flight Intent Manifest
Every agentic task must begin with a signed JSON manifest that defines the "Contract" for that specific session.

```json
{
  "metadata": {
    "agent_id": "refund-bot-v2",
    "trace_id": "otel-trace-uuid-12345"
  },
  "intent": {
    "task_goal": "Process customer refund for late delivery",
    "authorized_tools": ["stripe_refund_api", "crm_lookup"],
    "constraints": {
      "max_per_action": 100.0,
      "max_session_total": 150.0,
      "data_access": "billing_only"
    }
  }
}
```

or potentially a structure that includes the agent's motive 

```json
{
  "agent_id": "billing-bot-04",
  "task_intent": "process_refund",
  "constraints": {
    "max_amount": 500,
    "allowed_tools": ["stripe_api", "zendesk_lookup"],
    "data_perimeter": ["customer_billing_only"]
  },
  "justification": "Customer requested refund for Order #123 due to shipping delay."
}
```

---
###  Post-Operation: The Audit Trail Inspection

After the action, the CT pipeline compares the Actual Trace against the Intent Manifest. This is where you verify "Alignment."

An Audit Trail in a CT world needs to go beyond being just a log file by becoming a Reasoning Trace. It answers:

    Tool Usage: Did it use a tool not listed in the manifest?

    Logic Check: Did the agent "hallucinate" a reason to bypass a constraint?

    Semantic Drift: Did the tone or the data handled shift away from the intended task?


## 3. Instrumentation Strategies
### Purpose built data structures
One could easily see a purpose-build datastore of agent audit trails registering intent and actions  allowing for a Post-operation judge to determine alignment and rating the agent's trust over time

TODO: Firebase implementation of intent, action, judge



### OpenTelemetry
Alternatively using current standards, tool calls could be instrumented to emit **OTel Spans** using 2026 Semantic Conventions. This prevents the agent from "lying" about its actions.

### Python MVP: Instrumented Tool
```python
from opentelemetry import trace
from opentelemetry.semconv.ai import SpanAttributes

tracer = trace.get_tracer("agent.continuous_trust")

def safe_refund_tool(amount: float, customer_id: str):
    with tracer.start_as_current_span("trust.tool_execution") as span:
        # Record the 'Evidence' for the Shadow Judge
        span.set_attribute("trust.requested_amount", amount)
        span.set_attribute("trust.customer_id", customer_id)
        
        # Logic for tool execution goes here...
        return f"Processed ${amount} refund."
```

---

## 4. The Shadow Judge (Stateful Monitoring)
The Shadow Judge is an out-of-band process that aggregates session data to catch "Salami Slicing" attacks (multiple small actions exceeding a total limit).



### Logic for Cumulative Trust Verification
```python
# Conceptual logic for a Shadow Judge watching the OTel stream
trace_budgets = {} # In production, use business rule store, yaml, etc

def evaluate_session_trust(trace_id, requested_amount):
    current_total = trace_budgets.get(trace_id, 0.0)
    new_total = current_total + requested_amount
    
    if new_total > 150.0:
        # Trigger 'Kill Switch' via Google Cloud Alert
        return "TRUST_VIOLATION: Session budget exceeded."
    
    trace_budgets[trace_id] = new_total
    return "TRUST_OK"
```

---

## 5. Implementation Roadmap (Maturity Phases)

| Phase | Focus | Primary Tools |
| :--- | :--- | :--- |
| **Phase 1: Visibility** | Instrument all agents with OTel. | Google Cloud Trace, OTel SDK |
| **Phase 2: Guardrails** | Implement stateless "Gate" checks in tools. | Pydantic, JSON Schema |
| **Phase 3: Governance** | Deploy "Shadow Judge" for stateful session limits. | Cloud Functions, Log Metrics |
| **Phase 4: Alignment** | Automate "LLM-as-a-Judge" for semantic drift. | Arize Phoenix, Vertex AI |

---

## 6. GCP Integration Commands
To link your Gemini-powered agent to the Google Cloud OTel pipeline:

```bash
# Set the 2026 Unified Telemetry Endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="https://telemetry.googleapis.com"
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Install the Google-specific instrumentor
pip install opentelemetry-instrumentation-google-genai
```

---

To catch "Salami Slicing" (multiple small actions adding up to a violation), we move from a single-call gate to a **Shadow Judge architecture**. 

In this 2026 model, the "Judge" isn't part of your agent's code. It's a separate process—either a **GCP Log-Based Metric** (for simple numbers) or a **Cloud Function** (for complex reasoning)—that watches the OpenTelemetry (OTel) stream.

---

### The Architecture: "The Out-of-Band Auditor"



1. **The Agent:** Performs actions unaware of the specific aggregate limit.
2. **The Collector:** Telemetry flows to Google Cloud via OTLP.
3. **The Shadow Judge:** A background process (Log Metric or Cloud Function) calculates the session total and flags the "Trust Drift."

---

### Option A: The "Quick Win" (GCP Log-Based Metric)
If you just want to track numbers (like refund amounts) across a session, you can use **Cloud Logging** to create a cumulative counter without changing your code.

**How to set it up in the GCP Console:**
1.  **Filter:** Create a filter for your agent's tool logs:
    `jsonPayload.attributes."trust.requested_amount"=*`
2.  **Create Metric:** Select **Create Metric** -> **Counter**.
3.  **Grouping:** Set the "Field Name" to `jsonPayload.attributes."trace_id"`. This tells GCP to sum the amounts *per session*.
4.  **Alert:** Create a **Threshold Alert**. If the `sum` of `requested_amount` for any single `trace_id` exceeds 150 within a 10-minute window, GCP sends a critical alert to PagerDuty/Slack.

---

### Option B: The "Shadow Judge" (Python Cloud Function)
For the "tricked agent" scenario, you need to analyze **Intent**. A Shadow Judge can detect if the agent is "being too nice" by looking at the *text* of the reasoning.

**The MVP Shadow Judge Code:**
This function is triggered every time an OTel span is exported.

```python
import functions_framework
from google.cloud import monitoring_v3

@functions_framework.cloud_event
def shadow_judge_otel(cloud_event):
    # 1. Capture the OTel span data from the event
    data = cloud_event.data
    trace_id = data['traceId']
    tool_name = data['attributes'].get('gen_ai.call.tool_name')
    amount = float(data['attributes'].get('trust.requested_amount', 0))

    # 2. Check the "Session Store" (e.g., Firestore or Memorystore)
    session_total = get_session_total(trace_id) + amount
    
    # 3. THE "SHADOW" EVALUATION
    # Even if the agent thinks it's okay, the Judge has the final word.
    if session_total > 150.0:
        trigger_security_kill_switch(trace_id, reason="Aggregate Budget Exceeded")
        log_trust_violation(trace_id, amount, "Salami Slicing Detected")

    save_session_total(trace_id, session_total)
```

---

### 🟢 Why this is the "Uncharted Territory" Phase

This setup provides **True Continuous Trust** because:

* **Zero Bypass:** Because the Judge is "Shadow" (out-of-band), the agent cannot see or manipulate the budget logic. 
* **Agnosticism:** It doesn't matter if you use the Gemini SDK, LangChain, or a custom script. As long as they emit OTel spans with an `amount` attribute, the Judge catches them.
* **Behavioral Identity:** You can begin to score agents not just on "Did it work?" but on **"Is this agent's identity drifting?"** (e.g., It's becoming 20% more likely to grant refunds on Fridays).

### Summary of Maturity
* **Phase 1:** OTel Wrappers (The Evidence).
* **Phase 2:** Log-Based Metrics (The Counter).
* **Phase 3:** Shadow Judge (The Auditor).

## Logistics
 - Use Python
 - Always use uv to manage the python virtual environment
 - Use GCP project prj-continuous-trust-poc
 - Always use genai or adk for google AI development in vertex