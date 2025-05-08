import sys,asyncio
#from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # 替换为异步调度器
from app.utils.logging import log
from app.utils.stats import api_stats_manager
from app.utils import check_version
from zoneinfo import ZoneInfo
from app.config import settings,persistence
import copy  # 添加copy模块导入

def handle_exception(exc_type, exc_value, exc_traceback):
    """
    全局异常处理函数
    
    处理未捕获的异常，并记录到日志中
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.excepthook(exc_type, exc_value, exc_traceback)
        return
    from app.utils.error_handling import translate_error
    error_message = translate_error(str(exc_value))
    log('error', f"未捕获的异常: {error_message}", status_code=500, error_message=error_message)


def schedule_cache_cleanup(response_cache_manager, active_requests_manager):
    """
    设置定期清理缓存和活跃请求的定时任务
    顺便定时检查更新
    Args:
        response_cache_manager: 响应缓存管理器实例
        active_requests_manager: 活跃请求管理器实例
    """
    beijing_tz = ZoneInfo("Asia/Shanghai")
    scheduler = AsyncIOScheduler(timezone=beijing_tz)  # 使用 AsyncIOScheduler 替代 BackgroundScheduler
    
    # 添加任务时直接传递异步函数（无需额外包装）
    scheduler.add_job(response_cache_manager.clean_expired, 'interval', minutes=1)
    scheduler.add_job(active_requests_manager.clean_completed, 'interval', seconds=30)
    scheduler.add_job(active_requests_manager.clean_long_running, 'interval', minutes=5, args=[300])
    
    # 使用同步包装器调用异步函数
    def run_cleanup():
        try:
            # 创建新的事件循环而不是获取现有的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 在这个新循环中运行清理操作
            loop.run_until_complete(api_stats_manager.cleanup())
        except Exception as e:
            log('error', f"清理统计数据时出错: {str(e)}")
        finally:
            # 确保关闭循环以释放资源
            loop.close()
    
    # 添加同步的清理任务
    scheduler.add_job(run_cleanup, 'interval', minutes=5)
    
    # 同样修改定时重置函数
    def run_reset():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(api_call_stats_clean())
        except Exception as e:
            log('error', f"重置统计数据时出错: {str(e)}")
        finally:
            loop.close()
    
    scheduler.add_job(check_version, 'interval', hours=4)
    scheduler.add_job(run_reset, 'cron', hour=15, minute=0)
    scheduler.start()
    return scheduler

async def api_call_stats_clean():
    """
    每天定时重置API调用统计数据，但保留每日统计数据
    
    使用新的统计系统重置，只清除24小时内的临时统计，保留每日累计统计
    """
    from app.utils.logging import log
    
    try:
        # 记录重置前的状态
        log('info', "开始重置API调用统计数据（保留每日统计数据）")
        
        # 使用新的统计系统重置
        await api_stats_manager.reset()
        
        log('info', "API调用统计数据已成功重置（保留每日统计数据）")
        persistence.save_settings()
            
    except Exception as e:
        log('error', f"重置API调用统计数据时发生错误: {str(e)}")
        raise