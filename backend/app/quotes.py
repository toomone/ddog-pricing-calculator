import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Quote, QuoteLineItem
from .scraper import load_pricing_data, parse_price
from .redis_client import get_redis, is_redis_available, RedisKeys


DATA_DIR = Path(__file__).parent.parent / "data"
QUOTES_DIR = DATA_DIR / "quotes"


def get_quote_file(quote_id: str) -> Path:
    """Get the file path for a quote by ID."""
    return QUOTES_DIR / f"quote-{quote_id}.json"


def get_price_for_product(product_id: str, product_name: str, billing_type: str, region: str = "us") -> tuple[float, str, str]:
    """Get price for a product based on billing type. Returns (price, billing_unit, product_id)."""
    pricing_data = load_pricing_data(region)
    
    billing_map = {
        'annually': 'billed_annually',
        'monthly': 'billed_month_to_month',
        'on_demand': 'on_demand'
    }
    
    price_field = billing_map.get(billing_type, 'billed_annually')
    
    # Try to find by ID first
    if product_id:
        for item in pricing_data:
            if item.get('id') == product_id:
                price_str = item.get(price_field) or item.get('billed_annually') or '0'
                return parse_price(price_str), item.get('billing_unit', 'per unit'), item.get('id', '')
    
    # Fallback to name matching
    for item in pricing_data:
        if item['product'] == product_name:
            price_str = item.get(price_field) or item.get('billed_annually') or '0'
            return parse_price(price_str), item.get('billing_unit', 'per unit'), item.get('id', '')
    
    return 0.0, 'per unit', ''


def get_all_prices_for_product(product_id: str, product_name: str, region: str = "us") -> dict:
    """Get all prices (annually, monthly, on-demand) for a product. Returns dict with prices."""
    pricing_data = load_pricing_data(region)
    
    # Try to find by ID first
    target_item = None
    if product_id:
        for item in pricing_data:
            if item.get('id') == product_id:
                target_item = item
                break
    
    # Fallback to name matching
    if not target_item:
        for item in pricing_data:
            if item['product'] == product_name:
                target_item = item
                break
    
    if not target_item:
        return {
            'annually': 0.0,
            'monthly': 0.0,
            'on_demand': 0.0,
            'billing_unit': 'per unit',
            'id': ''
        }
    
    return {
        'annually': parse_price(target_item.get('billed_annually') or '0'),
        'monthly': parse_price(target_item.get('billed_month_to_month') or '0'),
        'on_demand': parse_price(target_item.get('on_demand') or '0'),
        'billing_unit': target_item.get('billing_unit', 'per unit'),
        'id': target_item.get('id', '')
    }


def save_quote_file(quote: Quote) -> None:
    """Save a quote to Redis (primary) and file (backup)."""
    quote_data = quote.model_dump()
    
    # Try Redis first
    redis = get_redis()
    if is_redis_available():
        redis.set_json(RedisKeys.quote(quote.id), quote_data)
        # Add to index for listing
        redis.add_to_index(RedisKeys.QUOTES_INDEX, quote.id)
        print(f"✅ Saved quote {quote.id} to Redis")
    
    # Always save to file as backup
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    quote_file = get_quote_file(quote.id)
    with open(quote_file, 'w') as f:
        json.dump(quote_data, f, indent=2)


def load_quote_file(quote_id: str) -> Optional[dict]:
    """Load a quote from Redis (primary) or file (fallback)."""
    # Try Redis first
    if is_redis_available():
        data = get_redis().get_json(RedisKeys.quote(quote_id))
        if data:
            return data
    
    # Fallback to file
    quote_file = get_quote_file(quote_id)
    if not quote_file.exists():
        return None
    with open(quote_file, 'r') as f:
        return json.load(f)


def create_quote(name: Optional[str], region: str, billing_type: str, items: list[dict]) -> Quote:
    """Create a new quote."""
    quote_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    quote_items = []
    total = 0.0
    total_annually = 0.0
    total_monthly = 0.0
    total_on_demand = 0.0
    
    for item in items:
        product_id = item.get('id', '')
        product = item.get('product', '')
        quantity = int(item.get('quantity', 0))
        
        # Get all prices for comparison
        all_prices = get_all_prices_for_product(product_id, product, region)
        
        unit_price, billing_unit, resolved_id = get_price_for_product(product_id, product, billing_type, region)
        item_total = unit_price * quantity
        total += item_total
        
        # Calculate totals for all billing types
        total_annually += all_prices['annually'] * quantity
        total_monthly += all_prices['monthly'] * quantity
        total_on_demand += all_prices['on_demand'] * quantity
        
        # Process allotments with IDs
        allotments = []
        for allot in item.get('allotments', []):
            from .models import AllotmentInfo
            allotments.append(AllotmentInfo(
                id=allot.get('id', ''),
                allotted_product=allot.get('allotted_product', ''),
                quantity_included=allot.get('quantity_included', 0),
                allotted_unit=allot.get('allotted_unit', 'units')
            ))
        
        quote_items.append(QuoteLineItem(
            id=resolved_id or product_id,
            product=product,
            billing_unit=billing_unit,
            quantity=quantity,
            unit_price=unit_price,
            total_price=item_total,
            allotments=allotments
        ))
    
    quote = Quote(
        id=quote_id,
        name=name or f"Quote {quote_id[:8]}",
        region=region,
        billing_type=billing_type,
        items=quote_items,
        total=total,
        total_annually=total_annually,
        total_monthly=total_monthly,
        total_on_demand=total_on_demand,
        created_at=now,
        updated_at=now
    )
    
    # Save quote to Redis and file
    save_quote_file(quote)
    
    return quote


