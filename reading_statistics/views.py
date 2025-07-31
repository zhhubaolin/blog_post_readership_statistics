from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.utils.timezone import localtime
from django.http import JsonResponse

from .models import Article
from utils.all_enum import ResponseStatus
from .serializers import ArticleSerializer, ArticleListSerializer, ReadingRecordRequestSerializer
from .services.reading_service import ReadingStatisticsService
from .services.exception_handler import ExceptionHandler


class ArticleViewSet(viewsets.ModelViewSet):
    '''文章视图'''
    queryset = Article.objects.filter(is_published=True)
    serializer_class = ArticleSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleSerializer

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        # 阅读统计由中间件处理
        return response

    def get_statistics(self, request, pk=None):
        reading_service = ReadingStatisticsService()
        result = reading_service.get_article_statistics(int(pk))

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'cache_hit': result['cache_hit'],
            'errors': result.get('errors', []),
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })


class ReadingStatisticsViewSet(viewsets.ViewSet):
    '''阅读统计视图'''
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        # 初始化服务
        super().__init__(**kwargs)
        self.reading_service = ReadingStatisticsService()
        self.exception_handler = ExceptionHandler()

    def record_reading(self, request):
        '''记录阅读'''
        serializer = ReadingRecordRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'status': ResponseStatus.ERROR.value,
                'message': serializer.errors,
                'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        if not data.get('ip_address'):
            data['ip_address'] = self._get_client_ip(request)
        if not data.get('user_agent'):
            data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]  # 限制长度
        if not data.get('session_key'):
            data['session_key'] = request.session.session_key or ''

        result = self.reading_service.record_reading(**data)

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'cache_hit': result['cache_hit'],
            'errors': result.get('errors', []),
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def get_article_stats(self, request, article_id=None):
        '''获取文章阅读统计'''
        result = self.reading_service.get_article_statistics(int(article_id))

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'cache_hit': result['cache_hit'],
            'errors': result.get('errors', []),
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def get_user_history(self, request, user_id=None):
        '''获取用户阅读历史'''
        limit = int(request.query_params.get('limit', 20))
        result = self.reading_service.get_user_reading_history(int(user_id), limit)

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'cache_hit': result['cache_hit'],
            'errors': result.get('errors', []),
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def get_popular_articles(self, request):
        '''获取热门文章'''
        limit = int(request.query_params.get('limit', 10))
        days = int(request.query_params.get('days', 7))

        result = self.reading_service.get_popular_articles(limit, days)

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'cache_hit': result['cache_hit'],
            'errors': result.get('errors', []),
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def get_cache_statistics(self, request):
        '''获取缓存统计信息'''
        result = self.reading_service.get_cache_statistics()

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'errors': result.get('errors', []),
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def get_system_overview(self, request):
        '''获取系统总览'''
        result = self.reading_service.get_system_overview()

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'errors': result.get('errors', [])
        })

    def sync_cache_to_database(self, request):
        '''将缓存同步到数据库'''
        result = self.reading_service.sync_cache_to_database()

        return Response({
            'status': ResponseStatus.SUCCESS.value if result['success'] else ResponseStatus.ERROR.value,
            'data': result['data'],
            'errors': result.get('errors', []),
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def get_error_statistics(self, request):
        '''获取错误统计信息'''
        error_stats = self.exception_handler.get_error_statistics()

        return Response({
            'status': ResponseStatus.SUCCESS.value,
            'data': error_stats,
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def reset_error_counters(self, request):
        """重置错误计数器"""
        self.exception_handler.reset_all_counters()

        return Response({
            'status': ResponseStatus.SUCCESS.value,
            'data': {'message': '错误计数器已重置'},
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        })

    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
            return ip

        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()

        return request.META.get('REMOTE_ADDR', '127.0.0.1')


class HealthCheckViewSet(viewsets.ViewSet):
    """健康检查视图集"""
    permission_classes = [AllowAny]

    def health_status(self, request):
        """系统健康状态检查"""
        reading_service = ReadingStatisticsService()

        # 检查缓存健康状态
        cache_healthy = reading_service.cache_service.health_check()

        # 检查数据库健康状态
        db_healthy = True

        # 数据库连接测试
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('SELECT 1')
        db_result = cursor.fetchone()
        db_healthy = db_result is not None

        overall_healthy = cache_healthy and db_healthy

        return Response({
            'status': ResponseStatus.SUCCESS.value,
            'data': {
                'overall_status': 'healthy' if overall_healthy else 'unhealthy',
                'cache_status': 'healthy' if cache_healthy else 'unhealthy',
                'database_status': 'healthy' if db_healthy else 'unhealthy',
                'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
            }
        })


def reading_stats_dashboard(request):
    """阅读统计"""
    reading_service = ReadingStatisticsService()

    # 获取系统概览数据
    overview_result = reading_service.get_system_overview()
    overview_data = overview_result.get('data', {}) if overview_result['success'] else {}

    # 获取热门文章
    popular_result = reading_service.get_popular_articles(10, 7)
    popular_articles = popular_result.get('data', []) if popular_result['success'] else []

    # 获取缓存统计
    cache_result = reading_service.get_cache_statistics()
    cache_data = cache_result.get('data', {}) if cache_result['success'] else {}

    return JsonResponse({
        'status': ResponseStatus.SUCCESS.value,
        'data': {
            'overview': overview_data,
            'popular_articles': popular_articles,
            'cache_statistics': cache_data,
            'timestamp': localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        }
    })
