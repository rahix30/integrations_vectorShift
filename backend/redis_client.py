import os
import redis

redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

async def add_key_value_redis(key, value, expire=None):
    redis_client.set(key, value)
    if expire:
        redis_client.expire(key, expire)

async def get_value_redis(key):
    return redis_client.get(key)

async def delete_key_redis(key):
    redis_client.delete(key)
