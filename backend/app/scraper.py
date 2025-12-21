import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import re
import hashlib
import logging
from pathlib import Path
from datetime import datetime

from .redis_client import get_redis, is_redis_available, RedisKeys
from .config import get_storage_type

logger = logging.getLogger("pricehound.scraper")


def generate_product_id(product_name: str, billing_unit: str) -> str:
    """Generate a unique, deterministic ID for a product based on name and billing unit."""
    # Create a consistent string to hash
    id_string = f"{product_name.lower().strip()}|{billing_unit.lower().strip()}"
    # Use SHA-256 and take first 12 characters for a short but unique ID
    hash_obj = hashlib.sha256(id_string.encode('utf-8'))
    return hash_obj.hexdigest()[:12]


def extract_plan_from_product(product_name: str) -> str:
    """Extract the plan tier from product name.
    
    Returns:
        - 'Enterprise' if product name contains 'Enterprise'
        - 'Pro' if product name contains 'Pro' (but not 'Enterprise')
        - 'All' if no specific plan tier is found (available to all plans)
    """
    product_lower = product_name.lower()
    
    if 'enterprise' in product_lower:
        return 'Enterprise'
    elif 'pro' in product_lower:
        return 'Pro'
    else:
        return 'All'


DATA_DIR = Path(__file__).parent.parent / "data"
PRICING_DIR = DATA_DIR / "pricing"

# Datadog regions/sites matching the pricing page selector
# Site values match the dropdown on https://www.datadoghq.com/pricing/list/
REGIONS = {
    "us": {
        "name": "US (US1, US3, US5)",
        "site": "us"
    },
    "us1-fed": {
        "name": "US1-FED",
        "site": "us1-fed"
    },
    "eu1": {
        "name": "EU1",
        "site": "eu1"
    },
    "ap1": {
        "name": "AP1",
        "site": "ap1"
    },
    "ap2": {
        "name": "AP2",
        "site": "ap2"
    }
}

# Base URL for pricing page - site is selected via cookie/JS on the page
PRICING_BASE_URL = "https://www.datadoghq.com/pricing/list/"

DEFAULT_REGION = "us"


def get_pricing_file(region: str) -> Path:
    """Get the pricing file path for a region."""
    return PRICING_DIR / f"pricing-{region}.json"


def get_metadata_file(region: str) -> Path:
    """Get the metadata file path for a region."""
    return PRICING_DIR / f"metadata-{region}.json"


