"""
Scraper for Datadog allotments data from https://www.datadoghq.com/pricing/allotments/
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from pathlib import Path
from datetime import datetime

from .scraper import load_pricing_data, DEFAULT_REGION
from .redis_client import get_redis, is_redis_available, RedisKeys

logger = logging.getLogger("pricehound.allotments")


DATA_DIR = Path(__file__).parent.parent / "data"
ALLOTMENTS_FILE = DATA_DIR / "allotments.json"
ALLOTMENTS_METADATA_FILE = DATA_DIR / "allotments_metadata.json"

ALLOTMENTS_URL = "https://www.datadoghq.com/pricing/allotments/"


def find_product_id_by_name(product_name: str, pricing_data: list[dict] = None) -> str | None:
    """
    Find a product ID by matching the product name.
    Uses fuzzy matching to handle variations in naming.
    """
    if pricing_data is None:
        pricing_data = load_pricing_data(DEFAULT_REGION)
    
    if not pricing_data:
        return None
    
    product_name_lower = product_name.lower().strip()
    
    # Try exact match first
    for product in pricing_data:
        if product.get("product", "").lower().strip() == product_name_lower:
            return product.get("id")
    
    # Try partial match (product name contains allotted product name)
    for product in pricing_data:
        prod_name = product.get("product", "").lower().strip()
        if product_name_lower in prod_name or prod_name in product_name_lower:
            return product.get("id")
    
    # Try matching key terms
    # e.g., "Custom Metrics" should match "Custom Metrics" product
    key_terms = product_name_lower.split()
    for product in pricing_data:
        prod_name = product.get("product", "").lower().strip()
        if all(term in prod_name for term in key_terms if len(term) > 2):
            return product.get("id")
    
    return None


def enrich_allotments_with_product_ids(allotments: list[dict]) -> list[dict]:
    """
    Enrich allotments data with product IDs by matching product names.
    """
    pricing_data = load_pricing_data(DEFAULT_REGION)
    
    enriched = []
    for allotment in allotments:
        enriched_allotment = allotment.copy()
        
        # Try to find product ID for the allotted product
        allotted_product = allotment.get("allotted_product", "")
        product_id = find_product_id_by_name(allotted_product, pricing_data)
        if product_id:
            enriched_allotment["allotted_product_id"] = product_id
        
        # Try to find product ID for the parent product
        parent_product = allotment.get("parent_product", "")
        parent_id = find_product_id_by_name(parent_product, pricing_data)
        if parent_id:
            enriched_allotment["parent_product_id"] = parent_id
        
        enriched.append(enriched_allotment)
    
    return enriched


def parse_allotment_value(value_str: str) -> dict:
    """
    Parse allotment value string like "100 custom metrics per host per month"
    Returns dict with quantity, unit, per_unit, frequency
    """
    if not value_str or value_str.strip() == "":
        return None
    
    value_str = value_str.strip().lower()
    
    # Extract the numeric value
    match = re.match(r'^([\d,\.]+)\s*(.+)$', value_str)
    if not match:
        return {"raw": value_str}
    
    quantity = float(match.group(1).replace(',', ''))
    remainder = match.group(2).strip()
    
    # Parse the unit and per-unit information
    # Common patterns: "custom metrics per host per month"
    result = {
        "quantity": quantity,
        "raw": value_str
    }
    
    # Extract what's being allotted
    per_match = re.search(r'^(.+?)\s+per\s+(.+?)\s+per\s+(month|hour)', remainder)
    if per_match:
        result["allotted_unit"] = per_match.group(1).strip()
        result["per_parent_unit"] = per_match.group(2).strip()
        result["frequency"] = per_match.group(3).strip()
    else:
        # Try simpler pattern
        simple_match = re.search(r'^(.+?)\s+per\s+(month|hour)', remainder)
        if simple_match:
            result["allotted_unit"] = simple_match.group(1).strip()
            result["frequency"] = simple_match.group(2).strip()
    
    return result


def scrape_allotments_data() -> list[dict]:
    """
    Scrape allotments data from Datadog allotments page.
    Returns list of allotment mappings.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(ALLOTMENTS_URL, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'lxml')
    
    allotments = []
    
    # Find the allotments table
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        
        current_parent = None
        
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if len(cells) < 3:
                continue
            
            # Check if this is a parent product row (usually has rowspan)
            first_cell = cells[0]
            
            # Check for rowspan which indicates a parent product
            if first_cell.get('rowspan'):
                current_parent = first_cell.get_text(strip=True)
            
            # Get cell texts
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Skip header rows
            if any(header in cell_texts[0].lower() for header in ['parent product', 'allotted product', 'monthly']):
                continue
            
            # Determine columns based on structure
            if len(cells) >= 4:
                # Full row with parent product
                parent = cell_texts[0] if cell_texts[0] else current_parent
                allotted_product = cell_texts[1]
                monthly_value = cell_texts[2]
                hourly_value = cell_texts[3] if len(cells) > 3 else None
            elif len(cells) == 3 and current_parent:
                # Continuation row (parent from rowspan)
                parent = current_parent
                allotted_product = cell_texts[0]
                monthly_value = cell_texts[1]
                hourly_value = cell_texts[2] if len(cells) > 2 else None
            else:
                continue
            
            # Skip empty or header-like rows
            if not parent or not allotted_product:
                continue
            if 'parent product' in parent.lower() or 'allotted product' in allotted_product.lower():
                continue
            
            # Parse the monthly value
            monthly_parsed = parse_allotment_value(monthly_value)
            
            if monthly_parsed:
                allotment = {
                    "parent_product": parent,
                    "allotted_product": allotted_product,
                    "monthly_on_demand": monthly_value,
                    "monthly_parsed": monthly_parsed,
                    "hourly_on_demand": hourly_value
                }
                allotments.append(allotment)
    
    # Deduplicate
    seen = set()
    unique_allotments = []
    for item in allotments:
        key = (item["parent_product"], item["allotted_product"])
        if key not in seen:
            seen.add(key)
            unique_allotments.append(item)
    
    return unique_allotments


