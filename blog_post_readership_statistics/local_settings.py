# 数据库配置 
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'blog_readership_db',
        'USER': 'root',
        'PASSWORD': '123.com',
        'HOST': 'localhost',
        'PORT': '3308',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# Redis配置
REDIS_CONFIG = {
    'HOST': 'localhost',
    'PORT': 6379,
    'DB': 0,
    'PASSWORD': None,  
    'DECODE_RESPONSES': True,  # 解码响应
    'CONNECTION_POOL_KWARGS': { 
        'max_connections': 50,    # 最大连接数
        'retry_on_timeout': True,      # 连接超时是否重试
    }
}

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',  # Redis缓存
        'LOCATION': f'redis://{REDIS_CONFIG["HOST"]}:{REDIS_CONFIG["PORT"]}/{REDIS_CONFIG["DB"]}',  # Redis连接地址
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': REDIS_CONFIG['CONNECTION_POOL_KWARGS'],
        },
        'KEY_PREFIX': 'blog_stats',
        'TIMEOUT': 300,  # 默认缓存5分钟
    }
}

# 阅读统计
READING_STATS_CONFIG = {
    # 缓存键前缀
    'CACHE_PREFIX': {
        'ARTICLE_VIEWS': 'article_views',  
        'USER_READS': 'user_reads',  
        'TOTAL_READS': 'total_reads',  
        'CACHE_HITS': 'cache_hits',
    },
    # 缓存过期时间
    'CACHE_TIMEOUT': {
        'ARTICLE_VIEWS': 3600,  # 1小时
        'USER_READS': 1800,     # 30分钟
        'TOTAL_READS': 600,     # 10分钟
        'STATS': 300,           # 5分钟
    },
    # 数据库更新
    'BATCH_UPDATE': {
        'SIZE': 100,            # 批量更新大小
        'INTERVAL': 60,         # 更新间隔（秒）
    },
    # 异常处理
    'ERROR_HANDLING': {
        'MAX_RETRIES': 3,
        'RETRY_DELAY': 1,       # 重试延迟（秒）
        'FALLBACK_TO_DB': True, # 缓存失败时是否回退到数据库
    }
}
