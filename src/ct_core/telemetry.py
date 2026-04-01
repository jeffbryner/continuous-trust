import os
import json
from typing import List, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SimpleSpanProcessor,
    SpanExportResult,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from google.cloud import logging as gcp_logging


class GCPLoggingExporter(SpanExporter):
    """
    Exports OTel spans as structured logs to Google Cloud Logging.
    This is required to trigger Cloud Logging Sinks for the Shadow Judge.
    """

    def __init__(self, project_id: str):
        self.client = gcp_logging.Client(project=project_id)
        self.logger = self.client.logger("agent-trust-telemetry")

    def export(self, spans):
        for span in spans:
            # Standard OTel attributes to structured log
            log_data = {
                "name": span.name,
                "context": {
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                    "span_id": format(span.get_span_context().span_id, "016x"),
                },
                "attributes": dict(span.attributes),
                "resource": dict(span.resource.attributes),
            }
            # The Log Sink will filter based on this jsonPayload
            self.logger.log_struct(log_data, severity="INFO")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


class SimpleSummaryExporter(SpanExporter):
    def export(self, spans):
        for span in spans:
            if span.name.startswith("trust."):
                print(
                    f"[OTel] Captured Evidence: {span.name} | Status: {span.status.status_code}"
                )
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def setup_telemetry(
    service_name: str, additional_exporters: Optional[List[SpanExporter]] = None
):
    # Check if provider is already set
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return trace.get_tracer(service_name)

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # Minimal console output for spans
    provider.add_span_processor(SimpleSpanProcessor(SimpleSummaryExporter()))

    # Add any additional exporters (like our Judge Pipe)
    if additional_exporters:
        for exporter in additional_exporters:
            provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Optional OTLP Exporter (e.g., to GCP)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
