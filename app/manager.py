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
        """初始化管理器并在内部创建队列，计数器从 1 开始。"""
        self.queue = PendingQueue()
        self.bots: list[Robot] = []
        self.next_order_id: int = 1
        self.next_bot_id: int = 1
        self.completed: list[Order] = []

    def new_order(self, order_type: OrderType) -> dict:
        """创建新订单（唯一递增 id），入对应队列尾部，返回订单字典。"""
        oid = self.next_order_id
        self.next_order_id += 1
        order = Order(id=oid, type=order_type, status="PENDING")
        if order_type == "VIP":
            self.queue.put_vip(order)
        else:
            self.queue.put_normal(order)
        return {"ok": True, "order": {"id": order.id, "type": order.type, "status": order.status}}

    def add_bot(self) -> dict:
        """创建并启动一个新机器人，返回其状态。"""
        bid = self.next_bot_id
        self.next_bot_id += 1
        bot = Robot(bid, self.queue, on_complete=self._on_complete)
        self.bots.append(bot)
        bot.start()
        return {"ok": True, "bot": bot.status()}

    def remove_bot(self) -> Optional[dict]:
        """移除“最新”机器人（创建序最后一个）。若无机器人返回 None。"""
        if not self.bots:
            return None
        bot = self.bots.pop()
        bot.stop(join=True, requeue_to_head=True)
        return {"ok": True, "bot_id": bot.status().get("bot_id")}

    def status(self) -> Dict[str, Any]:
        """返回系统快照：队列与所有机器人状态。"""
        return {
            "queue": self.queue.snapshot(max_items_per_queue=50),
            "bots": [b.status() for b in self.bots],
            "completed_count": len(self.completed),
            "completed_ids": [o.id for o in self.completed[-50:]],
        }

    def shutdown(self) -> None:
        """优雅关闭：停止所有机器人并等待线程退出。"""
        while self.bots:
            bot = self.bots.pop()
            bot.stop(join=True)

        # -------------------- CLI / CMD I/O --------------------

    def handle_cmd(self, line: str) -> Dict[str, Any]:
        """解析并执行一条命令行，返回结构化结果（不直接打印）。

        认可指令（大小写统一转小写处理）：
        - "new-normal" / "nn"      -> 创建普通订单
        - "new-vip" / "nv"         -> 创建 VIP 订单
        - "+bot" / "add-bot"        -> 新增一个机器人
        - "-bot" / "remove-bot"     -> 移除最新机器人
        - "status"                  -> 返回系统快照（队列 + 机器人）
        - "clear" / "cls"          -> 清屏
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
        cmd = (line or "").strip().lower()
        if not cmd:
            return {"ok": False, "cmd": cmd, "error": "empty command", "usage": self.help_text()}
        if cmd in ("help", "h", "?"):
            return {"ok": True, "cmd": cmd, "data": self.help_text()}
        if cmd in ("new-normal", "nn"):
            return self.new_order("NORMAL")
        if cmd in ("new-vip", "nv"):
            return self.new_order("VIP")
        if cmd in ("+bot", "add-bot"):
            return self.add_bot()
        if cmd in ("-bot", "remove-bot"):
            data = self.remove_bot()
            return data or {"ok": False, "cmd": cmd, "error": "no bot to remove"}
        if cmd in ("status",):
            return {"ok": True, "cmd": cmd, "data": self.status()}
        if cmd in ("clear", "cls"):
            return {"ok": True, "cmd": cmd, "data": {"clear": True}}
        if cmd in ("exit", "quit"):
            return {"ok": True, "cmd": cmd, "data": {"exit": True}}
        return {"ok": False, "cmd": cmd, "error": f"unknown command: {cmd}", "usage": self.help_text()}

    def help_text(self) -> str:
        """返回 CLI 帮助文本，供外层打印。"""
        return (
            "Commands:\n"
            "  new-normal | nn   - 新建普通订单\n"
            "  new-vip    | nv   - 新建 VIP 订单\n"
            "  +bot       | add-bot   - 增加一个机器人\n"
            "  -bot       | remove-bot- 移除最新机器人\n"
            "  clear | cls        - 清屏\n"
            "  status             - 查看系统状态\n"
            "  help|h|?           - 帮助\n"
            "  exit|quit          - 退出\n"
        )

    # -------------------- 回调 --------------------

    def _on_complete(self, order: Order) -> None:
        """当某机器人完成一个订单时的回调。"""
        self.completed.append(order)
