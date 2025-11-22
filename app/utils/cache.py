import redis
import json
from typing import Optional, Any, Union
from datetime import timedelta
import os


class CacheService:
    """Сервис кэширования на Redis.

    Обёртка над redis_client с асинхронными методами,
    чтобы удобно вызывать их из async-кода FastAPI.
    """

    def __init__(self):
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

    async def get(self, key: str) -> Optional[str]:
        """Получение строкового значения из кэша."""
        try:
            value = self.redis_client.get(key)
            return value.decode("utf-8") if value else None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: str, expire: Optional[Union[int, timedelta]] = None) -> bool:
        """Сохранение строкового значения в кэш.

        expire — время жизни в секундах или timedelta.
        """
        try:
            ex = None
            if isinstance(expire, timedelta):
                ex = int(expire.total_seconds())
            else:
                ex = expire
            self.redis_client.set(key, value, ex=ex)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        """Получение JSON-значения (dict/list) из кэша."""
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception as e:
            print(f"Cache get_json error: {e}")
            return None

    async def set_json(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> bool:
        """Сохранение JSON-значения (dict/list) в кэш."""
        try:
            raw = json.dumps(value, ensure_ascii=False)
            return await self.set(key, raw, expire=expire)
        except Exception as e:
            print(f"Cache set_json error: {e}")
            return False

    async def delete(self, key: str) -> int:
        """Удаление ключа."""
        try:
            return int(self.redis_client.delete(key) or 0)
        except Exception as e:
            print(f"Cache delete error: {e}")
            return 0

    async def delete_pattern(self, pattern: str) -> int:
        """Удаление значений по паттерну."""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return int(self.redis_client.delete(*keys) or 0)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0


# Глобальный экземпляр сервиса кэширования
cache_service = CacheService()