def parse_price(price_str: str) -> float:
    """Convert price string like '$15' or '$0.10' to float."""
    if not price_str or price_str == "-" or price_str == "":
        return 0.0
    # Remove $ and any commas, then convert to float
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def scrape_pricing_data(region: str = DEFAULT_REGION) -> list[dict]:
    """Scrape pricing data from Datadog pricing page."""
    region_info = REGIONS.get(region, REGIONS[DEFAULT_REGION])
    site = region_info["site"]
    
    # Build URL with site parameter
    pricing_url = f"{PRICING_BASE_URL}?site={site}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(pricing_url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'lxml')
    
    # Find pricing tables
    tables = soup.find_all('table')
    
    pricing_data = []
    
    for table in tables:
        # Try to parse with pandas
        try:
            df = pd.read_html(str(table))[0]
            
            # Process the dataframe based on column structure
            if len(df.columns) >= 4:
                # Normalize column names
                columns = df.columns.tolist()
                
                for _, row in df.iterrows():
                    try:
                        product_name = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                        billing_unit = str(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else ""
                        
                        # Skip header rows or empty rows
                        if not product_name or product_name.lower() in ['product', 'nan', '']:
                            continue
                        
                        # Clean up product name (remove billing unit if duplicated)
                        if billing_unit and billing_unit in product_name:
                            product_name = product_name.replace(billing_unit, '').strip()
                        
                        # Remove asterisks and clean whitespace
                        clean_product = product_name.replace('*', '').strip()
                        clean_billing_unit = billing_unit.replace('*', '').strip() if billing_unit else "per unit"
                        
                        item = {
                            "id": generate_product_id(clean_product, clean_billing_unit),
                            "region": region,
                            "product": clean_product,
                            "plan": extract_plan_from_product(clean_product),
                            "billing_unit": clean_billing_unit,
                            "billed_annually": str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else None,
                            "billed_month_to_month": str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else None,
                            "on_demand": str(row.iloc[4]).strip() if len(row) > 4 and pd.notna(row.iloc[4]) else None,
                        }
                        
                        # Only add if we have at least one price
                        if item["billed_annually"] or item["billed_month_to_month"] or item["on_demand"]:
                            pricing_data.append(item)
                    except Exception:
                        continue
                        
        except Exception:
            continue
    
    # Deduplicate based on product name
    seen = set()
    unique_data = []
    for item in pricing_data:
        key = (item["product"], item["billing_unit"])
        if key not in seen:
            seen.add(key)
            unique_data.append(item)
    
    return unique_data


def save_pricing_data(data: list[dict], region: str = DEFAULT_REGION) -> None:
    """Save pricing data to configured storage (Redis OR file)."""
    region_info = REGIONS.get(region, REGIONS[DEFAULT_REGION])
    site = region_info["site"]
    
    metadata = {
        "region": region,
        "region_name": region_info["name"],
        "site": site,
        "last_sync": datetime.utcnow().isoformat(),
        "products_count": len(data),
        "source_url": f"{PRICING_BASE_URL}?site={site}"
    }
    
    storage_type = get_storage_type()
    
    if is_redis_available():
        # Save to Redis
        redis = get_redis()
        redis.set_json(RedisKeys.pricing(region), data)
        redis.set_json(RedisKeys.pricing_metadata(region), metadata)
        logger.info(f"✅ Saved {len(data)} products to Redis for {region}")
    else:
        # Save to file
        PRICING_DIR.mkdir(parents=True, exist_ok=True)
        
        pricing_file = get_pricing_file(region)
        with open(pricing_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        metadata_file = get_metadata_file(region)
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Saved {len(data)} products to file for {region}")


def load_pricing_data(region: str = DEFAULT_REGION) -> list[dict]:
    """Load pricing data from configured storage (Redis OR file)."""
    if is_redis_available():
        # Load from Redis
        data = get_redis().get_json(RedisKeys.pricing(region))
        return data if data else []
    else:
        # Load from file
        pricing_file = get_pricing_file(region)
        if not pricing_file.exists():
            return []
        with open(pricing_file, 'r') as f:
            return json.load(f)


def load_metadata(region: str = DEFAULT_REGION) -> dict:
    """Load metadata from configured storage (Redis OR file)."""
    if is_redis_available():
        # Load from Redis
        metadata = get_redis().get_json(RedisKeys.pricing_metadata(region))
        return metadata if metadata else {}
    else:
        # Load from file
        metadata_file = get_metadata_file(region)
        if not metadata_file.exists():
            return {}
        with open(metadata_file, 'r') as f:
            return json.load(f)


def get_all_regions() -> dict:
    """Get all available regions with their info."""
    return REGIONS


def get_regions_status() -> list[dict]:
    """Get status of all regions (synced or not)."""
    status = []
    for region_id, region_info in REGIONS.items():
        metadata = load_metadata(region_id)
        status.append({
            "id": region_id,
            "name": region_info["name"],
            "site": region_info["site"],
            "synced": bool(metadata),
            "last_sync": metadata.get("last_sync"),
            "products_count": metadata.get("products_count", 0)
        })
    return status


def sync_pricing(region: str = DEFAULT_REGION) -> tuple[bool, str, int]:
    """Sync pricing data from Datadog website for a specific region."""
    if region not in REGIONS:
        return False, f"Unknown region: {region}", 0
    
    try:
        data = scrape_pricing_data(region)
        if data:
            save_pricing_data(data, region)
            region_name = REGIONS[region]["name"]
            storage = get_storage_type()
            return True, f"Successfully synced {len(data)} products for {region_name} (storage: {storage})", len(data)
        else:
            return False, "No pricing data found", 0
    except Exception as e:
        return False, f"Error syncing pricing: {str(e)}", 0


def sync_all_regions() -> list[dict]:
    """Sync pricing data for all regions."""
    results = []
    for region_id in REGIONS:
        success, message, count = sync_pricing(region_id)
        results.append({
            "region": region_id,
            "success": success,
            "message": message,
            "products_count": count
        })
    return results


def ensure_pricing_data(region: str = DEFAULT_REGION) -> tuple[bool, str, int]:
    """Ensure pricing data exists for a region, sync if not."""
    existing_data = load_pricing_data(region)
    if existing_data:
        metadata = load_metadata(region)
        last_sync = metadata.get("last_sync", "unknown")
        region_name = REGIONS.get(region, {}).get("name", region)
        storage = get_storage_type()
        return True, f"Loaded {len(existing_data)} products for {region_name} from {storage} (last sync: {last_sync})", len(existing_data)
    
    # No data exists, sync now
    return sync_pricing(region)
