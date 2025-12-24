"""
Redis client utility for PriceHound.
Handles connection management and provides helper functions for storing/retrieving data.
"""

import json
import redis
import logging
from typing import Optional, Any
from datetime import datetime

from .config import REDIS_URL, is_redis_storage

# Configure logging
logger = logging.getLogger("pricehound.redis")

# Key prefixes
class RedisKeys:
    """Redis key patterns for different data types."""
    PRICING = "pricing:{region}"
    PRICING_METADATA = "pricing:{region}:metadata"
    ALLOTMENTS = "allotments"
    ALLOTMENTS_MANUAL = "allotments:manual"
    QUOTE = "quote:{quote_id}"
    QUOTES_INDEX = "quotes:index"
    TEMPLATE = "template:{template_id}"
    TEMPLATES_INDEX = "templates:index"
    
    @staticmethod
    def pricing(region: str) -> str:
        return f"pricing:{region}"
    
    @staticmethod
    def pricing_metadata(region: str) -> str:
        return f"pricing:{region}:metadata"
    
    @staticmethod
    def quote(quote_id: str) -> str:
        return f"quote:{quote_id}"
    
    @staticmethod
    def template(template_id: str) -> str:
        return f"template:{template_id}"


class RedisClient:
    """Redis client wrapper with helper methods for JSON storage."""
    
    _instance: Optional['RedisClient'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        """Singleton pattern to reuse connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection if not already connected and Redis storage is configured."""
        if self._client is None and is_redis_storage():
            self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        if not is_redis_storage():
            logger.info("📁 File storage configured, skipping Redis connection")
            return
        
        try:
            self._client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self._client.ping()
            logger.info("✅ Connected to Redis (storage mode: redis)")
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.error("⚠️ Redis storage is configured but connection failed!")
            self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get the Redis client."""
        return self._client
    
    # JSON helpers
    def set_json(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Store JSON data in Redis."""
        if not self.is_connected:
            return False
        try:
            json_str = json.dumps(data, default=str)
            if ttl:
                self._client.setex(key, ttl, json_str)
            else:
                self._client.set(key, json_str)
            return True
        except Exception as e:
            logger.error(f"Redis set_json error: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Any]:
        """Retrieve JSON data from Redis."""
        if not self.is_connected:
            return None
        try:
            data = self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get_json error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.is_connected:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        if not self.is_connected:
            return False
        try:
            return self._client.exists(key) > 0
        except:
            return False
    
    def keys(self, pattern: str) -> list[str]:
        """Get all keys matching a pattern."""
        if not self.is_connected:
            return []
        try:
            return self._client.keys(pattern)
        except:
            return []
    
    # Sorted set helpers for quote indexing
    def add_to_index(self, index_key: str, member: str, score: Optional[float] = None) -> bool:
        """Add a member to a sorted set index."""
        if not self.is_connected:
            return False
        try:
            if score is None:
                score = datetime.utcnow().timestamp()
            self._client.zadd(index_key, {member: score})
            return True
        except Exception as e:
            logger.error(f"Redis add_to_index error: {e}")
            return False
    
    def get_index(self, index_key: str, start: int = 0, end: int = -1) -> list[str]:
        """Get members from a sorted set index (newest first)."""
        if not self.is_connected:
            return []
        try:
            return self._client.zrevrange(index_key, start, end)
        except:
            return []
    
    def remove_from_index(self, index_key: str, member: str) -> bool:
        """Remove a member from a sorted set index."""
        if not self.is_connected:
            return False
        try:
            self._client.zrem(index_key, member)
            return True
        except:
            return False


# Global instance
redis_client = RedisClient()


def get_redis() -> RedisClient:
    """Get the Redis client instance."""
    return redis_client


def is_redis_available() -> bool:
    """Check if Redis storage is configured and connected."""
    return is_redis_storage() and redis_client.is_connected

