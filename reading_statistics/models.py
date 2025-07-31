from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Article(models.Model):
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='作者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_published = models.BooleanField(default=True, verbose_name='是否发布')
    
    class Meta:
        db_table = 'articles'
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class ReadingRecord(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='文章')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='用户')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.TextField(verbose_name='用户代理')
    read_time = models.DateTimeField(default=timezone.now, verbose_name='阅读时间')
    session_key = models.CharField(max_length=40, verbose_name='会话键')
    
    class Meta:
        db_table = 'reading_records'
        verbose_name = '阅读记录'
        verbose_name_plural = '阅读记录'
        ordering = ['-read_time']
        indexes = [
            models.Index(fields=['article', 'user']),
            models.Index(fields=['article', 'ip_address']),
            models.Index(fields=['read_time']),
        ]
    
    def __str__(self):
        return f'{self.article.title} - {self.user or self.ip_address}'


class ArticleStatistics(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, verbose_name='文章')
    total_views = models.PositiveIntegerField(default=0, verbose_name='总阅读次数')
    unique_visitors = models.PositiveIntegerField(default=0, verbose_name='独立访客数')
    registered_user_views = models.PositiveIntegerField(default=0, verbose_name='注册用户阅读次数')
    anonymous_views = models.PositiveIntegerField(default=0, verbose_name='匿名用户阅读次数')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='最后更新时间')
    
    class Meta:
        db_table = 'article_statistics'
        verbose_name = '文章统计'
        verbose_name_plural = '文章统计'
    
    def __str__(self):
        return f'{self.article.title} - 统计'


class UserReadingStatistics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='文章')
    read_count = models.PositiveIntegerField(default=0, verbose_name='阅读次数')
    first_read_time = models.DateTimeField(verbose_name='首次阅读时间')
    last_read_time = models.DateTimeField(verbose_name='最后阅读时间')
    
    class Meta:
        db_table = 'user_reading_statistics'
        verbose_name = '用户阅读统计'
        verbose_name_plural = '用户阅读统计'
        unique_together = ['user', 'article']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['article']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.article.title}'


class CacheHitStatistics(models.Model):
    date = models.DateField(verbose_name='日期')
    cache_type = models.CharField(max_length=50, verbose_name='缓存类型')
    total_requests = models.PositiveIntegerField(default=0, verbose_name='总请求数')
    cache_hits = models.PositiveIntegerField(default=0, verbose_name='缓存命中数')
    cache_misses = models.PositiveIntegerField(default=0, verbose_name='缓存未命中数')
    hit_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='命中率')
    
    class Meta:
        db_table = 'cache_hit_statistics'
        verbose_name = '缓存命中率统计'
        verbose_name_plural = '缓存命中率统计'
        unique_together = ['date', 'cache_type']
        ordering = ['-date']
    
    def __str__(self):
        return f'{self.date} - {self.cache_type} - {self.hit_rate}%'
