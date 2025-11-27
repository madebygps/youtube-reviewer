import logging
import os

import opentelemetry._logs as otel_logs
import opentelemetry.exporter.otlp.proto.grpc._log_exporter as log_exporter
import opentelemetry.exporter.otlp.proto.grpc.metric_exporter as metric_exporter
import opentelemetry.exporter.otlp.proto.grpc.trace_exporter as trace_exporter
import opentelemetry.metrics as otel_metrics
import opentelemetry.sdk._logs as otel_sdk_logs
import opentelemetry.sdk._logs.export as otel_logs_export
import opentelemetry.sdk.metrics as otel_sdk_metrics
import opentelemetry.sdk.metrics.export as otel_metrics_export
import opentelemetry.sdk.resources as otel_resources
import opentelemetry.sdk.trace as otel_sdk_trace
import opentelemetry.sdk.trace.export as otel_trace_export
import opentelemetry.trace as otel_trace


def configure_opentelemetry():
    """Configure OpenTelemetry for Aspire dashboard integration.
    
    This uses the standard OTEL_EXPORTER_OTLP_ENDPOINT environment variable
    that Aspire sets automatically for hosted applications.
    """
    # Check if OTEL is enabled
    if os.environ.get("ENABLE_OTEL", "").lower() != "true":
        return

    # Get the OTLP endpoint - Aspire sets OTEL_EXPORTER_OTLP_ENDPOINT
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        return

    # Create a resource with service name
    resource = otel_resources.Resource.create({
        otel_resources.SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "app"),
    })

    # Configure tracing
    tracer_provider = otel_sdk_trace.TracerProvider(resource=resource)
    otlp_span_exporter = trace_exporter.OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    span_processor = otel_trace_export.BatchSpanProcessor(otlp_span_exporter)
    tracer_provider.add_span_processor(span_processor)
    otel_trace.set_tracer_provider(tracer_provider)

    # Configure metrics
    otlp_metric_exporter = metric_exporter.OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    metric_reader = otel_metrics_export.PeriodicExportingMetricReader(
        otlp_metric_exporter, export_interval_millis=5000
    )
    otel_metrics.set_meter_provider(otel_sdk_metrics.MeterProvider(
        resource=resource, metric_readers=[metric_reader]
    ))

    # Configure logging - set up the logger provider
    logger_provider = otel_sdk_logs.LoggerProvider(resource=resource)
    otlp_log_exporter = log_exporter.OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    log_processor = otel_logs_export.BatchLogRecordProcessor(otlp_log_exporter)
    logger_provider.add_log_record_processor(log_processor)
    otel_logs.set_logger_provider(logger_provider)

    # Add OTEL handler to the ROOT logger directly
    # This ensures all loggers (including those already created) will emit to OTEL
    # logging.basicConfig() is ignored if handlers already exist (uvicorn sets them up)
    otel_handler = otel_sdk_logs.LoggingHandler(
        level=logging.INFO,
        logger_provider=logger_provider,
    )
    
    # Get the root logger and add our handler
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(otel_handler)