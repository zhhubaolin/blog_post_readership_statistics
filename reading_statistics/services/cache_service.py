from django.core.cache import cache
from django.conf import settings
from datetime import datetime
import redis
import json
from typing import Optional, Dict, Any, List


class CacheService:
    def __init__(self):
        # 初始化缓存
        self.cache = cache
        self.config = getattr(settings, 'READING_STATS_CONFIG', {})
        self.cache_prefix = self.config.get('CACHE_PREFIX', {})
        self.cache_timeout = self.config.get('CACHE_TIMEOUT', {})

        redis_config = getattr(settings, 'REDIS_CONFIG', {})
        self.redis_client = redis.Redis(
            host=redis_config.get('HOST', 'localhost'),
            port=redis_config.get('PORT', 6379),
            db=redis_config.get('DB', 0),
            password=redis_config.get('PASSWORD', None),
            decode_responses=redis_config.get('DECODE_RESPONSES', True)  # 返回字符串
        )

    def _get_cache_key(self, key_type: str, identifier: str) -> str:
        # 生成缓存键
        prefix = self.cache_prefix.get(key_type, key_type)
        return f"{prefix}:{identifier}"

    def _get_timeout(self, key_type: str) -> int:
        #  获取超时时间
        return self.cache_timeout.get(key_type, 300)

    # 文章阅读量
    def get_article_views(self, article_id: int) -> Optional[Dict[str, Any]]:
        cache_key = self._get_cache_key('ARTICLE_VIEWS', str(article_id))
        return self.cache.get(cache_key)

    # 用户阅读统计
    def set_article_views(self, article_id: int, data: Dict[str, Any]) -> bool:
        cache_key = self._get_cache_key('ARTICLE_VIEWS', str(article_id))
        timeout = self._get_timeout('ARTICLE_VIEWS')
        return self.cache.set(cache_key, data, timeout)

    # 增加文章阅读量
    def increment_article_views(self, article_id: int, increment: int = 1) -> int:
        cache_key = self._get_cache_key('ARTICLE_VIEWS', f"{article_id}:count")

        pipeline = self.redis_client.pipeline()  # 创建Redis管道
        pipeline.incr(cache_key, increment)  # 增加阅读量
        pipeline.expire(cache_key, self._get_timeout('ARTICLE_VIEWS'))  # 设置过期时间
        results = pipeline.execute()  # 执行管道命令

        return results[0] if results else increment

    def get_user_reading_stats(self, user_id: int, article_id: int) -> Optional[Dict[str, Any]]:
        cache_key = self._get_cache_key('USER_READS', f"{user_id}:{article_id}")
        return self.cache.get(cache_key)

    def set_user_reading_stats(self, user_id: int, article_id: int, data: Dict[str, Any]) -> bool:
        # 用户阅读统计缓存
        cache_key = self._get_cache_key('USER_READS', f"{user_id}:{article_id}")
        timeout = self._get_timeout('USER_READS')
        return self.cache.set(cache_key, data, timeout)

    def increment_user_reads(self, user_id: int, article_id: int) -> int:
        cache_key = self._get_cache_key('USER_READS', f"{user_id}:{article_id}:count")

        pipeline = self.redis_client.pipeline()
        pipeline.incr(cache_key, 1)
        pipeline.expire(cache_key, self._get_timeout('USER_READS'))
        results = pipeline.execute()

        return results[0] if results else 1

    # 总阅读统计
    def get_total_reading_stats(self) -> Optional[Dict[str, Any]]:
        cache_key = self._get_cache_key('TOTAL_READS', 'global')
        return self.cache.get(cache_key)

    def set_total_reading_stats(self, data: Dict[str, Any]) -> bool:
        # 总阅读统计缓存
        cache_key = self._get_cache_key('TOTAL_READS', 'global')
        timeout = self._get_timeout('TOTAL_READS')
        result = self.cache.set(cache_key, data, timeout)
        return result if result is not None else False

    def get_cache_hit_stats(self, date: str = None) -> Optional[Dict[str, Any]]:
        """获取缓存命中率统计"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        cache_key = self._get_cache_key('CACHE_HITS', date)
        return self.cache.get(cache_key)

    def record_cache_hit(self, cache_type: str, hit: bool = True) -> None:
        """记录缓存命中情况"""
        date = datetime.now().strftime('%Y-%m-%d')
        cache_key = self._get_cache_key('CACHE_HITS', f"{date}:{cache_type}")

        # 缓存命中统计
        pipeline = self.redis_client.pipeline()
        pipeline.hincrby(cache_key, 'total_requests', 1)
        if hit:
            pipeline.hincrby(cache_key, 'cache_hits', 1)
        else:
            pipeline.hincrby(cache_key, 'cache_misses', 1)
        pipeline.expire(cache_key, 86400 * 7)  # 保存7天
        pipeline.execute()

    def get_pending_updates(self) -> List[Dict[str, Any]]:
        """获取即将更新到数据库的数据"""
        cache_key = self._get_cache_key('PENDING_UPDATES', 'queue')

        # 获取所有待更新的数据
        pending_data = []
        while True:
            data = self.redis_client.lpop(cache_key)
            if not data:
                break
            pending_data.append(json.loads(data))

        return pending_data

    def add_pending_update(self, update_data: Dict[str, Any]) -> None:
        """添加待更新数据到队列"""
        cache_key = self._get_cache_key('PENDING_UPDATES', 'queue')
        self.redis_client.rpush(cache_key, json.dumps(update_data))

    def clear_article_cache(self, article_id: int) -> None:
        """清除相关缓存"""
        patterns = [
            self._get_cache_key('ARTICLE_VIEWS', f"{article_id}*"),
            self._get_cache_key('USER_READS', f"*:{article_id}*"),
        ]

        for pattern in patterns:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        info = self.redis_client.info()
        return {
            'redis_version': info.get('redis_version'),  # Redis版本
            'used_memory': info.get('used_memory_human'),  # 已使用内存
            'connected_clients': info.get('connected_clients'),  # 连接的客户端数量
            'total_commands_processed': info.get('total_commands_processed'),  # 已处理的命令总数
            'keyspace_hits': info.get('keyspace_hits', 0),  # 缓存命中次数
            'keyspace_misses': info.get('keyspace_misses', 0),  # 缓存未命中次数
            'hit_rate': self._calculate_hit_rate(
                info.get('keyspace_hits', 0),
                info.get('keyspace_misses', 0)
            )
        }

    def _calculate_hit_rate(self, hits: int = None, misses: int = None) -> float:
        """计算缓存命中率"""
        if hits is None or misses is None:
            redis_info = self.redis_client.info()
            hits = redis_info.get('keyspace_hits', 0)
            misses = redis_info.get('keyspace_misses', 0)

        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def health_check(self) -> bool:
        """缓存健康检查"""
        test_key = 'health_check_test'
        test_value = 'ok'

        self.redis_client.set(test_key, test_value, ex=10)  # 设置过期时间
        result = self.redis_client.get(test_key)  # 获取值
        self.redis_client.delete(test_key)  # 删除键

        return result == test_value
