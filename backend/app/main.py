from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from .models import PricingItem, Quote, QuoteCreate, QuoteUpdate, SyncResponse, VerifyPasswordRequest, VerifyPasswordResponse, Template
from .scraper import (
    load_pricing_data, load_metadata, sync_pricing, ensure_pricing_data,
    get_all_regions, get_regions_status, sync_all_regions, DEFAULT_REGION, REGIONS,
    get_categories, sync_categories, get_category_order, load_pricing_changes
)
from .quotes import create_quote, get_quote, update_quote, delete_quote, list_quotes, verify_quote_password
from .allotments_scraper import (
    load_allotments_data, load_allotments_metadata, sync_allotments, 
    ensure_allotments_data, get_allotments_for_product, save_manual_allotments,
    get_manual_allotments, load_allotment_changes
)
from .redis_client import get_redis, is_redis_available
from .templates import get_all_templates, get_template, ensure_templates, sync_templates_to_redis
from .telemetry import setup_otlp_logging, setup_ddtrace, shutdown_telemetry


# Custom formatter that includes trace correlation when available
class TraceFormatter(logging.Formatter):
    """Log formatter that includes dd.trace_id and dd.span_id when available."""
    
    def format(self, record):
        # Get trace context from record (injected by ddtrace) or use defaults
        trace_id = getattr(record, 'dd.trace_id', '0')
        span_id = getattr(record, 'dd.span_id', '0')
        
        # Add trace context to the message
        record.trace_context = f"[dd.trace_id={trace_id} dd.span_id={span_id}]"
        return super().format(record)

