import json
import uuid
import logging
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Quote, QuoteLineItem
from .scraper import load_pricing_data, parse_price
from .redis_client import get_redis, is_redis_available, RedisKeys
from .config import get_storage_type

# Quote TTL configuration
QUOTE_TTL_DAYS = 30  # Quotes expire after 30 days
QUOTE_TTL_SECONDS = QUOTE_TTL_DAYS * 24 * 60 * 60

# Maximum number of quotes to keep (for garbage collection)
MAX_QUOTES = 5000

# Memory warning threshold (in bytes) - warn when 80% full
MEMORY_WARNING_THRESHOLD = 0.80


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a salt."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((salt + password).encode())
    return f"{salt}${hash_obj.hexdigest()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    if not password_hash or '$' not in password_hash:
        return False
    salt, stored_hash = password_hash.split('$', 1)
    hash_obj = hashlib.sha256((salt + password).encode())
    return hash_obj.hexdigest() == stored_hash

logger = logging.getLogger("pricehound.quotes")


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


def _check_redis_memory() -> None:
    """Check Redis memory usage and log warnings if needed."""
    redis = get_redis()
    memory_info = redis.get_memory_usage()
    if not memory_info:
        return
    
    used = memory_info.get('used_memory', 0)
    max_mem = memory_info.get('maxmemory', 0)
    if max_mem <= 0:
        return
    
    usage_ratio = used / max_mem
    used_human = memory_info.get('used_memory_human', 'N/A')
    max_human = memory_info.get('maxmemory_human', 'N/A')
    
    if usage_ratio >= 0.95:
        logger.error(
            f"🚨 REDIS STORAGE CRITICAL: Database is {usage_ratio*100:.1f}% full "
            f"({used_human} / {max_human})! Running automatic cleanup..."
        )
        cleanup_old_quotes(max_quotes=MAX_QUOTES // 2)  # Aggressive cleanup
    elif usage_ratio >= MEMORY_WARNING_THRESHOLD:
        logger.warning(
            f"⚠️ REDIS STORAGE WARNING: Database is {usage_ratio*100:.1f}% full "
            f"({used_human} / {max_human}). Consider cleaning up old quotes!"
        )


def save_quote_file(quote: Quote) -> None:
    """Save a quote to configured storage (Redis OR file)."""
    quote_data = quote.model_dump()
    
    if is_redis_available():
        redis = get_redis()
        
        # Check memory usage before saving
        _check_redis_memory()
        
        # Save to Redis with TTL
        redis.set_json(RedisKeys.quote(quote.id), quote_data, ttl=QUOTE_TTL_SECONDS)
        # Add to index for listing
        redis.add_to_index(RedisKeys.QUOTES_INDEX, quote.id)
        logger.info(f"✅ Saved quote {quote.id} to Redis (TTL: {QUOTE_TTL_DAYS} days)")
        
        # Run periodic cleanup to remove excess quotes
        cleanup_old_quotes()
    else:
        # Save to file
        QUOTES_DIR.mkdir(parents=True, exist_ok=True)
        quote_file = get_quote_file(quote.id)
        with open(quote_file, 'w') as f:
            json.dump(quote_data, f, indent=2)
        logger.info(f"✅ Saved quote {quote.id} to file")


def load_quote_file(quote_id: str) -> Optional[dict]:
    """Load a quote from configured storage (Redis OR file)."""
    if is_redis_available():
        # Load from Redis
        return get_redis().get_json(RedisKeys.quote(quote_id))
    else:
        # Load from file
        quote_file = get_quote_file(quote_id)
        if not quote_file.exists():
            return None
        with open(quote_file, 'r') as f:
            return json.load(f)


def create_quote(name: Optional[str], region: str, billing_type: str, items: list[dict], edit_password: Optional[str] = None, description: Optional[str] = None) -> Quote:
    """Create a new quote with optional password protection."""
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
            # Add prices for all billing types
            unit_price_annually=all_prices['annually'],
            unit_price_monthly=all_prices['monthly'],
            unit_price_on_demand=all_prices['on_demand'],
            total_price_annually=all_prices['annually'] * quantity,
            total_price_monthly=all_prices['monthly'] * quantity,
            total_price_on_demand=all_prices['on_demand'] * quantity,
            allotments=allotments
        ))
    
    # Hash password if provided
    password_hash = hash_password(edit_password) if edit_password else None
    
    quote = Quote(
        id=quote_id,
        name=name or f"Quote {quote_id[:8]}",
        description=description,
        region=region,
        billing_type=billing_type,
        items=quote_items,
        total=total,
        total_annually=total_annually,
        total_monthly=total_monthly,
        total_on_demand=total_on_demand,
        created_at=now,
        updated_at=now,
        edit_password_hash=password_hash,
        is_protected=password_hash is not None
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


def update_quote(quote_id: str, name: Optional[str], region: str, billing_type: str, items: list[dict], edit_password: Optional[str] = None, description: Optional[str] = None) -> tuple[Optional[Quote], str]:
    """Update an existing quote. Returns (quote, error_message)."""
    old_quote_data = load_quote_file(quote_id)
    
    if not old_quote_data:
        return None, "Quote not found"
    
    # Check password protection
    stored_hash = old_quote_data.get('edit_password_hash')
    if stored_hash:
        if not edit_password:
            return None, "Password required to edit this quote"
        if not verify_password(edit_password, stored_hash):
            return None, "Invalid password"
    
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
            # Add prices for all billing types
            unit_price_annually=all_prices['annually'],
            unit_price_monthly=all_prices['monthly'],
            unit_price_on_demand=all_prices['on_demand'],
            total_price_annually=all_prices['annually'] * quantity,
            total_price_monthly=all_prices['monthly'] * quantity,
            total_price_on_demand=all_prices['on_demand'] * quantity,
            allotments=allotments
        ))
    
    quote = Quote(
        id=quote_id,
        name=name or old_quote_data.get('name', f"Quote {quote_id[:8]}"),
        description=description if description is not None else old_quote_data.get('description'),
        region=region,
        billing_type=billing_type,
        items=quote_items,
        total=total,
        total_annually=total_annually,
        total_monthly=total_monthly,
        total_on_demand=total_on_demand,
        created_at=old_quote_data.get('created_at', now),
        updated_at=now,
        # Preserve password protection
        edit_password_hash=stored_hash,
        is_protected=stored_hash is not None
    )
    
    # Save updated quote
    save_quote_file(quote)
    
    return quote, ""


