import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Quote, QuoteLineItem
from .scraper import load_pricing_data, parse_price


DATA_DIR = Path(__file__).parent.parent / "data"
QUOTES_DIR = DATA_DIR / "quotes"


def get_quote_file(quote_id: str) -> Path:
    """Get the file path for a quote by ID."""
    return QUOTES_DIR / f"quote-{quote_id}.json"


def get_price_for_product(product: str, billing_type: str) -> tuple[float, str]:
    """Get price for a product based on billing type."""
    pricing_data = load_pricing_data()
    
    billing_map = {
        'annually': 'billed_annually',
        'monthly': 'billed_month_to_month',
        'on_demand': 'on_demand'
    }
    
    price_field = billing_map.get(billing_type, 'billed_annually')
    
    for item in pricing_data:
        if item['product'] == product:
            price_str = item.get(price_field) or item.get('billed_annually') or '0'
            return parse_price(price_str), item.get('billing_unit', 'per unit')
    
    return 0.0, 'per unit'


def save_quote_file(quote: Quote) -> None:
    """Save a quote to its own JSON file."""
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    quote_file = get_quote_file(quote.id)
    with open(quote_file, 'w') as f:
        json.dump(quote.model_dump(), f, indent=2)


def load_quote_file(quote_id: str) -> Optional[dict]:
    """Load a quote from its JSON file."""
    quote_file = get_quote_file(quote_id)
    if not quote_file.exists():
        return None
    with open(quote_file, 'r') as f:
        return json.load(f)


def create_quote(name: Optional[str], billing_type: str, items: list[dict]) -> Quote:
    """Create a new quote."""
    quote_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    quote_items = []
    total = 0.0
    
    for item in items:
        product = item.get('product', '')
        quantity = int(item.get('quantity', 0))
        
        unit_price, billing_unit = get_price_for_product(product, billing_type)
        item_total = unit_price * quantity
        total += item_total
        
        quote_items.append(QuoteLineItem(
            product=product,
            billing_unit=billing_unit,
            quantity=quantity,
            unit_price=unit_price,
            total_price=item_total
        ))
    
    quote = Quote(
        id=quote_id,
        name=name or f"Quote {quote_id[:8]}",
        billing_type=billing_type,
        items=quote_items,
        total=total,
        created_at=now,
        updated_at=now
    )
    
    # Save quote to its own file
    save_quote_file(quote)
    
    return quote


def get_quote(quote_id: str) -> Optional[Quote]:
    """Get a quote by ID."""
    quote_data = load_quote_file(quote_id)
    if quote_data:
        return Quote(**quote_data)
    return None


def update_quote(quote_id: str, name: Optional[str], billing_type: str, items: list[dict]) -> Optional[Quote]:
    """Update an existing quote."""
    old_quote_data = load_quote_file(quote_id)
    
    if not old_quote_data:
        return None
    
    now = datetime.utcnow().isoformat()
    
    quote_items = []
    total = 0.0
    
    for item in items:
        product = item.get('product', '')
        quantity = int(item.get('quantity', 0))
        
        unit_price, billing_unit = get_price_for_product(product, billing_type)
        item_total = unit_price * quantity
        total += item_total
        
        quote_items.append(QuoteLineItem(
            product=product,
            billing_unit=billing_unit,
            quantity=quantity,
            unit_price=unit_price,
            total_price=item_total
        ))
    
    quote = Quote(
        id=quote_id,
        name=name or old_quote_data.get('name', f"Quote {quote_id[:8]}"),
        billing_type=billing_type,
        items=quote_items,
        total=total,
        created_at=old_quote_data.get('created_at', now),
        updated_at=now
    )
    
    # Save updated quote
    save_quote_file(quote)
    
    return quote


def delete_quote(quote_id: str) -> bool:
    """Delete a quote."""
    quote_file = get_quote_file(quote_id)
    if quote_file.exists():
        quote_file.unlink()
        return True
    return False


def list_quotes() -> list[Quote]:
    """List all quotes."""
    if not QUOTES_DIR.exists():
        return []
    
    quotes = []
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