# Configure logging with trace correlation support
handler = logging.StreamHandler()
handler.setFormatter(TraceFormatter(
    fmt='%(asctime)s | %(levelname)s | %(trace_context)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger("pricehound")

# Background scheduler for automatic syncing
scheduler = BackgroundScheduler()


def sync_all_pricing_job():
    """Background job to sync pricing data for all regions."""
    logger.info("🔄 Running scheduled pricing sync...")
    try:
        results = sync_all_regions()
        success_count = sum(1 for r in results if r.get('success', False))
        logger.info(f"✅ Sync complete: {success_count}/{len(results)} regions updated")
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")


def should_sync_on_startup() -> bool:
    """Check if we should sync on startup (if data is older than 1 hour)."""
    metadata = load_metadata(DEFAULT_REGION)
    if not metadata or not metadata.get('last_sync'):
        return True
    
    try:
        last_sync = datetime.fromisoformat(metadata['last_sync'].replace('Z', '+00:00'))
        # Make last_sync offset-naive for comparison
        if last_sync.tzinfo is not None:
            last_sync = last_sync.replace(tzinfo=None)
        age = datetime.utcnow() - last_sync
        return age > timedelta(hours=1)
    except Exception:
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 PriceHound API starting up...")
    
    # Setup ddtrace first (before other initialization to capture all spans)
    setup_ddtrace()
    
    # Setup OTLP logging (before other initialization logs)
    setup_otlp_logging()
    
    # Log Redis status
    redis_status = "connected" if is_redis_available() else "disconnected"
    logger.info(f"📦 Redis status: {redis_status}")
    
    # Startup: ensure categories are synced first (needed for product categorization)
    logger.info("📋 Ensuring product categories are loaded...")
    cat_success, cat_message, cat_count = sync_categories()
    logger.info(f"📋 {cat_message}")
    
    # Startup: ensure pricing data exists for default region
    success, message, count = ensure_pricing_data(DEFAULT_REGION)
    logger.info(f"📊 {message}")
    
    # Startup: ensure templates are loaded from files to Redis
    success, message, count = ensure_templates()
    logger.info(f"📋 {message}")
    
    # Check if we should sync on startup (data older than 1 hour)
    if should_sync_on_startup():
        logger.info("⏰ Data is older than 1 hour, syncing all regions...")
        sync_all_pricing_job()
    
    # Start the background scheduler - sync every hour
    scheduler.add_job(
        sync_all_pricing_job,
        trigger=IntervalTrigger(hours=1),
        id='sync_pricing_hourly',
        name='Sync pricing data every hour',
        replace_existing=True
    )
    scheduler.start()
    logger.info("⏱️ Background scheduler started - pricing will sync every hour")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("👋 PriceHound API shutting down...")
    shutdown_telemetry()  # Flush remaining logs to Datadog


app = FastAPI(
    title="PriceHound API",
    description="PriceHound forecasts your Datadog usage and builds an accurate quote before you commit.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Datadog Pricing Calculator API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    """Health check endpoint with storage status."""
    redis_status = "connected" if is_redis_available() else "disconnected"
    return {
        "status": "healthy",
        "storage": {
            "redis": redis_status,
            "file": "available"
        },
        "version": "1.0.0"
    }


@app.get("/api/regions")
async def get_regions():
    """Get all available Datadog regions."""
    return get_all_regions()


@app.get("/api/regions/status")
async def get_regions_sync_status():
    """Get sync status for all regions."""
    return get_regions_status()


# ================================
# Categories Endpoints
# ================================

@app.get("/api/categories")
async def list_categories():
    """Get all product categories with their order.
    
    Categories are used to group products in the UI (e.g., Infrastructure, Logs, Security).
    """
    categories = get_categories()
    return categories


@app.get("/api/categories/order")
async def get_categories_order():
    """Get a mapping of category names to their display order.
    
    Useful for sorting products by category in the frontend.
    """
    return get_category_order()


@app.post("/api/categories/sync")
async def sync_categories_endpoint():
    """Re-sync product categories from Datadog pricing page."""
    logger.info("🔄 Manual category sync requested")
    success, message, count = sync_categories()
    if success:
        logger.info(f"✅ Category sync successful: {count} categories")
    else:
        logger.warning(f"⚠️ Category sync failed: {message}")
    return {"success": success, "message": message, "count": count}


# ================================
# Pricing Endpoints
# ================================

@app.get("/api/pricing", response_model=list[PricingItem])
async def get_pricing(region: str = Query(default=DEFAULT_REGION, description="Datadog region")):
    """Get all pricing data for a specific region."""
    data = load_pricing_data(region)
    return [PricingItem(**item) for item in data]


@app.get("/api/pricing/metadata")
async def get_pricing_metadata(region: str = Query(default=DEFAULT_REGION, description="Datadog region")):
    """Get metadata about the pricing data (last sync, count, etc.) for a specific region."""
    metadata = load_metadata(region)
    return metadata


@app.post("/api/pricing/sync", response_model=SyncResponse)
async def sync_pricing_data(region: str = Query(default=DEFAULT_REGION, description="Datadog region")):
    """Sync pricing data from Datadog website for a specific region."""
    logger.info(f"🔄 Manual sync requested for region: {region}")
    success, message, count = sync_pricing(region)
    if success:
        logger.info(f"✅ Sync successful: {count} products for {region}")
    else:
        logger.warning(f"⚠️ Sync failed for {region}: {message}")
    return SyncResponse(success=success, message=message, products_count=count)


@app.post("/api/pricing/sync-all")
async def sync_all_pricing_data():
    """Sync pricing data for all regions."""
    logger.info("🔄 Manual sync-all requested")
    results = sync_all_regions()
    success_count = sum(1 for r in results if r.get('success', False))
    logger.info(f"✅ Sync-all complete: {success_count}/{len(results)} regions")
    return {"results": results}


@app.get("/api/products")
async def get_products(region: str = Query(default=DEFAULT_REGION, description="Datadog region")):
    """Get list of product names for search for a specific region."""
    data = load_pricing_data(region)
    products = [
        {
            "id": item.get("id", ""),
            "product": item["product"],
            "category": item.get("category", "Other"),
            "plan": item.get("plan", "All"),
            "product_type": item.get("product_type", "addon"),
            "billing_unit": item["billing_unit"],
            "billed_annually": item.get("billed_annually"),
            "billed_month_to_month": item.get("billed_month_to_month"),
            "on_demand": item.get("on_demand"),
        }
        for item in data
    ]
    return products


@app.get("/api/quotes", response_model=list[Quote])
async def get_all_quotes():
    """Get all quotes."""
    return list_quotes()


@app.get("/api/quotes/stats")
async def get_quote_storage_stats():
    """Get quote storage statistics including memory usage and quote count."""
    from .quotes import get_quotes_stats
    return get_quotes_stats()


@app.post("/api/quotes/cleanup")
async def cleanup_quotes_endpoint(max_quotes: int = Query(default=5000, description="Maximum quotes to keep")):
    """Manually trigger quote cleanup to free up storage space."""
    from .quotes import cleanup_old_quotes
    logger.info(f"🧹 Manual quote cleanup requested (max: {max_quotes})")
    deleted = cleanup_old_quotes(max_quotes)
    logger.info(f"✅ Cleanup complete: {deleted} quotes removed")
    return {"deleted": deleted, "message": f"Cleaned up {deleted} quotes"}


@app.post("/api/quotes", response_model=Quote)
async def create_new_quote(quote_data: QuoteCreate):
    """Create a new quote with optional password protection."""
    logger.info(f"📝 Creating new quote: name='{quote_data.name}', region={quote_data.region}, billing={quote_data.billing_type}, items={len(quote_data.items)}, protected={quote_data.edit_password is not None}")
    quote = create_quote(
        name=quote_data.name,
        region=quote_data.region,
        billing_type=quote_data.billing_type,
        items=quote_data.items,
        edit_password=quote_data.edit_password,
        description=quote_data.description
    )
    logger.info(f"✅ Quote created: id={quote.id}, total=${quote.total:.2f}, protected={quote.is_protected}")
    return quote


@app.get("/api/quotes/{quote_id}", response_model=Quote)
async def get_quote_by_id(quote_id: str):
    """Get a quote by ID."""
    logger.info(f"🔍 Fetching quote: {quote_id}")
    quote = get_quote(quote_id)
    if not quote:
        logger.warning(f"⚠️ Quote not found: {quote_id}")
        raise HTTPException(status_code=404, detail="Quote not found")
    logger.info(f"✅ Quote found: {quote_id}, items={len(quote.items)}")
    return quote


@app.put("/api/quotes/{quote_id}", response_model=Quote)
async def update_existing_quote(quote_id: str, quote_data: QuoteUpdate):
    """Update an existing quote. Requires password if quote is protected."""
    logger.info(f"📝 Updating quote: {quote_id}")
    quote, error = update_quote(
        quote_id=quote_id,
        name=quote_data.name,
        region=quote_data.region,
        billing_type=quote_data.billing_type,
        items=quote_data.items,
        edit_password=quote_data.edit_password,
        description=quote_data.description
    )
    if not quote:
        if "Password required" in error or "Invalid password" in error:
            logger.warning(f"⚠️ Quote update unauthorized: {quote_id} - {error}")
            raise HTTPException(status_code=403, detail=error)
        logger.warning(f"⚠️ Quote not found: {quote_id}")
        raise HTTPException(status_code=404, detail="Quote not found")
    logger.info(f"✅ Quote updated: {quote_id}")
    return quote


@app.post("/api/quotes/{quote_id}/verify-password", response_model=VerifyPasswordResponse)
async def verify_password_endpoint(quote_id: str, request: VerifyPasswordRequest):
    """Verify password for a quote."""
    is_valid, message = verify_quote_password(quote_id, request.password)
    if not is_valid and message == "Quote not found":
        raise HTTPException(status_code=404, detail="Quote not found")
    return VerifyPasswordResponse(valid=is_valid, message=message)


@app.delete("/api/quotes/{quote_id}")
async def delete_existing_quote(quote_id: str):
    """Delete a quote."""
    logger.info(f"🗑️ Deleting quote: {quote_id}")
    success = delete_quote(quote_id)
    if not success:
        logger.warning(f"⚠️ Quote not found for deletion: {quote_id}")
        raise HTTPException(status_code=404, detail="Quote not found")
    logger.info(f"✅ Quote deleted: {quote_id}")
    return {"message": "Quote deleted successfully"}


# Allotments endpoints
@app.get("/api/allotments")
async def get_allotments():
    """Get all allotments data."""
    data = load_allotments_data()
    if not data:
        # Use manual allotments as fallback
        data = get_manual_allotments()
    return data


@app.get("/api/allotments/metadata")
async def get_allotments_metadata():
    """Get allotments metadata."""
    return load_allotments_metadata()


@app.get("/api/allotments/product/{product_name}")
async def get_product_allotments(product_name: str):
    """Get allotments for a specific parent product."""
    allotments = get_allotments_for_product(product_name)
    if not allotments:
        # Try manual allotments
        manual = get_manual_allotments()
        allotments = [a for a in manual if a["parent_product"].lower() == product_name.lower()]
    return allotments


@app.post("/api/allotments/sync")
async def sync_allotments_data():
    """Sync allotments data."""
    logger.info("🔄 Syncing allotments data...")
    success, message, count = sync_allotments()
    if not success:
        logger.warning(f"⚠️ Allotments sync failed, using manual data: {message}")
        save_manual_allotments()
        manual_count = len(get_manual_allotments())
        logger.info(f"✅ Manual allotments saved: {manual_count} items")
        return {"success": True, "message": f"Using manual allotments data ({manual_count} items)", "count": manual_count}
    logger.info(f"✅ Allotments synced: {count} items")
    return {"success": success, "message": message, "count": count}


@app.post("/api/allotments/init")
async def init_allotments():
    """Initialize allotments with manual data."""
    logger.info("📦 Initializing manual allotments...")
    save_manual_allotments()
    count = len(get_manual_allotments())
    logger.info(f"✅ Manual allotments initialized: {count} items")
    return {"success": True, "message": f"Initialized {len(get_manual_allotments())} manual allotments"}


# ================================
# Change History Endpoints
# ================================

@app.get("/api/changes")
async def get_all_changes(
    limit: int = Query(default=100, description="Maximum number of changes to return"),
    change_type: Optional[str] = Query(default=None, description="Filter by change type (price_change, product_added, product_removed, allotment_change, allotment_added, allotment_removed)"),
    region: Optional[str] = Query(default=None, description="Filter by region (for pricing changes)")
):
    """Get combined change history for both pricing and allotments.
    
    Returns changes sorted by timestamp (newest first).
    """
    # Load both change histories
    pricing_changes = load_pricing_changes()
    allotment_changes = load_allotment_changes()
    
    # Combine and sort by timestamp (newest first)
    all_changes = pricing_changes + allotment_changes
    all_changes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Apply filters
    if change_type:
        all_changes = [c for c in all_changes if c.get("type") == change_type]
    
    if region:
        all_changes = [c for c in all_changes if c.get("region") == region or "region" not in c]
    
    # Apply limit
    return all_changes[:limit]


@app.get("/api/changes/pricing")
async def get_pricing_changes(
    limit: int = Query(default=100, description="Maximum number of changes to return"),
    region: Optional[str] = Query(default=None, description="Filter by region")
):
    """Get pricing change history.
    
    Returns changes sorted by timestamp (newest first).
    """
    changes = load_pricing_changes()
    
    # Sort by timestamp (newest first)
    changes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Apply region filter
    if region:
        changes = [c for c in changes if c.get("region") == region]
    
    return changes[:limit]


@app.get("/api/changes/allotments")
async def get_allotments_changes(
    limit: int = Query(default=100, description="Maximum number of changes to return")
):
    """Get allotment change history.
    
    Returns changes sorted by timestamp (newest first).
    """
    changes = load_allotment_changes()
    
    # Sort by timestamp (newest first)
    changes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return changes[:limit]


@app.get("/api/changes/summary")
async def get_changes_summary():
    """Get a summary of recent changes.
    
    Returns counts by type and the most recent changes.
    """
    pricing_changes = load_pricing_changes()
    allotment_changes = load_allotment_changes()
    
    # Count by type
    type_counts = {}
    for change in pricing_changes + allotment_changes:
        change_type = change.get("type", "unknown")
        type_counts[change_type] = type_counts.get(change_type, 0) + 1
    
    # Get most recent changes (last 10)
    all_changes = pricing_changes + allotment_changes
    all_changes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    recent_changes = all_changes[:10]
    
    return {
        "total_pricing_changes": len(pricing_changes),
        "total_allotment_changes": len(allotment_changes),
        "changes_by_type": type_counts,
        "recent_changes": recent_changes
    }


# Template endpoints
@app.get("/api/templates", response_model=list[Template])
async def list_templates():
    """Get all available quote templates."""
    templates = get_all_templates()
    logger.info(f"📋 Returning {len(templates)} templates")
    return templates


@app.get("/api/templates/{template_id}", response_model=Template)
async def get_template_by_id(template_id: str):
    """Get a specific template by ID."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.post("/api/templates/seed")
async def seed_templates():
    """Sync templates from JSON files to Redis."""
    logger.info("🔄 Syncing templates from files to Redis...")
    count = sync_templates_to_redis()
    logger.info(f"✅ Synced {count} templates")
    return {"success": True, "count": count, "message": f"Synced {count} templates from files"}
