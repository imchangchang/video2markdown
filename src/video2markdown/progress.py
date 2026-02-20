"""进度监控和心跳日志工具.

用于在长时间运行的任务中提供实时反馈，便于排查卡顿问题。
"""

import threading
import time
from typing import Optional


class HeartbeatMonitor:
    """心跳监控器 - 定期输出日志表示任务仍在进行.
    
    用法:
        with HeartbeatMonitor("处理任务", interval=10):
            # 长时间运行的代码
            process_something()
    
    或手动控制:
        hb = HeartbeatMonitor("处理任务", interval=10)
        hb.start()
        try:
            process_something()
        finally:
            hb.stop()
    """
    
    def __init__(self, task_name: str, interval: int = 10, verbose: bool = True):
        """
        Args:
            task_name: 任务名称（显示在日志中）
            interval: 心跳间隔（秒）
            verbose: 是否输出日志
        """
        self.task_name = task_name
        self.interval = interval
        self.verbose = verbose
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
        self._last_message: Optional[str] = None
    
    def start(self):
        """启动心跳监控."""
        if not self.verbose:
            return
        
        self._start_time = time.time()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"    💓 [{self.task_name}] 开始...")
    
    def stop(self):
        """停止心跳监控."""
        if not self.verbose or self._thread is None:
            return
        
        self._stop_event.set()
        self._thread.join(timeout=1.0)
        
        if self._start_time:
            elapsed = time.time() - self._start_time
            print(f"    ✅ [{self.task_name}] 完成 (耗时 {elapsed:.1f}s)")
    
    def _run(self):
        """心跳线程."""
        while not self._stop_event.wait(self.interval):
            if self._start_time:
                elapsed = time.time() - self._start_time
                print(f"    💓 [{self.task_name}] 进行中... ({elapsed:.1f}s)", flush=True)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def log_progress(current: int, total: int, prefix: str = "进度", suffix: str = ""):
    """打印进度条.
    
    Args:
        current: 当前进度
        total: 总数
        prefix: 前缀文字
        suffix: 后缀文字
    """
    percent = (current / total * 100) if total > 0 else 0
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    
    message = f"    {prefix}: [{bar}] {percent:.1f}% ({current}/{total}) {suffix}"
    print(message, flush=True)


def log_stage(stage_name: str, message: str, indent: int = 0):
    """打印阶段日志.
    
    Args:
        stage_name: 阶段名称
        message: 消息内容
        indent: 缩进级别
    """
    prefix = "  " * indent
    print(f"{prefix}[{stage_name}] {message}", flush=True)