def verify_quote_password(quote_id: str, password: str) -> tuple[bool, str]:
    """Verify password for a quote. Returns (is_valid, message)."""
    quote_data = load_quote_file(quote_id)
    
    if not quote_data:
        return False, "Quote not found"
    
    stored_hash = quote_data.get('edit_password_hash')
    if not stored_hash:
        return True, "Quote is not password protected"
    
    if verify_password(password, stored_hash):
        return True, "Password verified"
    
    return False, "Invalid password"


def delete_quote(quote_id: str) -> bool:
    """Delete a quote from configured storage (Redis OR file)."""
    if is_redis_available():
        # Delete from Redis
        redis = get_redis()
        if redis.delete(RedisKeys.quote(quote_id)):
            redis.remove_from_index(RedisKeys.QUOTES_INDEX, quote_id)
            return True
        return False
    else:
        # Delete from file
        quote_file = get_quote_file(quote_id)
        if quote_file.exists():
            quote_file.unlink()
            return True
        return False


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


def cleanup_old_quotes(max_quotes: int = MAX_QUOTES) -> int:
    """Remove oldest quotes to stay under the limit. Returns count of deleted quotes.
    
    This function:
    1. Checks the current quote count
    2. If over limit, deletes the oldest quotes
    3. Also cleans up orphaned index entries (quotes that expired via TTL)
    """
    if not is_redis_available():
        return 0
    
    redis = get_redis()
    quote_count = redis.get_index_count(RedisKeys.QUOTES_INDEX)
    
    # First, clean up orphaned index entries (quotes deleted by TTL but still in index)
    all_quote_ids = redis.get_index(RedisKeys.QUOTES_INDEX)
    orphaned = 0
    for quote_id in all_quote_ids:
        if not redis.exists(RedisKeys.quote(quote_id)):
            redis.remove_from_index(RedisKeys.QUOTES_INDEX, quote_id)
            orphaned += 1
    
    if orphaned > 0:
        logger.info(f"🧹 Cleaned up {orphaned} expired quote index entries")
        quote_count = redis.get_index_count(RedisKeys.QUOTES_INDEX)
    
    # Then, if still over limit, delete oldest quotes
    if quote_count <= max_quotes:
        return orphaned
    
    excess = quote_count - max_quotes
    oldest_quote_ids = redis.get_oldest_from_index(RedisKeys.QUOTES_INDEX, excess)
    
    deleted = 0
    for quote_id in oldest_quote_ids:
        if delete_quote(quote_id):
            deleted += 1
            logger.info(f"🗑️ Garbage collected old quote: {quote_id}")
    
    if deleted > 0:
        logger.info(f"🧹 Cleaned up {deleted} old quotes (was {quote_count}, now {quote_count - deleted})")
    
    return orphaned + deleted


def get_quotes_stats() -> dict:
    """Get statistics about quotes storage for monitoring."""
    if is_redis_available():
        redis = get_redis()
        memory = redis.get_memory_usage()
        quote_count = redis.get_index_count(RedisKeys.QUOTES_INDEX)
        
        # Calculate usage percentage if maxmemory is set
        usage_percent = None
        if memory.get('maxmemory', 0) > 0:
            usage_percent = (memory.get('used_memory', 0) / memory['maxmemory']) * 100
        
        return {
            'quote_count': quote_count,
            'max_quotes': MAX_QUOTES,
            'ttl_days': QUOTE_TTL_DAYS,
            'storage': 'redis',
            'memory': {
                'used': memory.get('used_memory_human', 'N/A'),
                'max': memory.get('maxmemory_human', 'N/A'),
                'usage_percent': round(usage_percent, 1) if usage_percent else None
            }
        }
    else:
        quote_files = list(QUOTES_DIR.glob("quote-*.json")) if QUOTES_DIR.exists() else []
        return {
            'quote_count': len(quote_files),
            'max_quotes': MAX_QUOTES,
            'ttl_days': None,
            'storage': 'file'
        }
