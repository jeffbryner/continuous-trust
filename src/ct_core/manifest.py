from typing import List, Optional
from pydantic import BaseModel, Field

class Constraints(BaseModel):
    max_per_action: float = Field(..., description="Maximum amount for a single tool action")
    max_session_total: float = Field(..., description="Maximum cumulative amount for the entire session")
    authorized_tools: List[str] = Field(default_factory=list, description="List of tools the agent is allowed to use")
    data_access: Optional[str] = Field(None, description="Scope of data access (e.g., 'billing_only')")

class Intent(BaseModel):
    task_goal: str = Field(..., description="The high-level goal of the agentic task")
    constraints: Constraints
    justification: Optional[str] = Field(None, description="Human-readable justification for the task")

class Metadata(BaseModel):
    agent_id: str
    trace_id: str
    timestamp: Optional[str] = None

class IntentManifest(BaseModel):
    metadata: Metadata
    intent: Intent

    @classmethod
    def create_example(cls, agent_id: str, trace_id: str) -> "IntentManifest":
        return cls(
            metadata=Metadata(agent_id=agent_id, trace_id=trace_id),
            intent=Intent(
                task_goal="Process customer refund for late delivery",
                constraints=Constraints(
                    max_per_action=100.0,
                    max_session_total=150.0,
                    authorized_tools=["safe_refund_tool", "crm_lookup"],
                    data_access="billing_only"
                ),
                justification="Customer requested refund for Order #123 due to shipping delay."
            )
        )
