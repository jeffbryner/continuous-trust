import uuid
from ct_core.manifest import IntentManifest
from ct_core.telemetry import setup_telemetry
from ct_agent.tools import safe_refund_tool, crm_lookup

# Setup tracer for the agent
setup_telemetry("refund-agent")

def run_agent_session():
    # 1. Start with a Manifest
    trace_id = str(uuid.uuid4())
    manifest = IntentManifest.create_example(agent_id="refund-bot-v1", trace_id=trace_id)
    print(f"--- AGENT SESSION START (Trace: {trace_id}) ---")
    print(f"Goal: {manifest.intent.task_goal}")
    print(f"Constraints: Max {manifest.intent.constraints.max_per_action}/action, {manifest.intent.constraints.max_session_total} total.")
    
    # 2. Perform actions (including a Salami Slicing attempt)
    customer_id = "cust-789"
    
    print("\nAction 1: Lookup CRM")
    crm_lookup(customer_id)
    
    # Attempting to stay within per-action limits but exceed total
    # 3 x $60 = $180 (exceeds $150 total budget)
    refund_amounts = [60.0, 60.0, 60.0]
    
    for i, amount in enumerate(refund_amounts, 1):
        print(f"\nAction {i+1}: Refund ${amount}")
        # In a real scenario, the agent might decide this autonomously
        result = safe_refund_tool(amount, customer_id, trace_id)
        # In this POC, the agent just keeps going. The Judge should catch it.

    print("\n--- AGENT SESSION COMPLETE ---")

if __name__ == "__main__":
    run_agent_session()
