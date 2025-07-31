# 博客文章阅读量统计系统

### 环境要求
- Python 3.9.12
- Django 4.2.10
- MySQL 8.0
- Redis 3.0.5

1. **配置数据库**
编辑 `local_settings.py`，配置MySQL和Redis连接信息：
```python
# MySQL配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'database_name',
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

# Redis配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

2. **数据库迁移**
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **创建超级用户**
```bash
python manage.py createsuperuser
```

4. **启动服务**
```bash
python manage.py runserver
```


### 缓存配置
```python
# 缓存键前缀
READING_STATS_CACHE_PREFIX = 'reading_stats'

# 缓存超时时间（秒）
READING_STATS_CACHE_TIMEOUT = 3600  # 1小时

# 批量更新配置
READING_STATS_BATCH_SIZE = 100
READING_STATS_BATCH_TIMEOUT = 300  # 5分钟
```

### 异常处理配置
```python
# 错误重试配置
READING_STATS_MAX_RETRIES = 3
READING_STATS_RETRY_DELAY = 1  # 秒

# 熔断器配置
READING_STATS_CIRCUIT_BREAKER_THRESHOLD = 5
READING_STATS_CIRCUIT_BREAKER_TIMEOUT = 60  # 秒
```
