"""
Robots: 单个 Bot 的线程执行体

职责：
- 从 PendingQueue 拉取订单（阻塞），一次处理一个
- 每单处理固定时长（默认 10s，可配置）
- 支持中止（stop）：若正在处理则将订单回退到队尾
- 提供状态快照（IDLE/BUSY/STOPPED 与当前订单）
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Callable, Dict, Any
import threading
import time
from .domain import Order
if TYPE_CHECKING:
    from .queues import PendingQueue


class Robot:
    """Bot 执行体（线程友好）。

    建议内部字段：
    - bot_id: int
    - queue: PendingQueueProto
    - processing_time_sec: float = 10.0
    - state: Literal['IDLE','BUSY','STOPPED']
    - current_order: Optional[Order]
    - _thread: threading.Thread
    - _stop_event: threading.Event
    """

    def __init__(
        self,
        bot_id: int,
        queue: "PendingQueue",
        processing_time_sec: float = 10.0,
        on_complete: Optional[Callable[[Order], None]] = None,
    ) -> None:
        """初始化机器人，但不启动线程。"""
        self.bot_id = bot_id
        self.queue = queue
        self.processing_time_sec = processing_time_sec
        self._on_complete = on_complete

        self._state: str = "IDLE"  # 'IDLE' | 'BUSY' | 'STOPPED'
        self._current_order: Optional[Order] = None
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"Robot-{bot_id}", daemon=True)
        self._lock = threading.RLock()

    def start(self) -> None:
        """启动工作线程，循环拉单与处理。"""
        self._thread.start()

    def stop(self, join: bool = True, requeue_to_head: bool = False) -> None:
        """请求停止：
        - 若 BUSY：由工作线程检测到停止事件后，将 current_order 回到队列（默认队尾；若 requeue_to_head=True，则回队首）
        - 将状态置为 STOPPED，终止工作线程
        - join=True 时等待线程结束
        """
        # 将偏好写入实例，供运行线程读取
        self._requeue_to_head = bool(requeue_to_head)
        self._stop_event.set()
        if join:
            self._thread.join()

    def is_alive(self) -> bool:
        """返回工作线程是否仍存活。"""
        return self._thread.is_alive()

    def status(self) -> Dict[str, Any]:
        """返回状态快照：{bot_id, state, current_order_id}。"""
        with self._lock:
            return {
                "bot_id": self.bot_id,
                "state": self._state,
                "current_order_id": None if self._current_order is None else self._current_order.id,
            }

    # -------------------- 内部逻辑 --------------------

    def _run(self) -> None:
        """工作线程主体：循环取单、可中断处理。"""
        try:
            while not self._stop_event.is_set():
                # 取单：阻塞等待，有超时以便检查停止事件
                order = self.queue.get_next(block=True, timeout=0.2)
                if order is None:
                    continue

                with self._lock:
                    self._state = "BUSY"
                    self._current_order = order
                    order.status = "PROCESSING"

                # 处理：分段睡眠，允许及时响应 stop
                remaining = float(self.processing_time_sec)
                tick = 0.05 if remaining > 0.05 else remaining
                completed = False
                while remaining > 0 and not self._stop_event.is_set():
                    sleep_dur = tick if remaining >= tick else remaining
                    time.sleep(sleep_dur)
                    remaining -= sleep_dur

                if self._stop_event.is_set() and remaining > 0:
                    # 被中止，回退到队尾
                    order.status = "PENDING"
                    if getattr(self, "_requeue_to_head", False):
                        self.queue.return_to_head(order)
                    else:
                        self.queue.return_to_tail(order)
                    with self._lock:
                        self._current_order = None
                        self._state = "STOPPED"
                    break
                else:
                    # 正常完成
                    order.status = "COMPLETE"
                    if self._on_complete is not None:
                        try:
                            self._on_complete(order)
                        except Exception:
                            # 回调异常不应导致线程崩溃
                            pass
                    with self._lock:
                        self._current_order = None
                        # 若仍未接到 stop，回到 IDLE 继续循环
                        self._state = "IDLE" if not self._stop_event.is_set() else "STOPPED"

            # 收到停止：如果不是在 BUSY 中处理（上面已处理BUSY->STOPPED），则直接停止
            with self._lock:
                if self._state != "STOPPED":
                    self._state = "STOPPED"
        finally:
            # 保底清理：若仍挂着 current_order，将其回退
            with self._lock:
                order = self._current_order
                self._current_order = None
            if order is not None and order.status != "COMPLETE":
                order.status = "PENDING"
                try:
                    if getattr(self, "_requeue_to_head", False):
                        self.queue.return_to_head(order)
                    else:
                        self.queue.return_to_tail(order)
                except Exception:
                    pass
