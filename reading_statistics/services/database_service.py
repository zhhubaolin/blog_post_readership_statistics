from django.db import transaction, models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from ..models import (
    Article, ReadingRecord, ArticleStatistics,
    UserReadingStatistics, CacheHitStatistics
)


class DatabaseService:

    # 创建阅读记录
    def create_reading_record(self, article_id: int, user_id: Optional[int],
                              ip_address: str, user_agent: str, session_key: str) -> ReadingRecord:
        article = Article.objects.get(id=article_id)
        user = User.objects.get(id=user_id) if user_id else None

        record = ReadingRecord.objects.create(
            article=article,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            read_time=timezone.now()
        )
        return record

    def get_article_statistics(self, article_id: int) -> Optional[ArticleStatistics]:
        '''获取文章统计信息'''
        return ArticleStatistics.objects.filter(article_id=article_id).first()

    def update_article_statistics(self, article_id: int, **kwargs) -> ArticleStatistics:
        '''更新文章统计信息'''
        stats, created = ArticleStatistics.objects.get_or_create(
            article_id=article_id,
            defaults=kwargs
        )

        if not created:
            for key, value in kwargs.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            stats.save()

        return stats

    def increment_article_statistics(self, article_id: int,
                                     total_views: int = 0,
                                     unique_visitors: int = 0,
                                     registered_user_views: int = 0,
                                     anonymous_views: int = 0) -> ArticleStatistics:
        '''增加文章统计信息'''
        stats, created = ArticleStatistics.objects.get_or_create(
            article_id=article_id,
            defaults={
                'total_views': total_views,  # 总访问量
                'unique_visitors': unique_visitors,  # 独立访客数
                'registered_user_views': registered_user_views,  # 注册用户访问量
                'anonymous_views': anonymous_views,  # 匿名用户访问量
            }
        )

        if not created:
            stats.total_views += total_views
            stats.unique_visitors += unique_visitors
            stats.registered_user_views += registered_user_views
            stats.anonymous_views += anonymous_views
            stats.save()

        return stats

    def get_user_reading_statistics(self, user_id: int, article_id: int) -> Optional[UserReadingStatistics]:
        '''用户文章阅读统计'''
        return UserReadingStatistics.objects.filter(
            user_id=user_id,
            article_id=article_id
        ).first()

    def update_user_reading_statistics(self, user_id: int, article_id: int,
                                       read_count: int = 1) -> UserReadingStatistics:
        now = timezone.now()
        stats, created = UserReadingStatistics.objects.get_or_create(
            user_id=user_id,
            article_id=article_id,
            defaults={
                'read_count': read_count,
                'first_read_time': now,
                'last_read_time': now,
            }
        )

        if not created:
            stats.read_count += read_count
            stats.last_read_time = now
            stats.save()

        return stats

    def get_article_reading_summary(self, article_id: int) -> Dict[str, Any]:
        '''文章阅读摘要'''
        article = Article.objects.get(id=article_id)
        stats = self.get_article_statistics(article_id)

        recent_records = ReadingRecord.objects.filter(
            article_id=article_id
        ).order_by('-read_time')[:10]

        user_stats = UserReadingStatistics.objects.filter(
            article_id=article_id
        ).order_by('-read_count')[:10]

        return {
            'article': {
                'id': article.id,
                'title': article.title,
                'author': article.author.username,
                'created_at': article.created_at,
            },
            'statistics': {
                'total_views': stats.total_views if stats else 0,  # 总访问量
                'unique_visitors': stats.unique_visitors if stats else 0,  # 独立访客数
                'registered_user_views': stats.registered_user_views if stats else 0,  # 注册用户访问量
                'anonymous_views': stats.anonymous_views if stats else 0,  # 匿名用户访问量
                'last_updated': stats.last_updated if stats else None,  # 最后更新时间
            },
            'recent_records': [
                {
                    'user': record.user.username if record.user else None,
                    'ip_address': record.ip_address,
                    'read_time': record.read_time,
                }
                for record in recent_records
            ],
            'top_readers': [
                {
                    'user': stat.user.username,
                    'read_count': stat.read_count,
                    'first_read_time': stat.first_read_time,
                    'last_read_time': stat.last_read_time,
                }
                for stat in user_stats
            ]
        }

    def get_user_reading_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        user_stats = UserReadingStatistics.objects.filter(
            user_id=user_id
        ).select_related('article').order_by('-last_read_time')[:limit]

        return [
            {
                'article_id': stat.article.id,  # 文章ID
                'article_title': stat.article.title,  # 文章标题
                'read_count': stat.read_count,  # 阅读次数
                'first_read_time': stat.first_read_time,  # 首次阅读时间
                'last_read_time': stat.last_read_time,  # 最后阅读时间
            }
            for stat in user_stats
        ]

    def get_popular_articles(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        '''获取热门文章'''
        since_date = timezone.now() - timedelta(days=days)

        popular_articles = Article.objects.filter(
            readingrecord__read_time__gte=since_date,
            is_published=True
        ).distinct().annotate(
            recent_views=models.Count('readingrecord')
        ).order_by('-recent_views')[:limit]

        result = []
        for article in popular_articles:
            stats = self.get_article_statistics(article.id)
            result.append({
                'id': article.id,
                'title': article.title,
                'author': article.author.username,
                'created_at': article.created_at,
                'total_views': stats.total_views if stats else 0,  # 总访问量
                'unique_visitors': stats.unique_visitors if stats else 0,  # 独立访客数
            })

        return result

    def update_cache_hit_statistics(self, date: str, cache_type: str,
                                    total_requests: int, cache_hits: int,
                                    cache_misses: int) -> CacheHitStatistics:
        hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0

        stats, created = CacheHitStatistics.objects.get_or_create(
            date=date,
            cache_type=cache_type,
            defaults={
                'total_requests': total_requests,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'hit_rate': round(hit_rate, 2),
            }
        )

        if not created:
            stats.total_requests += total_requests
            stats.cache_hits += cache_hits
            stats.cache_misses += cache_misses
            stats.hit_rate = round(
                (stats.cache_hits / stats.total_requests * 100) if stats.total_requests > 0 else 0,
                2
            )
            stats.save()

        return stats

    def get_cache_hit_statistics(self, days: int = 7) -> List[Dict[str, Any]]:
        since_date = timezone.now().date() - timedelta(days=days)

        stats = CacheHitStatistics.objects.filter(
            date__gte=since_date
        ).order_by('-date', 'cache_type')

        return [
            {
                'date': stat.date,
                'cache_type': stat.cache_type,  # 缓存类型
                'total_requests': stat.total_requests,
                'cache_hits': stat.cache_hits,
                'cache_misses': stat.cache_misses,
                'hit_rate': float(stat.hit_rate),
            }
            for stat in stats
        ]

    @transaction.atomic
    def batch_update_statistics(self, updates: List[Dict[str, Any]]) -> Dict[str, int]:
        results = {
            'article_stats_updated': 0,  # 更新文章统计
            'user_stats_updated': 0,  # 更新用户统计
            'records_created': 0,  # 创建阅读记录
            'cache_stats_updated': 0,  # 更新缓存统计
        }

        for update in updates:
            update_type = update.get('type')
            data = update.get('data', {})

            if update_type == 'article_stats':
                self.increment_article_statistics(**data)
                results['article_stats_updated'] += 1

            elif update_type == 'user_stats':
                self.update_user_reading_statistics(**data)
                results['user_stats_updated'] += 1

            elif update_type == 'reading_record':
                self.create_reading_record(**data)
                results['records_created'] += 1

            elif update_type == 'cache_stats':
                self.update_cache_hit_statistics(**data)
                results['cache_stats_updated'] += 1

        return results

    def cleanup_old_records(self, days: int = 90) -> int:
        '''清理旧的阅读记录'''
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = ReadingRecord.objects.filter(
            read_time__lt=cutoff_date
        ).delete()
        return deleted_count

    def get_system_statistics(self) -> Dict[str, Any]:
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        return {
            'total_articles': Article.objects.filter(is_published=True).count(),  # 总文章数
            'total_users': User.objects.count(),  # 总用户数
            'total_reading_records': ReadingRecord.objects.count(),  # 总阅读记录数
            'today_reads': ReadingRecord.objects.filter(
                read_time__date=today
            ).count(),  # 今日阅读量
            'week_reads': ReadingRecord.objects.filter(
                read_time__date__gte=week_ago
            ).count(),  # 周阅读量
            'month_reads': ReadingRecord.objects.filter(
                read_time__date__gte=month_ago
            ).count(),  # 月阅读量
            'active_users_today': ReadingRecord.objects.filter(
                read_time__date=today,
                user__isnull=False
            ).values('user').distinct().count(),  # 今日活跃用户数
            'active_users_week': ReadingRecord.objects.filter(
                read_time__date__gte=week_ago,
                user__isnull=False
            ).values('user').distinct().count(),  # 周活跃用户数
        }
