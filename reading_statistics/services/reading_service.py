from time import localtime
from django.utils import timezone
from django.contrib.auth.models import User
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib

from .cache_service import CacheService
from .database_service import DatabaseService
from .exception_handler import ExceptionHandler
from ..models import Article
from django.utils.timezone import localtime


class ReadingStatisticsService:

    # 初始化服务
    def __init__(self):
        self.cache_service = CacheService()
        self.db_service = DatabaseService()
        self.exception_handler = ExceptionHandler()

    # 记录阅读
    def record_reading(self, article_id: int, user_id: Optional[int] = None,
                       ip_address: str = None, user_agent: str = None,
                       session_key: str = None) -> Dict[str, Any]:
        result = {
            'success': False,
            'data': {},
            'cache_hit': False,
            'errors': []
        }

        unique_key = self._generate_unique_key(article_id, user_id, ip_address, session_key)

        if self._is_duplicate_reading(unique_key):
            result['success'] = True
            result['data'] = {'message': '重复访问，未计入统计'}
            return result

        cache_success = self._update_cache_statistics(
            article_id, user_id, ip_address, session_key
        )

        if cache_success:
            # 如果缓存更新成功，则直接返回结果
            result['cache_hit'] = True

            self._queue_database_update({
                'type': 'reading_record',
                'data': {
                    'article_id': article_id,
                    'user_id': user_id,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'session_key': session_key,
                }
            })

            result['success'] = True
            result['data'] = self._get_reading_statistics(article_id)
        else:
            db_success = self._update_database_statistics(
                article_id, user_id, ip_address, user_agent, session_key
            )

            if db_success:
                result['success'] = True
                result['data'] = self._get_reading_statistics_from_db(article_id)
            else:
                result['errors'].append('统计记录失败')

        self._mark_reading_recorded(unique_key)
        return result

    def get_article_statistics(self, article_id: int) -> Dict[str, Any]:
        # 从缓存中获取文章统计数据
        result = {
            'success': False,
            'data': {},
            'cache_hit': False,
            'errors': []
        }

        cached_data = self.cache_service.get_article_views(article_id)

        if cached_data:
            self.cache_service.record_cache_hit('article_stats', True)
            result['cache_hit'] = True
            result['success'] = True
            result['data'] = cached_data
        else:
            self.cache_service.record_cache_hit('article_stats', False)

            db_data = self.db_service.get_article_reading_summary(article_id)

            if db_data:
                self.cache_service.set_article_views(article_id, db_data)
                result['success'] = True
                result['data'] = db_data
            else:
                result['errors'].append('文章统计数据不存在')

        return result

    def get_user_reading_history(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        # 从缓存中获取用户阅读历史
        result = {
            'success': False,
            'data': [],
            'cache_hit': False,
            'errors': []
        }

        cache_key = f"user_history:{user_id}:{limit}"
        cached_data = self.cache_service.cache.get(cache_key)

        if cached_data:
            self.cache_service.record_cache_hit('user_history', True)
            result['cache_hit'] = True
            result['success'] = True
            result['data'] = cached_data
        else:
            self.cache_service.record_cache_hit('user_history', False)

            db_data = self.db_service.get_user_reading_history(user_id, limit)

            self.cache_service.cache.set(cache_key, db_data, 300)

            result['success'] = True
            result['data'] = db_data

        return result

    def get_popular_articles(self, limit: int = 10, days: int = 7) -> Dict[str, Any]:
        # 从缓存中获取热门文章
        result = {
            'success': False,
            'data': [],
            'cache_hit': False,
            'errors': []
        }

        cache_key = f"popular_articles:{limit}:{days}"
        cached_data = self.cache_service.cache.get(cache_key)

        if cached_data:
            self.cache_service.record_cache_hit('popular_articles', True)
            result['cache_hit'] = True
            result['success'] = True
            result['data'] = cached_data
        else:
            self.cache_service.record_cache_hit('popular_articles', False)

            db_data = self.db_service.get_popular_articles(limit, days)

            self.cache_service.cache.set(cache_key, db_data, 600)

            result['success'] = True
            result['data'] = db_data

        return result

    def get_cache_statistics(self) -> Dict[str, Any]:
        # 从缓存中获取缓存统计数据
        result = {
            'success': False,
            'data': {},
            'errors': []
        }

        cache_info = self.cache_service.get_cache_info()
        cache_hit_stats = self.db_service.get_cache_hit_statistics()

        result['success'] = True
        result['data'] = {
            'redis_info': cache_info,
            'hit_statistics': cache_hit_stats,
            'health_status': self.cache_service.health_check()
        }

        return result

    def get_system_overview(self) -> Dict[str, Any]:
        """系统总览"""
        result = {
            'success': False,
            'data': {},
            'errors': []
        }

        system_stats = self.db_service.get_system_statistics()  # 获取系统统计数据
        cache_stats = self.get_cache_statistics()  # 获取缓存统计数据

        result['success'] = True
        result['data'] = {
            'system_statistics': system_stats,
            'cache_statistics': cache_stats['data'] if cache_stats['success'] else {},
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        }

        return result

    def sync_cache_to_database(self) -> Dict[str, Any]:
        """同步缓存数据到数据库"""
        result = {
            'success': False,
            'data': {},
            'errors': []
        }

        # 获取待更新的数据
        pending_updates = self.cache_service.get_pending_updates()

        if pending_updates:
            # 批量更新数据库
            update_results = self.db_service.batch_update_statistics(pending_updates)

            result['success'] = True
            result['data'] = {
                'processed_updates': len(pending_updates),
                'results': update_results
            }
        else:
            result['success'] = True
            result['data'] = {'message': '没有待同步的数据'}

        return result

    def _generate_unique_key(self, article_id: int, user_id: Optional[int],
                             ip_address: str, session_key: str) -> str:
        """生成唯一键"""
        identifier = f"{article_id}:{user_id or 'anonymous'}:{ip_address}:{session_key}"
        return hashlib.md5(identifier.encode()).hexdigest()

    def _is_duplicate_reading(self, unique_key: str, window_seconds: int = 300) -> bool:
        """300s内检查是否重复阅读"""
        cache_key = f"reading_lock:{unique_key}"
        return self.cache_service.cache.get(cache_key) is not None

    def _mark_reading_recorded(self, unique_key: str, window_seconds: int = 300) -> None:
        """标记阅读记录已记录"""
        cache_key = f"reading_lock:{unique_key}"
        self.cache_service.cache.set(cache_key, True, window_seconds)

    def _update_cache_statistics(self, article_id: int, user_id: Optional[int],
                                 ip_address: str, session_key: str) -> bool:
        """更新缓存统计"""
        # 增加文章总阅读量
        self.cache_service.increment_article_views(article_id)

        # 如果是注册用户，更新用户阅读统计
        if user_id:
            self.cache_service.increment_user_reads(user_id, article_id)

        return True

    def _update_database_statistics(self, article_id: int, user_id: Optional[int],
                                    ip_address: str, user_agent: str, session_key: str) -> bool:
        """更新数据库统计"""
        # 创建阅读记录
        self.db_service.create_reading_record(
            article_id, user_id, ip_address, user_agent, session_key
        )

        # 更新文章统计
        if user_id:
            self.db_service.increment_article_statistics(
                article_id, total_views=1, registered_user_views=1
            )
            self.db_service.update_user_reading_statistics(user_id, article_id)
        else:
            self.db_service.increment_article_statistics(
                article_id, total_views=1, anonymous_views=1
            )

        return True

    def _queue_database_update(self, update_data: Dict[str, Any]) -> None:
        """添加数据库更新到队列"""
        self.cache_service.add_pending_update(update_data)

    def _get_reading_statistics(self, article_id: int) -> Dict[str, Any]:
        """从缓存获取阅读统计"""
        cached_data = self.cache_service.get_article_views(article_id)
        if cached_data:
            return cached_data

        # if缓存没有，从数据库获取并缓存
        db_data = self.db_service.get_article_reading_summary(article_id)
        if db_data:
            self.cache_service.set_article_views(article_id, db_data)

        return db_data or {}

    def _get_reading_statistics_from_db(self, article_id: int) -> Dict[str, Any]:
        """从数据库获取阅读统计"""
        return self.db_service.get_article_reading_summary(article_id) or {}
