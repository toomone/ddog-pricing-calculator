from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from .models import PricingItem, Quote, QuoteCreate, QuoteUpdate, SyncResponse, VerifyPasswordRequest, VerifyPasswordResponse
from .scraper import (
    load_pricing_data, load_metadata, sync_pricing, ensure_pricing_data,
    get_all_regions, get_regions_status, sync_all_regions, DEFAULT_REGION, REGIONS
)
from .quotes import create_quote, get_quote, update_quote, delete_quote, list_quotes, verify_quote_password
from .allotments_scraper import (
    load_allotments_data, load_allotments_metadata, sync_allotments, 
    ensure_allotments_data, get_allotments_for_product, save_manual_allotments,
    get_manual_allotments
)
from .redis_client import get_redis, is_redis_available


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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
    
    # Log Redis status
    redis_status = "connected" if is_redis_available() else "disconnected"
    logger.info(f"📦 Redis status: {redis_status}")
    
    # Startup: ensure pricing data exists for default region
    success, message, count = ensure_pricing_data(DEFAULT_REGION)
    logger.info(f"📊 {message}")
    
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
            "plan": item.get("plan", "All"),
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


@app.post("/api/quotes", response_model=Quote)
async def create_new_quote(quote_data: QuoteCreate):
    """Create a new quote with optional password protection."""
    logger.info(f"📝 Creating new quote: name='{quote_data.name}', region={quote_data.region}, billing={quote_data.billing_type}, items={len(quote_data.items)}, protected={quote_data.edit_password is not None}")
    quote = create_quote(
        name=quote_data.name,
        region=quote_data.region,
        billing_type=quote_data.billing_type,
        items=quote_data.items,
        edit_password=quote_data.edit_password
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
        edit_password=quote_data.edit_password
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
