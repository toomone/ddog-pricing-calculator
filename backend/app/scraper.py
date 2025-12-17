import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
from datetime import datetime


DATA_DIR = Path(__file__).parent.parent / "data"
PRICING_DIR = DATA_DIR / "pricing"

# Datadog regions with their pricing page URLs
REGIONS = {
    "us1": {
        "name": "US1 (Virginia)",
        "url": "https://www.datadoghq.com/pricing/list/",
        "site": "datadoghq.com"
    },
    "us3": {
        "name": "US3 (Virginia)", 
        "url": "https://www.datadoghq.com/pricing/list/",
        "site": "us3.datadoghq.com"
    },
    "us5": {
        "name": "US5 (Oregon)",
        "url": "https://www.datadoghq.com/pricing/list/",
        "site": "us5.datadoghq.com"
    },
    "eu1": {
        "name": "EU1 (Frankfurt)",
        "url": "https://www.datadoghq.com/pricing/list/",
        "site": "datadoghq.eu"
    },
    "ap1": {
        "name": "AP1 (Tokyo)",
        "url": "https://www.datadoghq.com/pricing/list/",
        "site": "ap1.datadoghq.com"
    },
    "gov": {
        "name": "US1-FED (GovCloud)",
        "url": "https://www.datadoghq.com/pricing/list/",
        "site": "ddog-gov.com"
    }
}

DEFAULT_REGION = "us1"


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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(region_info["url"], headers=headers, timeout=30)
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
                        
                        item = {
                            "region": region,
                            "product": product_name.strip(),
                            "billing_unit": billing_unit.strip() if billing_unit else "per unit",
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
    """Save pricing data to JSON file for a specific region."""
    PRICING_DIR.mkdir(parents=True, exist_ok=True)
    
    pricing_file = get_pricing_file(region)
    with open(pricing_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Save metadata with last sync timestamp
    region_info = REGIONS.get(region, REGIONS[DEFAULT_REGION])
    metadata = {
        "region": region,
        "region_name": region_info["name"],
        "site": region_info["site"],
        "last_sync": datetime.utcnow().isoformat(),
        "products_count": len(data),
        "source_url": region_info["url"]
    }
    metadata_file = get_metadata_file(region)
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def load_pricing_data(region: str = DEFAULT_REGION) -> list[dict]:
    """Load pricing data from JSON file for a specific region."""
    pricing_file = get_pricing_file(region)
    if not pricing_file.exists():
        return []
    with open(pricing_file, 'r') as f:
        return json.load(f)


def load_metadata(region: str = DEFAULT_REGION) -> dict:
    """Load metadata about the pricing data for a specific region."""
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
            return True, f"Successfully synced {len(data)} products for {region_name}", len(data)
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
        return True, f"Loaded {len(existing_data)} products for {region_name} (last sync: {last_sync})", len(existing_data)
    
    # No data exists, sync now
    return sync_pricing(region)
