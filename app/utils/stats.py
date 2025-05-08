import asyncio 
from datetime import datetime, timedelta
from app.utils.logging import log
import app.config.settings as settings
from collections import defaultdict, Counter
import time
import threading
import queue
import functools
import json
import os

class ApiStatsManager:
    """API调用统计管理器，优化性能的新实现"""
    
    def __init__(self, enable_background=True, batch_interval=1.0):
        # 使用Counter记录API密钥和模型的调用次数
        self.api_key_counts = Counter()  # 记录每个API密钥的调用次数
        self.model_counts = Counter()    # 记录每个模型的调用次数
        self.api_model_counts = defaultdict(Counter)  # 记录每个API密钥对每个模型的调用次数
        
        # 记录token使用量
        self.api_key_tokens = Counter()  # 记录每个API密钥的token使用量
        self.model_tokens = Counter()    # 记录每个模型的token使用量
        self.api_model_tokens = defaultdict(Counter)  # 记录每个API密钥对每个模型的token使用量
        
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
        
        # 每日统计数据
        self._daily_stats_lock = threading.Lock()
        self.daily_stats = {}  # 格式: {date_str: {"calls": count, "tokens": count}}
        self.permanent_daily_stats = {}  # 持久化存储的每日统计数据
        self._daily_stats_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "daily_stats.json")
        
        # 创建数据目录（如果不存在）
        os.makedirs(os.path.dirname(self._daily_stats_file), exist_ok=True)
        
        # 加载持久化的每日统计数据
        self._load_daily_stats()
        
        # 保存统计数据的计数器和定时器
        self._save_counter = 0
        self._last_save_time = time.time()
        
        if enable_background:
            self._start_worker()
    
    def _start_worker(self):
        """启动后台工作线程"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True
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
                
                # 检查是否需要保存每日统计数据（每5分钟保存一次）
                if current_time - self._last_save_time >= 300:  # 5分钟
                    try:
                        self._save_daily_stats_async()
                        self._last_save_time = current_time
                    except Exception as e:
                        log('error', f"保存每日统计数据失败: {str(e)}")
                
                # 短暂休眠以避免CPU占用过高
                time.sleep(0.01)
                
            except Exception as e:
                log('error', f"后台处理线程错误: {str(e)}")
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
    
    def _load_daily_stats(self):
        """加载持久化的每日统计数据"""
        try:
            # 确保数据目录存在
            os.makedirs(os.path.dirname(self._daily_stats_file), exist_ok=True)
            
            if os.path.exists(self._daily_stats_file):
                with open(self._daily_stats_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # 确保文件不为空
                        self.permanent_daily_stats = json.loads(content)
                        log('info', f"成功加载每日统计数据: {len(self.permanent_daily_stats)}天")
                    else:
                        self.permanent_daily_stats = {}
                        log('info', "每日统计数据文件为空，初始化新的统计数据")
            else:
                # 创建新的空文件
                with open(self._daily_stats_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                self.permanent_daily_stats = {}
                log('info', "每日统计数据文件不存在，创建新的统计文件")
                
            # 确保今天的统计数据存在
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in self.daily_stats:
                self.daily_stats[today] = {"calls": 0, "tokens": 0}
                
        except Exception as e:
            self.permanent_daily_stats = {}
            log('error', f"加载每日统计数据失败: {str(e)}")
            # 尝试创建空白文件以修复问题
            try:
                os.makedirs(os.path.dirname(self._daily_stats_file), exist_ok=True)
                with open(self._daily_stats_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                log('info', "创建了新的每日统计数据文件")
            except Exception as write_err:
                log('error', f"无法创建每日统计数据文件: {str(write_err)}")
    
    def _save_daily_stats(self):
        """保存每日统计数据到文件（同步方法）"""
        try:
            # 确保数据目录存在
            os.makedirs(os.path.dirname(self._daily_stats_file), exist_ok=True)
            
            with self._daily_stats_lock:
                # 将当前内存中的数据合并到永久存储
                today = datetime.now().strftime("%Y-%m-%d")
                if today in self.daily_stats:
                    if today not in self.permanent_daily_stats:
                        self.permanent_daily_stats[today] = {"calls": 0, "tokens": 0}
                    
                    # 将今天的临时数据添加到永久数据
                    self.permanent_daily_stats[today]["calls"] += self.daily_stats[today]["calls"]
                    self.permanent_daily_stats[today]["tokens"] += self.daily_stats[today]["tokens"]
                    
                    # 记录日志，便于调试
                    log('info', f"每日统计更新: 日期={today}, 调用数增加={self.daily_stats[today]['calls']}, Token数增加={self.daily_stats[today]['tokens']}")
                    
                    # 清空当天的临时数据
                    self.daily_stats[today] = {"calls": 0, "tokens": 0}
                
                # 保存到文件
                with open(self._daily_stats_file, 'w', encoding='utf-8') as f:
                    json.dump(self.permanent_daily_stats, f, ensure_ascii=False, indent=2)
                
                log('info', f"每日统计数据已保存: {len(self.permanent_daily_stats)}天")
        except Exception as e:
            log('error', f"保存每日统计数据失败: {str(e)}")
            # 尝试修复问题
            try:
                os.makedirs(os.path.dirname(self._daily_stats_file), exist_ok=True)
                log('info', "数据目录已重新创建")
            except Exception:
                log('error', "无法创建数据目录")
    
    def _save_daily_stats_async(self):
        """在后台线程中保存每日统计数据"""
        threading.Thread(target=self._save_daily_stats, daemon=True).start()
    
    async def update_stats(self, api_key, model, tokens=0):
        """更新API调用统计"""
        # 日志记录开始进行统计更新
        log('debug', f"开始更新API调用统计: 秘钥={api_key[:8]}, 模型={model}, 令牌={tokens}")
        
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
                'api_key': api_key,
                'model': model,
                'timestamp': now,
                'tokens': tokens
            }
            
            self.recent_calls.append(compact_call)
            if len(self.recent_calls) > self.max_recent_calls:
                self.recent_calls.pop(0)
        
        # 更新每日统计数据（不锁定整个方法）
        today = now.strftime("%Y-%m-%d")
        
        # 使用更小粒度的锁
        with self._daily_stats_lock:
            if today not in self.daily_stats:
                self.daily_stats[today] = {"calls": 0, "tokens": 0}
            
            self.daily_stats[today]["calls"] += 1
            self.daily_stats[today]["tokens"] += tokens
            
            # 记录日志，便于调试
            daily_calls = self.daily_stats[today]["calls"]
            daily_tokens = self.daily_stats[today]["tokens"]
            log('debug', f"已更新今日统计: 日期={today}, 当前调用数={daily_calls}, 当前Token数={daily_tokens}")
            
            # 增加计数器，但不每次都保存
            self._save_counter += 1
        
        # 避免在主请求处理流程中执行文件IO操作
        # 只有在累积了足够的调用次数后，才在后台保存数据
        if self._save_counter >= 10:  # 每10次调用考虑保存一次（之前是100次，改为更频繁保存）
            with self._daily_stats_lock:
                self._save_counter = 0
            
            # 在后台线程中执行保存，避免阻塞主线程
            self._save_daily_stats_async()
        
        # 记录日志
        log_message = f"API调用已记录: 秘钥 '{api_key[:8]}', 模型 '{model}', 令牌: {tokens if tokens is not None else 0}"
        log('info', log_message)
    
    async def cleanup(self):
        """清理超过24小时的时间桶数据"""
        now = datetime.now()
        day_ago_ts = self._get_minute_timestamp(now - timedelta(days=1))
        
        with self._time_series_lock:
            # 直接删除旧的时间桶
            for ts in list(self.time_buckets.keys()):
                if ts < day_ago_ts:
                    del self.time_buckets[ts]
        
        # 清理90天前的每日统计数据
        with self._daily_stats_lock:
            days_90_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")
            for date in list(self.permanent_daily_stats.keys()):
                if date < days_90_ago:
                    del self.permanent_daily_stats[date]
            
            # 在后台保存清理后的数据
            threading.Thread(target=self._save_daily_stats, daemon=True).start()
        
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
            return sum(data["calls"] for ts, data in self.time_buckets.items() 
                      if ts >= hour_ago_ts)
    
    def get_calls_last_minute(self, now=None):
        """获取过去一分钟的总调用次数"""
        if now is None:
            now = datetime.now()
        
        minute_ago_ts = self._get_minute_timestamp(now - timedelta(minutes=1))
        
        with self._time_series_lock:
            return sum(data["calls"] for ts, data in self.time_buckets.items() 
                      if ts >= minute_ago_ts)
    
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
                
                calls_series.append({
                    'time': minute_dt.strftime('%H:%M'),
                    'value': bucket["calls"]
                })
                
                tokens_series.append({
                    'time': minute_dt.strftime('%H:%M'),
                    'value': bucket["tokens"]
                })
        
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
                    model_stats[model] = {
                        'calls': count,
                        'tokens': tokens
                    }
                
                usage_percent = (calls_24h / settings.API_KEY_DAILY_LIMIT) * 100 if settings.API_KEY_DAILY_LIMIT > 0 else 0
                
                stats.append({
                    'api_key': api_key_id,
                    'calls_24h': calls_24h,
                    'total_tokens': total_tokens,
                    'usage_percent': round(usage_percent, 1),
                    'model_stats': model_stats
                })
        
        return stats
    
    def get_daily_stats(self, days=15):
        """获取最近N天中有数据的日期统计
        只返回最近N天中实际有调用数据的日期，按日期降序排序"""
        now = datetime.now()
        stats = []
        
        # 先触发一次同步保存，确保当天最新数据也被包含
        self._save_daily_stats()
        
        # 使用本地副本处理数据，减少锁定时间
        local_copy = {}
        with self._daily_stats_lock:
            local_copy = self.permanent_daily_stats.copy()
        
        # 如果没有数据，添加今天的数据作为默认
        if not local_copy:
            today = now.strftime("%Y-%m-%d")
            local_copy[today] = {"calls": 0, "tokens": 0}
            log('info', "没有历史数据，添加今天的空数据")
        
        # 获取所有有数据的日期（如果没有数据，也包括今天）
        data_dates = sorted(local_copy.keys(), reverse=True)
        
        # 只返回最近15天的日期
        recent_dates = []
        for date in data_dates:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            if (now - date_obj).days <= days:
                recent_dates.append(date)
            if len(recent_dates) >= days:
                break
        
        # 构建返回数据
        for date in recent_dates:
            stats.append({
                "date": date,
                "calls": local_copy[date]["calls"],
                "tokens": local_copy[date]["tokens"]
            })
        
        # 记录日志
        if stats:
            log('info', f"获取每日统计数据: {len(stats)}天的数据")
        else:
            log('warning', "没有找到任何历史统计数据")
        
        return stats
    
    async def reset(self):
        """重置所有统计数据，但保留每日统计数据"""
        # 在重置前保存当前的每日统计数据到永久存储
        self._save_daily_stats()
        
        with self._counters_lock:
            self.api_key_counts.clear()
            self.model_counts.clear()
            self.api_model_counts.clear()
            self.api_key_tokens.clear()
            self.model_tokens.clear()
            self.api_model_tokens.clear()
        
        with self._time_series_lock:
            self.time_buckets.clear()
            self.current_minute = self._get_minute_timestamp(datetime.now())
        
        with self._recent_calls_lock:
            self.recent_calls.clear()
        
        # 不再清除daily_stats数据
        # 但记录一条日志说明此次重置没有影响每日统计
        log('info', "API调用统计数据已重置，但保留了每日统计数据")
    
    def _get_minute_timestamp(self, dt):
        """将日期时间对象转换为分钟级别的时间戳字符串"""
        return dt.strftime("%Y-%m-%d %H:%M:00")

# 初始化全局API统计管理器实例
api_stats_manager = ApiStatsManager()

# 兼容现有代码的函数
def clean_expired_stats(api_call_stats):
    """清理过期的API调用统计数据"""
    # 调用API统计管理器的清理方法
    asyncio.create_task(api_stats_manager.maybe_cleanup(force=True))

async def update_api_call_stats(api_call_stats, endpoint=None, model=None, token=None): 
    """更新API调用统计数据（兼容旧接口）"""
    if endpoint and model:
        # 调用API统计管理器的更新方法
        await api_stats_manager.update_stats(endpoint, model, token or 0)

async def get_api_key_usage(api_call_stats, api_key, model=None):
    """获取API密钥的使用统计（兼容旧接口）"""
    # 调用API统计管理器的获取方法
    return await api_stats_manager.get_api_key_usage(api_key, model) 