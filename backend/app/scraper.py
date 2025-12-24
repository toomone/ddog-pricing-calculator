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
PRICING_MAIN_URL = "https://www.datadoghq.com/pricing/"

DEFAULT_REGION = "us"

# Default product categories based on Datadog pricing page structure
# These are used as fallback if scraping the sidebar fails
DEFAULT_CATEGORIES = [
    {
        "name": "Infrastructure",
        "order": 1,
        "keywords": ["infrastructure", "container", "custom metrics", "ingested custom metrics", 
                     "serverless", "network", "cloud cost", "fargate", "azure app", "google cloud run"]
    },
    {
        "name": "Applications",
        "order": 2,
        "keywords": ["apm", "database", "data streams", "profiler", "continuous profiler", 
                     "dynamic instrumentation", "universal service monitoring", "llm observability",
                     "data jobs"]
    },
    {
        "name": "Logs",
        "order": 3,
        "keywords": ["logs", "log management", "sensitive data scanner", "audit trail", 
                     "observability pipelines", "flex logs"]
    },
    {
        "name": "Security",
        "order": 4,
        "keywords": ["security", "cspm", "ciem", "cloud siem", "siem", "workload", 
                     "application security", "asm", "code security", "sca", "software composition"]
    },
    {
        "name": "Digital Experience",
        "order": 5,
        "keywords": ["rum", "real user", "session replay", "synthetic", "mobile rum", 
                     "browser rum", "error tracking", "product analytics"]
    },
    {
        "name": "Software Delivery",
        "order": 6,
        "keywords": ["ci visibility", "test visibility", "pipeline visibility", "continuous testing",
                     "ide", "test optimization"]
    },
    {
        "name": "Service Management",
        "order": 7,
        "keywords": ["incident", "on-call", "case management", "workflow automation", 
                     "slo", "service level", "event management"]
    },
    {
        "name": "AI",
        "order": 8,
        "keywords": ["ai", "llm", "bits ai"]
    }
]


def get_pricing_file(region: str) -> Path:
    """Get the pricing file path for a region."""
    return PRICING_DIR / f"pricing-{region}.json"


def get_metadata_file(region: str) -> Path:
    """Get the metadata file path for a region."""
    return PRICING_DIR / f"metadata-{region}.json"


def get_categories_file() -> Path:
    """Get the categories file path."""
    return PRICING_DIR / "categories.json"


def match_product_to_category(product_name: str, categories: list[dict] = None) -> str:
    """Find which category a product belongs to.
    
    First tries exact match using 'products' list (from scraped data),
    then falls back to keyword matching using 'keywords' list.
    
    Args:
        product_name: The product name to categorize
        categories: List of category dicts with 'name' and 'products' or 'keywords' fields.
                   Uses DEFAULT_CATEGORIES if not provided.
    
    Returns:
        Category name or 'Specific' if no match found.
    """
    if categories is None:
        categories = DEFAULT_CATEGORIES
    
    product_lower = product_name.lower()
    product_words = set(product_lower.split())
    
    # First: Try exact match from scraped product lists
    for category in categories:
        products = category.get("products", [])
        for prod in products:
            if prod.lower() in product_lower or product_lower in prod.lower():
                return category["name"]
    
    # Second: Try keyword matching (fallback for DEFAULT_CATEGORIES)
    # Use word-boundary matching for short keywords to avoid false positives
    for category in categories:
        keywords = category.get("keywords", [])
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # For short keywords (<=3 chars), require exact word match
            if len(keyword_lower) <= 3:
                if keyword_lower in product_words:
                    return category["name"]
            # For longer keywords, allow substring match
            elif keyword_lower in product_lower:
                return category["name"]
    
    return "Specific"


