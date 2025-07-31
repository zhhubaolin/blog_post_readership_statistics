from django.urls import path
from . import views

list_only = {'get': 'list'}
list_and_create = {'get': 'list', 'post': 'create'}
get_and_update = {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}
get_and_update_delete = {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}
get_only = {'get': 'retrieve'}
post_only = {'post': 'create'}

urlpatterns = [
    # --------------------------------------------文章相关----------------------------------------------------
    path('articles/', views.ArticleViewSet.as_view(list_and_create), name='文章列表'),
    path('articles/<int:pk>/', views.ArticleViewSet.as_view(get_and_update), name='文章详情'),
    path('articles/<int:pk>/statistics/', views.ArticleViewSet.as_view({'get': 'get_statistics'}), name='文章统计'),

    # ---------------------------------------------阅读统计----------------------------------------------------
    path('reading_stats/record/', views.ReadingStatisticsViewSet.as_view({'post': 'record_reading'}), name='记录阅读'),
    path('reading_stats/articles/<int:article_id>/',
         views.ReadingStatisticsViewSet.as_view({'get': 'get_article_stats'}), name='文章统计信息'),
    path('reading_stats/users/<int:user_id>/history/',
         views.ReadingStatisticsViewSet.as_view({'get': 'get_user_history'}), name='用户阅读历史'),
    path('reading_stats/popular_articles/', views.ReadingStatisticsViewSet.as_view({'get': 'get_popular_articles'}),
         name='热门文章'),
    path('reading_stats/cache_statistics/', views.ReadingStatisticsViewSet.as_view({'get': 'get_cache_statistics'}),
         name='缓存统计'),
    path('reading_stats/system_overview/', views.ReadingStatisticsViewSet.as_view({'get': 'get_system_overview'}),
         name='系统概览'),
    path('reading_stats/sync_cache/', views.ReadingStatisticsViewSet.as_view({'post': 'sync_cache_to_database'}),
         name='缓存同步'),
    path('reading_stats/error_statistics/', views.ReadingStatisticsViewSet.as_view({'get': 'get_error_statistics'}),
         name='错误统计'),
    path('reading_stats/reset_errors/', views.ReadingStatisticsViewSet.as_view({'post': 'reset_error_counters'}),
         name='重置错误计数'),

    # ---------------------------------------------健康检查----------------------------------------------------
    path('health/status/', views.HealthCheckViewSet.as_view({'get': 'health_status'}), name='健康检查'),

    # ---------------------------------------------阅读统计----------------------------------------------------
    path('dashboard/', views.reading_stats_dashboard, name='阅读统计'),
]
