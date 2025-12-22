"""
Template management for PriceHound.
Handles storage and retrieval of quote templates from Redis and JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .models import Template, TemplateItem
from .redis_client import get_redis, is_redis_available, RedisKeys

logger = logging.getLogger("pricehound.templates")

# Directory paths
DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = DATA_DIR / "templates"


def load_templates_from_files() -> list[dict]:
    """Load all template JSON files from the templates directory."""
    templates = []
    
    if not TEMPLATES_DIR.exists():
        logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
        return templates
    
    for template_file in TEMPLATES_DIR.glob("template-*.json"):
        try:
            with open(template_file, 'r') as f:
                template_data = json.load(f)
                templates.append(template_data)
                logger.debug(f"Loaded template from {template_file.name}")
        except Exception as e:
            logger.error(f"Failed to load template {template_file}: {e}")
    
    return templates


def sync_templates_to_redis() -> int:
    """Load templates from JSON files and sync to Redis. Returns count synced."""
    redis_client = get_redis()
    
    if not redis_client or not is_redis_available():
        logger.warning("Redis not available, cannot sync templates")
        return 0
    
    templates_data = load_templates_from_files()
    count = 0
    
    for tmpl_data in templates_data:
        try:
            template_id = tmpl_data["id"]
            
            # Store template in Redis
            redis_client.set_json(
                RedisKeys.template(template_id),
                tmpl_data
            )
            # Add to index
            redis_client.add_to_index(RedisKeys.TEMPLATES_INDEX, template_id)
            count += 1
            logger.info(f"Synced template: {tmpl_data.get('name', template_id)}")
            
        except Exception as e:
            logger.error(f"Failed to sync template {tmpl_data.get('name', 'unknown')}: {e}")
    
    return count


def ensure_templates() -> tuple[bool, str, int]:
    """Ensure templates exist in Redis, sync from files if needed."""
    redis_client = get_redis()
    
    if redis_client and is_redis_available():
        # Check if templates exist in Redis
        template_ids = redis_client.get_index(RedisKeys.TEMPLATES_INDEX)
        
        if not template_ids:
            # No templates in Redis, sync from files
            logger.info("No templates in Redis, syncing from files...")
            count = sync_templates_to_redis()
            return True, f"Synced {count} templates from files to Redis", count
        else:
            return True, f"Found {len(template_ids)} templates in Redis", len(template_ids)
    else:
        # Redis not available, will use file fallback
        templates = load_templates_from_files()
        return True, f"Loaded {len(templates)} templates from files (Redis unavailable)", len(templates)


def get_all_templates() -> list[Template]:
    """Get all templates from Redis or files."""
    redis_client = get_redis()
    
    if redis_client and is_redis_available():
        try:
            # Get all template IDs from index
            template_ids = redis_client.get_index(RedisKeys.TEMPLATES_INDEX)
            
            if not template_ids:
                # No templates in Redis, sync from files first
                sync_templates_to_redis()
                template_ids = redis_client.get_index(RedisKeys.TEMPLATES_INDEX)
            
            templates = []
            for template_id in template_ids:
                template_data = redis_client.get_json(RedisKeys.template(template_id))
                if template_data:
                    templates.append(_dict_to_template(template_data))
            
            # Sort by name for consistent ordering
            templates.sort(key=lambda t: t.name)
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get templates from Redis: {e}")
    
    # Fallback to loading from files
    logger.info("Loading templates from files (Redis fallback)")
    return [_dict_to_template(t) for t in load_templates_from_files()]


def get_template(template_id: str) -> Optional[Template]:
    """Get a single template by ID."""
    redis_client = get_redis()
    
    if redis_client and is_redis_available():
        try:
            template_data = redis_client.get_json(RedisKeys.template(template_id))
            if template_data:
                return _dict_to_template(template_data)
        except Exception as e:
            logger.error(f"Failed to get template {template_id} from Redis: {e}")
    
    # Fallback to files
    for tmpl_data in load_templates_from_files():
        if tmpl_data.get("id") == template_id:
            return _dict_to_template(tmpl_data)
    
    return None


def _dict_to_template(data: dict) -> Template:
    """Convert a dict to a Template model."""
    return Template(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        region=data.get("region", "us"),
        billing_type=data.get("billing_type", "annually"),
        items=[TemplateItem(**item) for item in data.get("items", [])],
        created_at=data.get("created_at", "")
    )
