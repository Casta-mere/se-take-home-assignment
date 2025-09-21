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

    def __init__(self) -> None:
        """初始化管理器并在内部创建队列，计数器从 1 开始。

        约定：
        - self.queue: PendingQueue 由此处自行实例化（而非外部注入）
        - self.bots: list[Robot] 初始为空
        - self.next_order_id: int = 1
        - self.next_bot_id: int = 1
        """
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

        # -------------------- CLI / CMD I/O --------------------

    def handle_cmd(self, line: str) -> Dict[str, Any]:
            """解析并执行一条命令行，返回结构化结果（不直接打印）。

            认可指令（大小写统一转小写处理）：
            - "new-normal" / "nn"      -> 创建普通订单
            - "new-vip" / "nv"         -> 创建 VIP 订单
            - "+bot" / "add-bot"        -> 新增一个机器人
            - "-bot" / "remove-bot"     -> 移除最新机器人
            - "status"                  -> 返回系统快照（队列 + 机器人）
            - "exit" / "quit"          -> 请求退出（由外层 CLI 决定是否终止进程）

            约定：
            - 本方法不做阻塞 I/O，不直接读取/打印；只做解析与调度。
            - 返回值建议格式：
                {
                    "ok": bool,
                    "cmd": str,
                    "data": Any | None,
                    "error": str | None,
                }
            - 未知命令：ok=False，并附带 error 与 usage。
            """
            raise NotImplementedError("Manager.handle_cmd is not implemented.")

    def help_text(self) -> str:
            """返回 CLI 帮助文本，供外层打印。"""
            raise NotImplementedError("Manager.help_text is not implemented.")
