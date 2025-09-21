"""
Manager: 系统管理类（接口骨架）

职责：
- 管理 PendingQueue 实例与一组 Robot 实例
- 维护订单 ID 递增生成器
- 提供 CLI 需要的入口：新建订单、加/减 Bot、状态查询、优雅退出

注意：仅接口与文档注释；方法体抛出 NotImplementedError。
"""
from __future__ import annotations

from typing import Literal, Optional, Dict, Any, TYPE_CHECKING
from .domain import Order, OrderType
if TYPE_CHECKING:
    from .queues import PendingQueue
    from .robots import Robot


class Manager:
    """系统管理者。

    建议内部字段：
    - queue: PendingQueue 实例
    - bots: list[Robot]
    - next_order_id: int
    - next_bot_id: int
    - completed: list[dict] （可选，或让 CLI 直接从 queue.snapshot 获取）
    """

    def __init__(self, queue: "PendingQueue") -> None:
        """用传入的队列初始化管理器，计数器从 1 开始。"""
        raise NotImplementedError("Manager.__init__ is not implemented.")

    def new_order(self, order_type: OrderType) -> dict:
        """创建新订单（唯一递增 id），入对应队列尾部，返回订单字典。"""
        raise NotImplementedError("Manager.new_order is not implemented.")

    def add_bot(self) -> dict:
        """创建并启动一个新机器人，返回其状态。"""
        raise NotImplementedError("Manager.add_bot is not implemented.")

    def remove_bot(self) -> Optional[dict]:
        """移除“最新”机器人（创建序最后一个）。若无机器人返回 None。"""
        raise NotImplementedError("Manager.remove_bot is not implemented.")

    def status(self) -> Dict[str, Any]:
        """返回系统快照：队列与所有机器人状态。"""
        raise NotImplementedError("Manager.status is not implemented.")

    def shutdown(self) -> None:
        """优雅关闭：停止所有机器人并等待线程退出。"""
        raise NotImplementedError("Manager.shutdown is not implemented.")
