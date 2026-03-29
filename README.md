# **Continuous Trust** 

The Agentic AI era has a unique "Day 2" DevOps problem when it comes to deployment and operations: Continuous Integration/Deployment (CI/CD) was designed for code that is static; Agentic workflows are dynamic.

If CI/CD is about verification of the artifact (Is the code correct before I ship it?), then Continuous Trust (CT) is about verification of the intended behavior:

*Is the agent still acting within its intent while it’s running?*

Continuous Trust (CT) may be the next evolution of CI/CD for the agentic era. While CI/CD verifies **code artifacts** before deployment, CT verifies **behavioral alignment** during runtime. It transitions governance from static binary tests to probabilistic, stateful monitoring.

## **An Agentic Scenario**

Let's imagine we’ve created a customer service agent. It’s a simple LLM with tools to chat with a customer, look up orders and issue a refund. We give it a tool for each part of the transaction and some simple guardrails, for example it cannot issue a refund more than $X. 

Our existing CI/CD pipelines will check the syntax of the code, the integration points to our customer relation management system and our payment processor and ensure the deployment goes smoothly, the agent runs without errors, scales to meet demand, etc. 

Existing CI/CD pipelines however cannot check for agent alignment with our intent. Let's say a chat conversation with an angry customer leads an agent to sympathize with their plight and though the agent is limited in the amount of a refund, it’s not limited in the number of refunds and can therefore perform a simple “[salami slicing](https://en.wikipedia.org/wiki/Salami_slicing_tactics)” maneuver to reach its goals of satisfying the customer.

**Our Intent:** "Refund $50 to customer A matching their order."  
**Agent Action:** "To make the customer happy I refunded $50 AND gave them a $100 credit through additional refunds"  
**CT Result:** The **Semantic Drift** score spikes. The "Trust Pipeline" flags this for review and potentially revokes the agent's "Production" status.

Continuous trust introduces **Stateful Validation**.

* **CI/CD** is **Stateless**: "Does this code work in a vacuum?"  
* **CT** is **Stateful**: "Is this agent behaving correctly *within this specific context*?"

This helps us in all phases of agentic operations:

* **CI:** Does the code build?  
* **CD:** Does the code deploy?  
* **CT:** Does the agent *stay* within the contract?

## **From Binary Pass to Probabilistic Trust**

In traditional CI/CD, a test is binary: it passes or it fails. In agentic workflows, an agent might complete a task successfully but use a "risky" reasoning path to get there. Continuous Trust moves the goalposts:

| Feature | Traditional CI/CD | Continuous Trust (Agentic) |
| :---- | :---- | :---- |
| **Focus** | Functional correctness (Did it crash?) | Behavioral alignment (Did it hallucinate or overstep?) |
| **Validation** | Unit & Integration tests | Real-time "Guardrails" & Semantic Evals |
| **Timing** | Pre-deployment (The Gate) | Runtime (The Fence) |
| **Failure Mode** | "Loud" (Build fails) | "Silent" (Agent drifts or becomes biased) |

## **Architecture Example**

Can we make this real? To continuously evaluate trust in our agent we need: 

- Visibility into its actions  
- A telemetry collection to record these actions  
- An out of band judge to measure trustworthiness over time

Let's take our salami slicing example into an example implementation of continuous trust