def get_quote(quote_id: str) -> Optional[Quote]:
    """Get a quote by ID."""
    quote_data = load_quote_file(quote_id)
    if quote_data:
        return Quote(**quote_data)
    return None


def update_quote(quote_id: str, name: Optional[str], region: str, billing_type: str, items: list[dict]) -> Optional[Quote]:
    """Update an existing quote."""
    old_quote_data = load_quote_file(quote_id)
    
    if not old_quote_data:
        return None
    
    now = datetime.utcnow().isoformat()
    
    quote_items = []
    total = 0.0
    total_annually = 0.0
    total_monthly = 0.0
    total_on_demand = 0.0
    
    for item in items:
        product_id = item.get('id', '')
        product = item.get('product', '')
        quantity = int(item.get('quantity', 0))
        
        # Get all prices for comparison
        all_prices = get_all_prices_for_product(product_id, product, region)
        
        unit_price, billing_unit, resolved_id = get_price_for_product(product_id, product, billing_type, region)
        item_total = unit_price * quantity
        total += item_total
        
        # Calculate totals for all billing types
        total_annually += all_prices['annually'] * quantity
        total_monthly += all_prices['monthly'] * quantity
        total_on_demand += all_prices['on_demand'] * quantity
        
        # Process allotments with IDs
        allotments = []
        for allot in item.get('allotments', []):
            from .models import AllotmentInfo
            allotments.append(AllotmentInfo(
                id=allot.get('id', ''),
                allotted_product=allot.get('allotted_product', ''),
                quantity_included=allot.get('quantity_included', 0),
                allotted_unit=allot.get('allotted_unit', 'units')
            ))
        
        quote_items.append(QuoteLineItem(
            id=resolved_id or product_id,
            product=product,
            billing_unit=billing_unit,
            quantity=quantity,
            unit_price=unit_price,
            total_price=item_total,
            allotments=allotments
        ))
    
    quote = Quote(
        id=quote_id,
        name=name or old_quote_data.get('name', f"Quote {quote_id[:8]}"),
        region=region,
        billing_type=billing_type,
        items=quote_items,
        total=total,
        total_annually=total_annually,
        total_monthly=total_monthly,
        total_on_demand=total_on_demand,
        created_at=old_quote_data.get('created_at', now),
        updated_at=now
    )
    
    # Save updated quote
    save_quote_file(quote)
    
    return quote


def delete_quote(quote_id: str) -> bool:
    """Delete a quote from Redis and file."""
    deleted = False
    
    # Try Redis first
    if is_redis_available():
        redis = get_redis()
        if redis.delete(RedisKeys.quote(quote_id)):
            redis.remove_from_index(RedisKeys.QUOTES_INDEX, quote_id)
            deleted = True
    
    # Also delete file
    quote_file = get_quote_file(quote_id)
    if quote_file.exists():
        quote_file.unlink()
        deleted = True
    
    return deleted


def list_quotes() -> list[Quote]:
    """List all quotes from Redis (primary) or file (fallback)."""
    quotes = []
    
    # Try Redis first
    if is_redis_available():
        redis = get_redis()
        quote_ids = redis.get_index(RedisKeys.QUOTES_INDEX)
        for quote_id in quote_ids:
            quote_data = redis.get_json(RedisKeys.quote(quote_id))
            if quote_data:
                try:
                    quotes.append(Quote(**quote_data))
                except Exception:
                    continue
        if quotes:
            return quotes
    
    # Fallback to file
    if not QUOTES_DIR.exists():
        return []
    
    for quote_file in QUOTES_DIR.glob("quote-*.json"):
        try:
            with open(quote_file, 'r') as f:
                quote_data = json.load(f)
                quotes.append(Quote(**quote_data))
        except Exception:
            continue
    
    # Sort by created_at descending
    quotes.sort(key=lambda q: q.created_at, reverse=True)
    return quotes