def scrape_product_categories() -> list[dict]:
    """Scrape product categories from the main Datadog pricing page sidebar.
    
    Falls back to DEFAULT_CATEGORIES if scraping fails.
    
    Returns:
        List of category dicts with 'name', 'order', and 'products' fields.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(PRICING_MAIN_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        categories = []
        
        # Look for pricing navigation sections
        # The Datadog pricing page typically has sections with headers and product lists
        # Try to find category headers (usually h2, h3, or h4 elements)
        
        # Try various selectors that might contain category information
        nav_elements = soup.find_all(['nav', 'aside', 'div'], class_=re.compile(r'nav|sidebar|menu|pricing', re.I))
        
        for nav in nav_elements:
            # Look for heading + list patterns
            headings = nav.find_all(['h2', 'h3', 'h4'])
            for heading in headings:
                category_name = heading.get_text(strip=True)
                
                # Skip empty or generic headings
                if not category_name or len(category_name) < 2:
                    continue
                
                # Find the next sibling list or div containing products
                product_list = heading.find_next(['ul', 'div'])
                if product_list:
                    products = []
                    for link in product_list.find_all('a', limit=20):
                        product_name = link.get_text(strip=True)
                        if product_name and len(product_name) > 2:
                            products.append(product_name)
                    
                    if products:
                        categories.append({
                            "name": category_name,
                            "products": products
                        })
        
        if categories:
            # Add order based on position
            for i, cat in enumerate(categories):
                cat["order"] = i + 1
            logger.info(f"✅ Scraped {len(categories)} categories from pricing page")
            return categories
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to scrape categories from pricing page: {e}")
    
    # Fallback to default categories
    logger.info("📋 Using default product categories")
    return DEFAULT_CATEGORIES


def get_categories() -> list[dict]:
    """Get product categories from storage or scrape if not available.
    
    Returns:
        List of category dicts.
    """
    # Try Redis first
    if is_redis_available():
        redis = get_redis()
        categories = redis.get_json("categories")
        if categories:
            return categories
    
    # Try file
    categories_file = get_categories_file()
    if categories_file.exists():
        with open(categories_file, 'r') as f:
            return json.load(f)
    
    # Scrape and save
    categories = scrape_product_categories()
    save_categories(categories)
    return categories


def save_categories(categories: list[dict]) -> None:
    """Save product categories to storage."""
    if is_redis_available():
        get_redis().set_json("categories", categories)
        logger.info(f"✅ Saved {len(categories)} categories to Redis")
    else:
        PRICING_DIR.mkdir(parents=True, exist_ok=True)
        with open(get_categories_file(), 'w') as f:
            json.dump(categories, f, indent=2)
        logger.info(f"✅ Saved {len(categories)} categories to file")


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
    """Scrape pricing data from Datadog pricing page with category information."""
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
    
    # Get categories for matching (use cached or default)
    categories = get_categories()
    
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
                        
                        # Match product to category
                        category = match_product_to_category(clean_product, categories)
                        
                        item = {
                            "id": generate_product_id(clean_product, clean_billing_unit),
                            "region": region,
                            "product": clean_product,
                            "category": category,
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
    
    # Log category distribution
    category_counts = {}
    for item in unique_data:
        cat = item.get("category", "Other")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    logger.info(f"📊 Category distribution: {category_counts}")
    
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


def sync_categories() -> tuple[bool, str, int]:
    """Sync product categories from Datadog pricing page.
    
    Returns:
        Tuple of (success, message, count)
    """
    try:
        categories = scrape_product_categories()
        save_categories(categories)
        return True, f"Successfully synced {len(categories)} categories", len(categories)
    except Exception as e:
        return False, f"Error syncing categories: {str(e)}", 0


def get_category_order() -> dict[str, int]:
    """Get a mapping of category names to their display order.
    
    Returns:
        Dict mapping category name to order (1-based, 99 for Other)
    """
    categories = get_categories()
    order_map = {}
    for cat in categories:
        order_map[cat["name"]] = cat.get("order", 50)
    order_map["Specific"] = 99
    return order_map
