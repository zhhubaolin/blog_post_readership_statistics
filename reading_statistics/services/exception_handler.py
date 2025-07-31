from enum import Enum
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from django.conf import settings
import time


class ErrorLevel(Enum):
    """错误级别"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class ErrorType(Enum):
    """错误类型"""
    CACHE_ERROR = 'cache_error'  # 缓存错误
    DATABASE_ERROR = 'database_error'  # 数据库错误
    NETWORK_ERROR = 'network_error'  # 网络错误
    VALIDATION_ERROR = 'validation_error'  # 验证错误
    BUSINESS_ERROR = 'business_error'  # 业务错误
    SYSTEM_ERROR = 'system_error'  # 系统错误


class ExceptionHandler:

    def __init__(self):
        # 获取配置文件中的错误处理配置
        self.config = getattr(settings, 'READING_STATS_CONFIG', {}).get('ERROR_HANDLING', {})
        # 获取最大重试次数
        self.max_retries = self.config.get('MAX_RETRIES', 3)
        # 获取重试延迟时间
        self.retry_delay = self.config.get('RETRY_DELAY', 1)
        # 获取是否回退到数据库的配置
        self.fallback_to_db = self.config.get('FALLBACK_TO_DB', True)

        self.error_counters = {}  # 错误计数器
        self.circuit_breakers = {}  # 熔断器

    def handle_exception(self, exception: Exception, error_type: ErrorType,
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        error_level = self._classify_error(exception, error_type)
        error_info = {
            'exception': exception,
            'error_type': error_type,
            'error_level': error_level,
            'context': context or {},
            'timestamp': datetime.now(),
        }

        # 记录错误
        self._record_error(error_info)

        # 根据错误级别选择处理策略
        if error_level == ErrorLevel.CRITICAL:
            return self._handle_critical_error(error_info)
        elif error_level == ErrorLevel.HIGH:
            return self._handle_high_error(error_info)
        elif error_level == ErrorLevel.MEDIUM:
            return self._handle_medium_error(error_info)
        else:
            return self._handle_low_error(error_info)

    def with_retry(self, func: Callable, *args, max_retries: int = None,
                   retry_delay: float = None, **kwargs) -> Any:
        max_retries = max_retries or self.max_retries  # 最大重试次数
        retry_delay = retry_delay or self.retry_delay  # 重试延迟时间

        last_exception = None

        for attempt in range(max_retries + 1):
            if self._is_circuit_open(func.__name__):
                return None

            attempt_start = time.time()

            result = func(*args, **kwargs)

            if result is not None:
                self._reset_error_count(func.__name__)
                return result

            self._increment_error_count(func.__name__)

            if attempt == max_retries:
                break

            time.sleep(retry_delay * (2 ** attempt))

        return None

    def with_fallback(self, primary_func: Callable, fallback_func: Callable,
                      *args, **kwargs) -> Any:
        result = self.with_retry(primary_func, *args, **kwargs)
        if result is None and fallback_func:
            return fallback_func(*args, **kwargs)
        return result

    def cache_fallback_to_db(self, cache_func: Callable, db_func: Callable,
                             *args, **kwargs) -> Any:
        if not self.fallback_to_db:
            return cache_func(*args, **kwargs)

        result = cache_func(*args, **kwargs)
        if result is None:
            return db_func(*args, **kwargs)
        return result

    def _classify_error(self, exception: Exception, error_type: ErrorType) -> ErrorLevel:
        # 根据异常类型和错误类型进行分级
        if error_type == ErrorType.CRITICAL or isinstance(exception, (SystemExit, KeyboardInterrupt)):
            return ErrorLevel.CRITICAL

        if error_type == ErrorType.DATABASE_ERROR:
            # 数据库连接错误---高级
            if 'connection' in str(exception).lower():
                return ErrorLevel.HIGH
            # 其他---中级
            return ErrorLevel.MEDIUM

        if error_type == ErrorType.CACHE_ERROR:
            # 缓存错误--中级
            return ErrorLevel.MEDIUM

        if error_type == ErrorType.NETWORK_ERROR:
            # 网络-中级
            return ErrorLevel.MEDIUM

        if error_type == ErrorType.VALIDATION_ERROR:
            # 验证--低级
            return ErrorLevel.LOW

        return ErrorLevel.MEDIUM

    def _handle_critical_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        # 严重错误
        return {
            'success': False,
            'error_level': ErrorLevel.CRITICAL,
            'message': '系统遇到严重错误，服务已停止',
            'should_retry': False,  # 不重试
            'fallback_available': False,  # 不回退
        }

    def _handle_high_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        # 高级错误
        return {
            'success': False,
            'error_level': ErrorLevel.HIGH,
            'message': '核心功能暂时不可用，正在尝试恢复',
            'should_retry': True,
            'fallback_available': True,
            'degraded_mode': True,  # 降级
        }

    def _handle_medium_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        # 中级错误
        return {
            'success': False,
            'error_level': ErrorLevel.MEDIUM,
            'message': '部分功能暂时不可用，正在尝试恢复',
            'should_retry': True,
            'fallback_available': True,
        }

    def _handle_low_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        # 低级错误
        return {
            'success': False,
            'error_level': ErrorLevel.LOW,
            'message': '低级错误，已记录',
            'should_retry': True,
            'fallback_available': False,
        }

    def _record_error(self, error_info: Dict[str, Any]) -> None:
        # 日志、监控
        error_key = f"{error_info['error_type'].value}_{error_info['error_level'].value}"

        if error_key not in self.error_counters:
            self.error_counters[error_key] = {
                'count': 0,
                'last_occurrence': None,
                'first_occurrence': None,
            }

        self.error_counters[error_key]['count'] += 1
        self.error_counters[error_key]['last_occurrence'] = error_info['timestamp']

        if not self.error_counters[error_key]['first_occurrence']:
            self.error_counters[error_key]['first_occurrence'] = error_info['timestamp']

    def _increment_error_count(self, function_name: str) -> None:
        '''增加错误计数'''
        if function_name not in self.error_counters:
            self.error_counters[function_name] = {
                'count': 0,
                'last_error': None,
                'circuit_open_until': None,
            }

        self.error_counters[function_name]['count'] += 1
        self.error_counters[function_name]['last_error'] = datetime.now()

        # 如果错误次数超过阈值，打开熔断器
        if self.error_counters[function_name]['count'] >= 5:
            self._open_circuit_breaker(function_name)

    def _reset_error_count(self, function_name: str) -> None:
        '''重置错误计数'''
        if function_name in self.error_counters:
            self.error_counters[function_name]['count'] = 0
            self.error_counters[function_name]['circuit_open_until'] = None

    def _open_circuit_breaker(self, function_name: str, duration_minutes: int = 5) -> None:
        '''打开熔断器'''
        open_until = datetime.now() + timedelta(minutes=duration_minutes)
        self.error_counters[function_name]['circuit_open_until'] = open_until

    def _is_circuit_open(self, function_name: str) -> bool:
        '''熔断器是否打开'''
        if function_name not in self.error_counters:
            return False

        circuit_open_until = self.error_counters[function_name].get('circuit_open_until')
        if not circuit_open_until:
            return False

        if datetime.now() > circuit_open_until:
            # 熔断器超时，自动关闭
            self.error_counters[function_name]['circuit_open_until'] = None
            return False

        return True

    def get_error_statistics(self) -> Dict[str, Any]:
        '''错误统计'''
        return {
            'error_counters': self.error_counters,
            'circuit_breakers_status': {
                func_name: self._is_circuit_open(func_name)
                for func_name in self.error_counters.keys()
            },
            'total_errors': sum(
                counter.get('count', 0)
                for counter in self.error_counters.values()
            ),
        }

    def reset_all_counters(self) -> None:
        self.error_counters.clear()  # 重置计数器
        self.circuit_breakers.clear()  # 重置熔断器状态


class CircuitBreakerOpenException(Exception):
    pass


class DegradedModeException(Exception):
    pass