def save_allotments_data(data: list[dict]) -> None:
    """Save allotments data to Redis (primary) and file (backup), enriched with product IDs."""
    # Enrich allotments with product IDs
    enriched_data = enrich_allotments_with_product_ids(data)
    
    metadata = {
        "last_sync": datetime.utcnow().isoformat(),
        "allotments_count": len(enriched_data),
        "source_url": ALLOTMENTS_URL
    }
    
    # Try Redis first
    redis = get_redis()
    if is_redis_available():
        redis.set_json(RedisKeys.ALLOTMENTS, enriched_data)
        redis.set_json(f"{RedisKeys.ALLOTMENTS}:metadata", metadata)
        logger.info(f"✅ Saved {len(enriched_data)} allotments to Redis")
    
    # Always save to file as backup
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(ALLOTMENTS_FILE, 'w') as f:
        json.dump(enriched_data, f, indent=2)
    
    with open(ALLOTMENTS_METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)


def load_allotments_data() -> list[dict]:
    """Load allotments data from Redis (primary) or file (fallback)."""
    # Try Redis first
    if is_redis_available():
        data = get_redis().get_json(RedisKeys.ALLOTMENTS)
        if data:
            return data
    
    # Fallback to file
    if not ALLOTMENTS_FILE.exists():
        return []
    with open(ALLOTMENTS_FILE, 'r') as f:
        return json.load(f)


def load_allotments_metadata() -> dict:
    """Load allotments metadata from Redis (primary) or file (fallback)."""
    # Try Redis first
    if is_redis_available():
        metadata = get_redis().get_json(f"{RedisKeys.ALLOTMENTS}:metadata")
        if metadata:
            return metadata
    
    # Fallback to file
    if not ALLOTMENTS_METADATA_FILE.exists():
        return {}
    with open(ALLOTMENTS_METADATA_FILE, 'r') as f:
        return json.load(f)


def get_allotments_for_product(parent_product: str) -> list[dict]:
    """Get all allotments for a given parent product."""
    allotments = load_allotments_data()
    return [
        a for a in allotments 
        if a["parent_product"].lower() == parent_product.lower()
    ]


def sync_allotments() -> tuple[bool, str, int]:
    """Sync allotments data from Datadog website."""
    try:
        data = scrape_allotments_data()
        if data:
            save_allotments_data(data)
            return True, f"Successfully synced {len(data)} allotments", len(data)
        else:
            return False, "No allotments data found", 0
    except Exception as e:
        return False, f"Error syncing allotments: {str(e)}", 0


def ensure_allotments_data() -> tuple[bool, str, int]:
    """Ensure allotments data exists, sync if not."""
    existing_data = load_allotments_data()
    if existing_data:
        metadata = load_allotments_metadata()
        last_sync = metadata.get("last_sync", "unknown")
        return True, f"Loaded {len(existing_data)} allotments (last sync: {last_sync})", len(existing_data)
    
    return sync_allotments()


