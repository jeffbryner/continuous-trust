from opentelemetry import trace
from typing import Dict, Any, Optional

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
            
        result = f"Processed ${amount} refund for customer {customer_id}."
        print(f"[TOOL] {result}")
        return result

def crm_lookup(customer_id: str):
    """
    Retrieves customer status and tier information.
    
    Args:
        customer_id: The unique identifier for the customer.
    """
    with tracer.start_as_current_span("trust.crm_lookup") as span:
        span.set_attribute("trust.customer_id", customer_id)
        span.set_attribute("gen_ai.call.tool_name", "crm_lookup")
        
        print(f"[TOOL] Looked up CRM data for {customer_id}.")
        return {"id": customer_id, "status": "active", "tier": "gold"}
