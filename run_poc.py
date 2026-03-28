import uuid
from ct_core.manifest import IntentManifest
from ct_core.telemetry import setup_telemetry
from ct_agent.tools import safe_refund_tool, crm_lookup
from ct_judge.judge import ShadowJudge
from ct_agent.smart_agent import run_smart_agent_session
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

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

def run_integrated_poc():
    # 1. Setup Shadow Judge
    judge = ShadowJudge()
    judge_exporter = JudgePipeExporter(judge)
    
    # 2. Configure Telemetry ONCE with the judge exporter
    setup_telemetry("continuous-trust-poc", additional_exporters=[judge_exporter])
    
    # 3. Run the Smart Agent (uses google-genai)
    # The agent will now use the global tracer provider that includes our judge
    run_smart_agent_session()

if __name__ == "__main__":
    run_integrated_poc()
