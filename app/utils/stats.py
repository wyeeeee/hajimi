import asyncio
from datetime import datetime, timedelta
from app.utils.logging import log
import app.config.settings as settings
from collections import defaultdict, Counter
import time
import threading
import queue


class ApiStatsManager:
    """API调用统计管理器，优化性能的新实现"""

    def __init__(self, enable_background=True, batch_interval=1.0):
        # 使用Counter记录API密钥和模型的调用次数
        self.api_key_counts = Counter()  # 记录每个API密钥的调用次数
        self.model_counts = Counter()  # 记录每个模型的调用次数
        self.api_model_counts = defaultdict(
            Counter
        )  # 记录每个API密钥对每个模型的调用次数

        # 记录token使用量
        self.api_key_tokens = Counter()  # 记录每个API密钥的token使用量
        self.model_tokens = Counter()  # 记录每个模型的token使用量
        self.api_model_tokens = defaultdict(
            Counter
        )  # 记录每个API密钥对每个模型的token使用量

        # 用于时间序列分析的数据结构（最近24小时，按分钟分组）
        self.time_buckets = {}  # 格式: {timestamp_minute: {"calls": count, "tokens": count}}

        # 保存与兼容格式相关的调用日志（最小化存储）
        self.recent_calls = []  # 仅保存最近的少量调用，用于前端展示
        self.max_recent_calls = 100  # 最大保存的最近调用记录数

        # 当前时间分钟桶的时间戳（分钟级别）
        self.current_minute = self._get_minute_timestamp(datetime.now())

        # 清理间隔（小时）
        self.cleanup_interval = 1
        self.last_cleanup = time.time()

        # 使用线程锁而不是asyncio锁
        self._counters_lock = threading.Lock()
        self._time_series_lock = threading.Lock()
        self._recent_calls_lock = threading.Lock()

        # 后台处理相关
        self.enable_background = enable_background
        self.batch_interval = batch_interval
        self._update_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()

        if enable_background:
            self._start_worker()

    def _start_worker(self):
        """启动后台工作线程"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop, daemon=True
            )
            self._worker_thread.start()

    def _worker_loop(self):
        """后台工作线程的主循环"""
        batch = []
        last_process = time.time()

        while not self._stop_event.is_set():
            try:
                # 非阻塞获取更新
                try:
                    update = self._update_queue.get_nowait()
                    batch.append(update)
                except queue.Empty:
                    pass

                # 处理批次或超时
                current_time = time.time()
                if batch and (current_time - last_process >= self.batch_interval):
                    self._process_batch(batch)
                    batch = []
                    last_process = current_time

                # 短暂休眠以避免CPU占用过高
                time.sleep(0.01)

            except Exception as e:
                log("error", f"后台处理线程错误: {str(e)}")
                time.sleep(1)  # 发生错误时短暂休眠

    def _process_batch(self, batch):
        """处理一批更新"""
        with self._counters_lock:
            for api_key, model, tokens in batch:
                self.api_key_counts[api_key] += 1
                self.model_counts[model] += 1
                self.api_model_counts[api_key][model] += 1
                self.api_key_tokens[api_key] += tokens
                self.model_tokens[model] += tokens
                self.api_model_tokens[api_key][model] += tokens

    async def update_stats(self, api_key, model, tokens=0):
        """更新API调用统计"""
        if self.enable_background:
            # 将更新放入队列
            self._update_queue.put((api_key, model, tokens))
        else:
            # 同步更新
            with self._counters_lock:
                self.api_key_counts[api_key] += 1
                self.model_counts[model] += 1
                self.api_model_counts[api_key][model] += 1
                self.api_key_tokens[api_key] += tokens
                self.model_tokens[model] += tokens
                self.api_model_tokens[api_key][model] += tokens

        # 更新时间序列数据
        now = datetime.now()
        minute_ts = self._get_minute_timestamp(now)

        with self._time_series_lock:
            if minute_ts not in self.time_buckets:
                self.time_buckets[minute_ts] = {"calls": 0, "tokens": 0}

            self.time_buckets[minute_ts]["calls"] += 1
            self.time_buckets[minute_ts]["tokens"] += tokens
            self.current_minute = minute_ts

        # 更新最近调用记录
        with self._recent_calls_lock:
            compact_call = {
                "api_key": api_key,
                "model": model,
                "timestamp": now,
                "tokens": tokens,
            }

            self.recent_calls.append(compact_call)
            if len(self.recent_calls) > self.max_recent_calls:
                self.recent_calls.pop(0)

        # 记录日志
        log_message = f"API调用已记录: 秘钥 '{api_key[:8]}', 模型 '{model}', 令牌: {tokens if tokens is not None else 0}"
        log("info", log_message)

    async def cleanup(self):
        """清理超过24小时的时间桶数据"""
        now = datetime.now()
        day_ago_ts = self._get_minute_timestamp(now - timedelta(days=1))

        with self._time_series_lock:
            # 直接删除旧的时间桶
            for ts in list(self.time_buckets.keys()):
                if ts < day_ago_ts:
                    del self.time_buckets[ts]

        self.last_cleanup = time.time()

    async def maybe_cleanup(self, force=False):
        """根据需要清理旧数据"""
        now = time.time()
        if force or (now - self.last_cleanup > self.cleanup_interval * 3600):
            await self.cleanup()
            self.last_cleanup = now

    async def get_api_key_usage(self, api_key, model=None):
        """获取API密钥的使用统计"""
        with self._counters_lock:
            if model:
                return self.api_model_counts[api_key][model]
            else:
                return self.api_key_counts[api_key]

    def get_calls_last_24h(self):
        """获取过去24小时的总调用次数"""
        with self._counters_lock:
            return sum(self.api_key_counts.values())

    def get_calls_last_hour(self, now=None):
        """获取过去一小时的总调用次数"""
        if now is None:
            now = datetime.now()

        hour_ago_ts = self._get_minute_timestamp(now - timedelta(hours=1))

        with self._time_series_lock:
            return sum(
                data["calls"]
                for ts, data in self.time_buckets.items()
                if ts >= hour_ago_ts
            )

    def get_calls_last_minute(self, now=None):
        """获取过去一分钟的总调用次数"""
        if now is None:
            now = datetime.now()

        minute_ago_ts = self._get_minute_timestamp(now - timedelta(minutes=1))

        with self._time_series_lock:
            return sum(
                data["calls"]
                for ts, data in self.time_buckets.items()
                if ts >= minute_ago_ts
            )

    def get_tokens_last_24h(self):
        """获取过去24小时的总Token消耗量"""
        with self._counters_lock:
            return sum(self.api_key_tokens.values())

    def get_tokens_last_hour(self, now=None):
        """获取过去一小时的总Token消耗量"""
        if now is None:
            now = datetime.now()
        
        hour_ago_ts = self._get_minute_timestamp(now - timedelta(hours=1))
        
        with self._time_series_lock:
            return sum(
                data["tokens"]
                for ts, data in self.time_buckets.items()
                if ts >= hour_ago_ts
            )

    def get_tokens_last_minute(self, now=None):
        """获取过去一分钟的总Token消耗量"""
        if now is None:
            now = datetime.now()
        
        minute_ago_ts = self._get_minute_timestamp(now - timedelta(minutes=1))
        
        with self._time_series_lock:
            return sum(
                data["tokens"]
                for ts, data in self.time_buckets.items()
                if ts >= minute_ago_ts
            )

    def get_time_series_data(self, minutes=30, now=None):
        """获取过去N分钟的时间序列数据"""
        if now is None:
            now = datetime.now()

        calls_series = []
        tokens_series = []

        with self._time_series_lock:
            for i in range(minutes, -1, -1):
                minute_dt = now - timedelta(minutes=i)
                minute_ts = self._get_minute_timestamp(minute_dt)

                bucket = self.time_buckets.get(minute_ts, {"calls": 0, "tokens": 0})

                calls_series.append(
                    {"time": minute_dt.strftime("%H:%M"), "value": bucket["calls"]}
                )

                tokens_series.append(
                    {"time": minute_dt.strftime("%H:%M"), "value": bucket["tokens"]}
                )

        return calls_series, tokens_series

    def get_api_key_stats(self, api_keys):
        """获取API密钥的详细统计信息"""
        stats = []

        with self._counters_lock:
            for api_key in api_keys:
                api_key_id = api_key[:8]
                calls_24h = self.api_key_counts[api_key]
                total_tokens = self.api_key_tokens[api_key]

                model_stats = {}
                for model, count in self.api_model_counts[api_key].items():
                    tokens = self.api_model_tokens[api_key][model]
                    model_stats[model] = {"calls": count, "tokens": tokens}

                usage_percent = (
                    (calls_24h / settings.API_KEY_DAILY_LIMIT) * 100
                    if settings.API_KEY_DAILY_LIMIT > 0
                    else 0
                )

                stats.append(
                    {
                        "api_key": api_key_id,
                        "calls_24h": calls_24h,
                        "total_tokens": total_tokens,
                        "limit": settings.API_KEY_DAILY_LIMIT,
                        "usage_percent": round(usage_percent, 2),
                        "model_stats": model_stats,
                    }
                )

        stats.sort(key=lambda x: x["usage_percent"], reverse=True)
        return stats

    async def reset(self):
        """重置所有统计数据"""
        with self._counters_lock:
            self.api_key_counts.clear()
            self.model_counts.clear()
            self.api_model_counts.clear()
            self.api_key_tokens.clear()
            self.model_tokens.clear()
            self.api_model_tokens.clear()

        with self._time_series_lock:
            self.time_buckets.clear()

        with self._recent_calls_lock:
            self.recent_calls.clear()

        self.current_minute = self._get_minute_timestamp(datetime.now())
        self.last_cleanup = time.time()

    def _get_minute_timestamp(self, dt):
        """将时间戳转换为分钟级别的时间戳（按分钟取整）"""
        return int(dt.timestamp() // 60 * 60)


# 创建全局单例实例
api_stats_manager = ApiStatsManager()


# 兼容现有代码的函数
def clean_expired_stats(api_call_stats):
    """清理过期统计数据的函数 (兼容旧接口)"""
    asyncio.create_task(api_stats_manager.cleanup())


async def update_api_call_stats(api_call_stats, endpoint=None, model=None, token=None):
    """更新API调用统计的函数 (兼容旧接口)"""
    if endpoint and model:
        await api_stats_manager.update_stats(
            endpoint, model, token if token is not None else 0
        )


async def get_api_key_usage(api_call_stats, api_key, model=None):
    """获取API密钥的调用次数 (兼容旧接口)"""
    return await api_stats_manager.get_api_key_usage(api_key, model)
