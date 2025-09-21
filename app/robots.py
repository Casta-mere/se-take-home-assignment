"""
Robots: 单个 Bot 的线程执行体（接口骨架）

职责：
- 从 PendingQueue 拉取订单（阻塞或非阻塞），一次处理一个
- 每单处理固定时长（默认 10s，可配置）
- 支持中止（stop）：若正在处理则将订单回退到队尾
- 提供状态可观测性（IDLE/BUSY/STOPPED 与当前订单）

注意：仅接口与文档注释；方法体抛出 NotImplementedError。
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
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

    def __init__(self, bot_id: int, queue: "PendingQueue", processing_time_sec: float = 10.0) -> None:
        """初始化机器人，但不启动线程。"""
        raise NotImplementedError("Robot.__init__ is not implemented.")

    def start(self) -> None:
        """启动工作线程，循环拉单与处理。"""
        raise NotImplementedError("Robot.start is not implemented.")

    def stop(self, join: bool = True) -> None:
        """请求停止：
        - 若 BUSY：回退 current_order 到队尾
        - 将状态置为 STOPPED，终止工作线程
        - join=True 时等待线程结束
        """
        raise NotImplementedError("Robot.stop is not implemented.")

    def is_alive(self) -> bool:
        """返回工作线程是否仍存活。"""
        raise NotImplementedError("Robot.is_alive is not implemented.")

    def status(self) -> dict:
        """返回状态快照：{bot_id, state, current_order_id}。"""
        raise NotImplementedError("Robot.status is not implemented.")
