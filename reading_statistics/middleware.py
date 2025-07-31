from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
from django.urls import resolve
from django.contrib.auth.models import AnonymousUser
from .services.reading_service import ReadingStatisticsService
from .services.exception_handler import ExceptionHandler, ErrorType
import re


class ReadingStatsMiddleware(MiddlewareMixin):

    # 初始化中间件
    def __init__(self, get_response):
        super().__init__(get_response)
        self.reading_service = ReadingStatisticsService()
        self.exception_handler = ExceptionHandler()

        # 需要统计的URL
        self.article_url_patterns = [
            r'^/api/reading/articles/(?P<article_id>\d+)/$',
            r'^/api/reading/reading_stats/articles/(?P<article_id>\d+)/$',
        ]

    def process_request(self, request: HttpRequest) -> None:
        # 记录请求开始时间
        request._reading_stats_start_time = self._get_current_timestamp()

        # 检查是否是文章访问请求
        article_id = self._extract_article_id(request)
        if article_id:
            request._reading_stats_article_id = article_id

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        # 只有成功的GET请求才记录阅读统计
        if (request.method == 'GET' and
                response.status_code == 200 and
                hasattr(request, '_reading_stats_article_id')):
            self._record_reading_async(request)

        return response

    def _extract_article_id(self, request: HttpRequest) -> int:
        # 检查URL是否匹配
        path = request.path

        for pattern in self.article_url_patterns:
            match = re.match(pattern, path)
            if match:
                return int(match.group('article_id'))

        # 从URL参数中获取
        resolved = resolve(request.path)
        if resolved and 'article_id' in resolved.kwargs:
            return int(resolved.kwargs['article_id'])

        return None

    def _record_reading_async(self, request: HttpRequest) -> None:
        article_id = request._reading_stats_article_id

        # 获取用户信息
        user_id = None
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            user_id = request.user.id

        # 获取客户端信息
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # 限制长度
        session_key = request.session.session_key or ''

        # 记录阅读统计
        result = self.reading_service.record_reading(
            article_id=article_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key
        )

        if not result:
            self.exception_handler.handle_exception(
                None, ErrorType.BUSINESS_ERROR, {
                    'middleware': 'ReadingStatsMiddleware',
                    'article_id': article_id,
                    'user_id': user_id,
                    'ip_address': ip_address
                }
            )

    def _get_client_ip(self, request: HttpRequest) -> str:
        # 尝试从X-Forwarded-For头获取真实IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
            return ip

        # 尝试从X-Real-IP头获取真实IP
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()

        # 默认使用REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    def _get_current_timestamp(self) -> float:
        import time
        return time.time()

    def _is_bot_request(self, request: HttpRequest) -> bool:
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

        # 常见的爬虫User-Agent关键词
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper',
            'googlebot', 'bingbot', 'slurp', 'duckduckbot',
            'baiduspider', 'yandexbot', 'facebookexternalhit'
        ]

        return any(pattern in user_agent for pattern in bot_patterns)

    def _should_skip_tracking(self, request: HttpRequest) -> bool:
        # 跳过爬虫请求
        if self._is_bot_request(request):
            return True

        # 跳过管理员页面请求
        if request.path.startswith('/admin/'):
            return True

        # 跳过静态文件请求
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return True

        # 跳过API文档请求
        if request.path.startswith('/docs/') or request.path.startswith('/swagger/'):
            return True

        return False