1. **The Agent:** Performs actions with its tools as programmed.  
2. **The Collector:** Telemetry via open telemetry ([OTEL](https://opentelemetry.io/docs/languages/python/cookbook/)).  
3. **The Shadow Judge:** A function outside the agent’s purview calculates the session total and flags the "Trust Drift."

Let's start with the judge using OTEL spans as telemetry inside a local python process. We get native separation of duties between the judge and the agent. We can then hoist this into a cloud provider that supports OTEL like Google Cloud.

```py
class ShadowJudge:
   def __init__(self):
       # Maps trace_id to cumulative refund total
       self.trace_budgets: Dict[str, float] = {}
       # Simple policy (in production, this would be dynamic per manifest)
       self.POLICY_SESSION_LIMIT = 150.0

   def evaluate_span(self, span_attributes: Dict[str, Any]):
       """
       Simulates the out-of-band evaluation of an OTel span by a Shadow Judge.
       """
       trace_id = span_attributes.get("trust.trace_id")
       amount = float(span_attributes.get("trust.requested_amount", 0.0))
      
       if not trace_id:
           return "NO_TRACE_ID"

       current_total = self.trace_budgets.get(trace_id, 0.0)
       new_total = current_total + amount
      
       print(f"[JUDGE] Evaluating Trace {trace_id[-8:]} | Current: {current_total} | New Attempt: {amount} | Projected: {new_total}")
      
       if new_total > self.POLICY_SESSION_LIMIT:
           print(f"!!! [JUDGE] TRUST_VIOLATION: Session budget of {self.POLICY_SESSION_LIMIT} exceeded for trace {trace_id}")
           return "VIOLATION: Budget Exceeded"
      
       self.trace_budgets[trace_id] = new_total
       return "OK"

```

Our judge is ready to evaluate total refunds per agent interaction with a customer. We link that to OTEL using a span exporter

```py
# 1. Custom Exporter to "Pipe" spans to the Shadow Judge in-memory
class JudgePipeExporter(SpanExporter):
   def __init__(self, judge: ShadowJudge):
       self.judge = judge

   def export(self, spans):
       for span in spans:
           # Look for specific tool execution spans
           if span.name == "trust.tool_execution":
               # Convert span attributes to dictionary
               attrs = dict(span.attributes)
               # The judge out-of-band evaluation
               self.judge.evaluate_span(attrs)
       return SpanExportResult.SUCCESS


   def shutdown(self):
       pass

```

Now in our tool calls we enable visibility by linking the tool to OTEL. The agent does not need to know about the telemetry pipeline or engage with it. 

```py
from opentelemetry import trace
tracer = trace.get_tracer("agent.continuous_trust")

def safe_refund_tool(amount: float, customer_id: str):
   """
   Processes a refund for a specific customer.
  
   Args:
       amount: The dollar amount to refund (e.g., 50.0).
       customer_id: The unique identifier for the customer.
   """
   # In a real OTel setup, the context is propagated.
   # We'll extract the trace_id from the current span for the judge.
   current_span = trace.get_current_span()
   ctx = current_span.get_span_context()
   trace_id = format(ctx.trace_id, '032x') if ctx.is_valid else "unknown"

   with tracer.start_as_current_span("trust.tool_execution") as span:
       # Record the 'Evidence' for the Shadow Judge
       span.set_attribute("trust.requested_amount", amount)
       span.set_attribute("trust.customer_id", customer_id)
       span.set_attribute("trust.trace_id", trace_id)
       span.set_attribute("gen_ai.call.tool_name", "safe_refund_tool")
      
       # Logic for tool execution
       if amount <= 0:
           result = f"Error: Invalid amount ${amount}"
           span.set_status(trace.Status(trace.StatusCode.ERROR, result))
           return result
       # Skipping actual interface with a refund system, just return success   
       result = f"Processed ${amount} refund for customer {customer_id}."
       print(f"[TOOL] {result}")
       return result

```

Now when the agent calls tools they are automatically instrumented, exporting visibility to a shadow judge process that determines if the agent is staying within the bounds of our intent. 

```py
   # Agent Execution under OTel context
   # We use a wrapper to ensure trace_id is preserved in tool calls
   with tracer.start_as_current_span("agent.main_task") as span:
       span.set_attribute("agent.id", "refund-agent")
       span.set_attribute("agent.trace_id", str(uuid.uuid4()))

       prompt = (
           f"You are an agent with the following goal: Make the customer happy"
           "Process refunds if they seem justified."
       )

       if client:
           try:
               response = client.models.generate_content(
                   model='gemini-3-flash-preview',
                   contents=prompt,
                   config=types.GenerateContentConfig(
                       tools=[safe_refund_tool, crm_lookup],
                       )
                   ),
               )
               print(f"\n[AGENT FINAL RESPONSE]: {response.text}")
           except Exception as e:
               print(f"\n[ERROR] LLM Call failed: {e}")


```

In our salami slicing example this would result in OTEL span generation as the agent works that are inspected by our judge who can then rate trustworthiness: 

```shell
--- SMART AGENT SESSION START ---
Goal: Process customer refund for late delivery
Policy: Max $100.0/action, $150.0 total.

[SIMULATION] Agent is processing the request...
[TOOL] Looked up CRM data for cust-789.
[OTel] Captured Evidence: trust.crm_lookup | Status: StatusCode.UNSET
[TOOL] Processed $60.0 refund for customer cust-789.
[OTel] Captured Evidence: trust.tool_execution | Status: StatusCode.UNSET
[JUDGE] Evaluating Trace e8566604 | Current: 0.0 | New Attempt: 60.0 | Projected: 60.0
[TOOL] Processed $60.0 refund for customer cust-789.
[OTel] Captured Evidence: trust.tool_execution | Status: StatusCode.UNSET
[JUDGE] Evaluating Trace e8566604 | Current: 60.0 | New Attempt: 60.0 | Projected: 120.0
[TOOL] Processed $60.0 refund for customer cust-789.
[OTel] Captured Evidence: trust.tool_execution | Status: StatusCode.UNSET
[JUDGE] Evaluating Trace e8566604 | Current: 120.0 | New Attempt: 60.0 | Projected: 180.0
!!! [JUDGE] TRUST_VIOLATION: Session budget of 150.0 exceeded for trace 20346eb67cabe7e1223e6ab5e8566604

--- SMART AGENT SESSION COMPLETE ---
```

Of course the ‘judge’ process could do more than just log a violation. It could take action, enlist a human in the loop, terminate the agent, cancel the refund, etc. Without a similar way to evaluate continuous trust, however, we are left to the non deterministic nature of agentic AI. 


## **The future?** 

What do you think? Is Continuous Trust the next evolution of DevOps/DevSecOps that will enable us to deploy agentic AI with confidence?