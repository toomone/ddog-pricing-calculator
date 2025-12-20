from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .models import PricingItem, Quote, QuoteCreate, SyncResponse
from .scraper import (
    load_pricing_data, load_metadata, sync_pricing, ensure_pricing_data,
    get_all_regions, get_regions_status, sync_all_regions, DEFAULT_REGION, REGIONS
)
from .quotes import create_quote, get_quote, update_quote, delete_quote, list_quotes
from .allotments_scraper import (
    load_allotments_data, load_allotments_metadata, sync_allotments, 
    ensure_allotments_data, get_allotments_for_product, save_manual_allotments,
    get_manual_allotments
)
from .redis_client import get_redis, is_redis_available


# Background scheduler for automatic syncing
scheduler = BackgroundScheduler()


def sync_all_pricing_job():
    """Background job to sync pricing data for all regions."""
    print(f"[{datetime.now().isoformat()}] Running scheduled pricing sync...")
    try:
        results = sync_all_regions()
        success_count = sum(1 for r in results if r.get('success', False))
        print(f"[{datetime.now().isoformat()}] Sync complete: {success_count}/{len(results)} regions updated")
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Sync failed: {e}")


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
    # Startup: ensure pricing data exists for default region
    success, message, count = ensure_pricing_data(DEFAULT_REGION)
    print(f"Startup: {message}")
    
    # Check if we should sync on startup (data older than 1 hour)
    if should_sync_on_startup():
        print("Data is older than 1 hour, syncing all regions...")
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
    print("Background scheduler started - pricing will sync every hour")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    print("Shutting down...")


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
    success, message, count = sync_pricing(region)
    return SyncResponse(success=success, message=message, products_count=count)


@app.post("/api/pricing/sync-all")
async def sync_all_pricing_data():
    """Sync pricing data for all regions."""
    results = sync_all_regions()
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
    """Create a new quote."""
    quote = create_quote(
        name=quote_data.name,
        region=quote_data.region,
        billing_type=quote_data.billing_type,
        items=quote_data.items
    )
    return quote


@app.get("/api/quotes/{quote_id}", response_model=Quote)
async def get_quote_by_id(quote_id: str):
    """Get a quote by ID."""
    quote = get_quote(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote


@app.put("/api/quotes/{quote_id}", response_model=Quote)
async def update_existing_quote(quote_id: str, quote_data: QuoteCreate):
    """Update an existing quote."""
    quote = update_quote(
        quote_id=quote_id,
        name=quote_data.name,
        billing_type=quote_data.billing_type,
        items=quote_data.items
    )
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote


@app.delete("/api/quotes/{quote_id}")
async def delete_existing_quote(quote_id: str):
    """Delete a quote."""
    success = delete_quote(quote_id)
    if not success:
        raise HTTPException(status_code=404, detail="Quote not found")
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
    success, message, count = sync_allotments()
    if not success:
        # Fall back to saving manual allotments
        save_manual_allotments()
        return {"success": True, "message": f"Using manual allotments data ({len(get_manual_allotments())} items)", "count": len(get_manual_allotments())}
    return {"success": success, "message": message, "count": count}


@app.post("/api/allotments/init")
async def init_allotments():
    """Initialize allotments with manual data."""
    save_manual_allotments()
    return {"success": True, "message": f"Initialized {len(get_manual_allotments())} manual allotments"}
