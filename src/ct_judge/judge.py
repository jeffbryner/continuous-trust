from typing import Dict, Any, List

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

# In the real GCP world, this logic would live in a Cloud Function 
# triggered by the telemetry stream.