# Manual allotments data based on the Datadog documentation
# This serves as a fallback if scraping fails
MANUAL_ALLOTMENTS = [
    # Infrastructure Monitoring - Pro
    {
        "parent_product": "Infrastructure Pro",
        "allotted_product": "Custom Metrics",
        "quantity_per_parent": 100,
        "allotted_unit": "custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure Pro",
        "allotted_product": "Ingested Custom Metrics",
        "quantity_per_parent": 100,
        "allotted_unit": "ingested custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure Pro",
        "allotted_product": "Containers",
        "quantity_per_parent": 5,
        "allotted_unit": "containers",
        "per_parent_unit": "host",
        "frequency": "hour"
    },
    {
        "parent_product": "Infrastructure Pro",
        "allotted_product": "Custom Events",
        "quantity_per_parent": 500,
        "allotted_unit": "custom events",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    # Infrastructure Monitoring - Enterprise
    {
        "parent_product": "Infrastructure Enterprise",
        "allotted_product": "Custom Metrics",
        "quantity_per_parent": 200,
        "allotted_unit": "custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure Enterprise",
        "allotted_product": "Ingested Custom Metrics",
        "quantity_per_parent": 200,
        "allotted_unit": "ingested custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure Enterprise",
        "allotted_product": "Containers",
        "quantity_per_parent": 10,
        "allotted_unit": "containers",
        "per_parent_unit": "host",
        "frequency": "hour"
    },
    {
        "parent_product": "Infrastructure Enterprise",
        "allotted_product": "Custom Events",
        "quantity_per_parent": 1000,
        "allotted_unit": "custom events",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    # Infrastructure DevSecOps Pro (same as Infrastructure Pro)
    {
        "parent_product": "Infrastructure DevSecOps Pro",
        "allotted_product": "Custom Metrics",
        "quantity_per_parent": 100,
        "allotted_unit": "custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure DevSecOps Pro",
        "allotted_product": "Ingested Custom Metrics",
        "quantity_per_parent": 100,
        "allotted_unit": "ingested custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure DevSecOps Pro",
        "allotted_product": "Containers",
        "quantity_per_parent": 5,
        "allotted_unit": "containers",
        "per_parent_unit": "host",
        "frequency": "hour"
    },
    {
        "parent_product": "Infrastructure DevSecOps Pro",
        "allotted_product": "Custom Events",
        "quantity_per_parent": 500,
        "allotted_unit": "custom events",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    # Infrastructure DevSecOps Enterprise (same as Infrastructure Enterprise)
    {
        "parent_product": "Infrastructure DevSecOps Enterprise",
        "allotted_product": "Custom Metrics",
        "quantity_per_parent": 200,
        "allotted_unit": "custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure DevSecOps Enterprise",
        "allotted_product": "Ingested Custom Metrics",
        "quantity_per_parent": 200,
        "allotted_unit": "ingested custom metrics",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    {
        "parent_product": "Infrastructure DevSecOps Enterprise",
        "allotted_product": "Containers",
        "quantity_per_parent": 10,
        "allotted_unit": "containers",
        "per_parent_unit": "host",
        "frequency": "hour"
    },
    {
        "parent_product": "Infrastructure DevSecOps Enterprise",
        "allotted_product": "Custom Events",
        "quantity_per_parent": 1000,
        "allotted_unit": "custom events",
        "per_parent_unit": "host",
        "frequency": "month"
    },
    # APM
    {
        "parent_product": "APM",
        "allotted_product": "Indexed Spans",
        "quantity_per_parent": 1000000,
        "allotted_unit": "indexed spans",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM",
        "allotted_product": "Ingested Spans",
        "quantity_per_parent": 150,
        "allotted_unit": "GB",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM",
        "allotted_product": "Profiled Hosts",
        "quantity_per_parent": 1,
        "allotted_unit": "profiled host",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM",
        "allotted_product": "Profiled Containers",
        "quantity_per_parent": 4,
        "allotted_unit": "profiled containers",
        "per_parent_unit": "APM host",
        "frequency": "hour"
    },
    # APM Pro (based on pricing page screenshot)
    {
        "parent_product": "APM Pro",
        "allotted_product": "Indexed Spans",
        "quantity_per_parent": 1000000,
        "allotted_unit": "indexed spans",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM Pro",
        "allotted_product": "Ingested Spans",
        "quantity_per_parent": 150,
        "allotted_unit": "GB",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM Pro",
        "allotted_product": "Data Streams Monitoring",
        "quantity_per_parent": 1,
        "allotted_unit": "DSM host",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    # APM Enterprise
    {
        "parent_product": "APM Enterprise",
        "allotted_product": "Indexed Spans",
        "quantity_per_parent": 1000000,
        "allotted_unit": "indexed spans",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM Enterprise",
        "allotted_product": "Ingested Spans",
        "quantity_per_parent": 150,
        "allotted_unit": "GB",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM Enterprise",
        "allotted_product": "Data Streams Monitoring",
        "quantity_per_parent": 1,
        "allotted_unit": "DSM host",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM Enterprise",
        "allotted_product": "Continuous Profiler",
        "quantity_per_parent": 1,
        "allotted_unit": "profiled host",
        "per_parent_unit": "APM host",
        "frequency": "month"
    },
    {
        "parent_product": "APM Enterprise",
        "allotted_product": "Profiled Containers",
        "quantity_per_parent": 4,
        "allotted_unit": "profiled containers",
        "per_parent_unit": "APM host",
        "frequency": "hour"
    },
    # Database Monitoring
    {
        "parent_product": "Database Monitoring",
        "allotted_product": "Normalized Queries",
        "quantity_per_parent": 200,
        "allotted_unit": "queries",
        "per_parent_unit": "database host",
        "frequency": "month"
    },
    # Continuous Profiler
    {
        "parent_product": "Continuous Profiler",
        "allotted_product": "Profiled Containers",
        "quantity_per_parent": 4,
        "allotted_unit": "profiled containers",
        "per_parent_unit": "profiled host",
        "frequency": "hour"
    },
    # CSM Pro
    {
        "parent_product": "Cloud Security Management Pro",
        "allotted_product": "CSM Pro Containers",
        "quantity_per_parent": 5,
        "allotted_unit": "containers",
        "per_parent_unit": "CSM host",
        "frequency": "hour"
    },
    {
        "parent_product": "Cloud Security Management Pro",
        "allotted_product": "Workflow Automation",
        "quantity_per_parent": 5,
        "allotted_unit": "executions",
        "per_parent_unit": "CSM host",
        "frequency": "month"
    },
    # CSM Enterprise
    {
        "parent_product": "Cloud Security Management Enterprise",
        "allotted_product": "CSM Enterprise Containers",
        "quantity_per_parent": 20,
        "allotted_unit": "containers",
        "per_parent_unit": "CSM host",
        "frequency": "hour"
    },
    {
        "parent_product": "Cloud Security Management Enterprise",
        "allotted_product": "Workflow Automation",
        "quantity_per_parent": 20,
        "allotted_unit": "executions",
        "per_parent_unit": "CSM host",
        "frequency": "month"
    },
    # Serverless
    {
        "parent_product": "Serverless Workload Monitoring - Functions",
        "allotted_product": "Custom Metrics",
        "quantity_per_parent": 5,
        "allotted_unit": "custom metrics",
        "per_parent_unit": "function",
        "frequency": "month"
    },
    {
        "parent_product": "Serverless Workload Monitoring - Apps",
        "allotted_product": "Custom Metrics",
        "quantity_per_parent": 20,
        "allotted_unit": "custom metrics",
        "per_parent_unit": "instance app",
        "frequency": "month"
    },
    # Test/CI
    {
        "parent_product": "Pipeline Visibility",
        "allotted_product": "Pipeline Spans",
        "quantity_per_parent": 400000,
        "allotted_unit": "spans",
        "per_parent_unit": "committer",
        "frequency": "month"
    },
    {
        "parent_product": "Test Optimization",
        "allotted_product": "Test Spans",
        "quantity_per_parent": 1000000,
        "allotted_unit": "spans",
        "per_parent_unit": "committer",
        "frequency": "month"
    },
]


def get_manual_allotments() -> list[dict]:
    """Get the manually defined allotments."""
    return MANUAL_ALLOTMENTS


def save_manual_allotments() -> None:
    """Save manual allotments to Redis (primary) and file (backup), enriched with product IDs."""
    # Enrich manual allotments with product IDs
    enriched_data = enrich_allotments_with_product_ids(MANUAL_ALLOTMENTS)
    
    metadata = {
        "last_sync": datetime.utcnow().isoformat(),
        "allotments_count": len(enriched_data),
        "source": "manual",
        "source_url": ALLOTMENTS_URL
    }
    
    # Try Redis first
    redis = get_redis()
    if is_redis_available():
        redis.set_json(RedisKeys.ALLOTMENTS_MANUAL, enriched_data)
        redis.set_json(RedisKeys.ALLOTMENTS, enriched_data)  # Also save to main key
        redis.set_json(f"{RedisKeys.ALLOTMENTS}:metadata", metadata)
        logger.info(f"✅ Saved {len(enriched_data)} manual allotments to Redis")
    
    # Always save to file as backup
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(ALLOTMENTS_FILE, 'w') as f:
        json.dump(enriched_data, f, indent=2)
    
    with open(ALLOTMENTS_METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

