"""
OpenTelemetry logging configuration for agentless log shipping to Datadog.

This module provides OTLP-based log export to Datadog without requiring
a local Datadog Agent. Logs are sent directly to Datadog's HTTP intake API.

Usage:
    Set environment variables:
        DD_API_KEY: Your Datadog API key (required for OTLP export)
        DD_SITE: Datadog site (default: datadoghq.com)
        DD_SERVICE: Service name (default: pricehound)
        DD_ENV: Environment (default: production)
        DD_VERSION: Version (default: 1.0.0)
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("pricehound.telemetry")

# Track if telemetry is initialized
_telemetry_initialized = False
_logger_provider = None


def setup_otlp_logging() -> bool:
    """Configure OpenTelemetry to ship logs to Datadog via OTLP.
    
    Returns:
        True if OTLP logging was successfully configured, False otherwise.
    """
    global _telemetry_initialized, _logger_provider
    
    if _telemetry_initialized:
        logger.debug("OTLP logging already initialized")
        return True
    
    dd_api_key = os.getenv("DD_API_KEY")
    dd_site = os.getenv("DD_SITE", "datadoghq.com")
    
    if not dd_api_key:
        logger.warning("⚠️ DD_API_KEY not set - OTLP logging disabled (logs will only go to console)")
        return False
    
    try:
        # Import OpenTelemetry components (only when needed)
        from opentelemetry import _logs
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk.resources import Resource
        
        # Service metadata from environment
        service_name = os.getenv("DD_SERVICE", "pricehound")
        service_version = os.getenv("DD_VERSION", "1.0.0")
        environment = os.getenv("DD_ENV", "production")
        hostname = os.getenv("RENDER_SERVICE_NAME", os.getenv("HOSTNAME", "local"))
        
        # Define resource attributes (service metadata)
        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
            "host.name": hostname,
        })
        
        # Datadog OTLP intake endpoint for logs
        # Format: https://otlp.{site}/v1/logs
        otlp_endpoint = f"https://otlp.{dd_site}/v1/logs"
        
        logger.info(f"🔗 OTLP endpoint: {otlp_endpoint}")
        
        # Create OTLP exporter with Datadog API key header
        exporter = OTLPLogExporter(
            endpoint=otlp_endpoint,
            headers={
                "DD-API-KEY": dd_api_key,
            }
        )
        
        # Set up logger provider with batch processing
        _logger_provider = LoggerProvider(resource=resource)
        _logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(exporter)
        )
        _logs.set_logger_provider(_logger_provider)
        
        # Create handler and attach to root logger
        otlp_handler = LoggingHandler(
            level=logging.INFO,
            logger_provider=_logger_provider
        )
        
        # Add handler to root logger so all loggers inherit it
        logging.getLogger().addHandler(otlp_handler)
        
        _telemetry_initialized = True
        logger.info(f"✅ OTLP logging enabled → {dd_site} (service: {service_name}, env: {environment})")
        return True
        
    except ImportError as e:
        logger.error(f"❌ OpenTelemetry packages not installed: {e}")
        logger.error("   Install with: pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to setup OTLP logging: {e}")
        return False


def shutdown_telemetry() -> None:
    """Gracefully shutdown telemetry exporters.
    
    This should be called on application shutdown to ensure
    all buffered logs are flushed to Datadog.
    """
    global _telemetry_initialized, _logger_provider
    
    if not _telemetry_initialized or _logger_provider is None:
        return
    
    try:
        logger.info("🔄 Flushing remaining logs to Datadog...")
        if hasattr(_logger_provider, 'shutdown'):
            _logger_provider.shutdown()
        logger.info("✅ Telemetry shutdown complete")
    except Exception as e:
        logger.error(f"⚠️ Error during telemetry shutdown: {e}")
    finally:
        _telemetry_initialized = False
        _logger_provider = None


def is_telemetry_enabled() -> bool:
    """Check if OTLP telemetry is currently enabled."""
    return _telemetry_initialized

