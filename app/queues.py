"""
PendingQueue: 双队列（VIP / Normal）的线程安全待处理队列

仅提供接口与文档注释，不含具体实现逻辑。用于后续与 BotManager 等模块对接。

设计要点：
- 两个 deque：VIP 段与 Normal 段，按类型存放；形成 Pending 的“前 VIP、后 Normal”的优先结构。
- 线程安全：所有公有方法需在内部加锁（RLock + Condition）。
- 两端插入：支持在各自子队列的 left/right 端插入（默认尾部 right）。
- 取单优先级：get_next() 优先从 VIP 子队列头部取；为空再从 Normal 子队列头部取。
- 阻塞与唤醒：支持阻塞式获取与超时；put 时唤醒等待者。
"""

from __future__ import annotations

from typing import Optional, Literal, Deque, Dict, Any
from collections import deque
import threading
import time
from .domain import Order


class PendingQueue:
    """双队列 Pending 结构的接口定义（仅注释，无实现）。

    线程安全约定：
    - 内部应维护：
      - self._vip: Deque[Order]         # VIP 子队列（队头在 left）
      - self._normal: Deque[Order]      # Normal 子队列（队头在 left）
      - self._lock: threading.RLock     # 保护所有共享状态
      - self._not_empty: threading.Condition(self._lock)  # 非空条件
    - 所有公有方法在进入后需获取 self._lock，保持原子性

    唤醒策略：
    - put/return_to_tail 等会使队列从空变非空，需 self._not_empty.notify()

    性能目标：
    - 所有入队/出队操作均为 O(1)
    """

    def __init__(self) -> None:
        """初始化内部结构，不做任何 I/O。"""
        self._vip: Deque[Order] = deque()
        self._normal: Deque[Order] = deque()
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)

    # -------------------- 入队 API --------------------

    def put(self, order: Order, end: Literal["left", "right"] = "right") -> None:
        """按订单类型入对应子队列。

        参数：
        - order: 满足 Order 协议的对象，必须包含 type: 'VIP'|'NORMAL'
        - end  : 插入端口，'left' 表示队头，'right' 表示队尾（默认）

        语义：
        - type == 'VIP'  -> 放入 VIP 队列的指定端
        - type == 'NORMAL' -> 放入 Normal 队列的指定端
        - 插入后调用 not_empty.notify() 唤醒可能等待的消费方
        """
        if end not in ("left", "right"):
            raise ValueError("end must be 'left' or 'right'")
        if order.type not in ("VIP", "NORMAL"):
            raise ValueError("order.type must be 'VIP' or 'NORMAL'")
        with self._lock:
            dq = self._vip if order.type == "VIP" else self._normal
            if end == "left":
                dq.appendleft(order)
            else:
                dq.append(order)
            self._not_empty.notify()

    def put_vip(self, order: Order, end: Literal["left", "right"] = "right") -> None:
        """显式放入 VIP 子队列（避免调用方传错类型）。

        - end 同上，默认队尾（right）。
        - 内部等价于 put(order_with_type_vip, end)
        """
        order.type = "VIP"  # 明确覆盖类型
        self.put(order, end=end)

    def put_normal(self, order: Order, end: Literal["left", "right"] = "right") -> None:
        """显式放入 Normal 子队列（避免调用方传错类型）。

        - end 同上，默认队尾（right）。
        - 内部等价于 put(order_with_type_normal, end)
        """
        order.type = "NORMAL"  # 明确覆盖类型
        self.put(order, end=end)

    # -------------------- 出队/读取 API --------------------

    def get_next(
        self,
        block: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[Order]:
        """按优先级获取一个订单：优先 VIP，随后 Normal；默认非阻塞。

        参数：
        - block  : 若为 True，当两队皆空时会阻塞等待 not_empty 条件
        - timeout: 阻塞等待的超时秒数；None 表示无限等待（当 block=True）

        返回：
        - 订单对象；若非阻塞或超时并且无订单可取，返回 None

        语义：
        - 先尝试从 VIP 子队列左侧弹出；若为空再尝试 Normal 子队列左侧
        - 成功取出后立即返回；失败时视 block/timeout 决定阻塞或返回 None
        """
        with self._lock:
            if not block:
                # 非阻塞：直接尝试一次
                if self._vip:
                    return self._vip.popleft()
                if self._normal:
                    return self._normal.popleft()
                return None
            # 阻塞模式
            # 使用 Condition 等待非空，支持超时
            end_time = None if timeout is None else time.monotonic() + max(0.0, timeout)
            while not self._vip and not self._normal:
                if end_time is None:
                    self._not_empty.wait()
                else:
                    remaining = end_time - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._not_empty.wait(remaining)
            if self._vip:
                return self._vip.popleft()
            return self._normal.popleft() if self._normal else None

    def get_vip(
        self,
        end: Literal["left", "right"] = "left",
        block: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[Order]:
        """仅从 VIP 子队列取一个订单，默认从队头（left）弹出。

        参数同 get_next，区别是只在 VIP 子队列上操作。
        """
        if end not in ("left", "right"):
            raise ValueError("end must be 'left' or 'right'")
        with self._lock:
            if not block:
                if not self._vip:
                    return None
                return self._vip.popleft() if end == "left" else self._vip.pop()
            # 阻塞
            end_time = None if timeout is None else time.monotonic() + max(0.0, timeout)
            while not self._vip:
                if end_time is None:
                    self._not_empty.wait()
                else:
                    remaining = end_time - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._not_empty.wait(remaining)
            return self._vip.popleft() if end == "left" else self._vip.pop()

    def get_normal(
        self,
        end: Literal["left", "right"] = "left",
        block: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[Order]:
        """仅从 Normal 子队列取一个订单，默认从队头（left）弹出。

        参数同 get_next，区别是只在 Normal 子队列上操作。
        """
        if end not in ("left", "right"):
            raise ValueError("end must be 'left' or 'right'")
        with self._lock:
            if not block:
                if not self._normal:
                    return None
                return self._normal.popleft() if end == "left" else self._normal.pop()
            # 阻塞
            end_time = None if timeout is None else time.monotonic() + max(0.0, timeout)
            while not self._normal:
                if end_time is None:
                    self._not_empty.wait()
                else:
                    remaining = end_time - time.monotonic()
                    if remaining <= 0:
                        return None
                    self._not_empty.wait(remaining)
            return self._normal.popleft() if end == "left" else self._normal.pop()

    def return_to_tail(self, order: Order) -> None:
        """将订单按其类型放回对应子队列队尾（right）。

        用途：处理中止/被打断时的回退，保持同优先级 FIFO，不插队。
        - type == 'VIP'    -> 回到 VIP 队尾
        - type == 'NORMAL' -> 回到 Normal 队尾
        - 需要唤醒等待者（notify）
        """
        # 回到对应类型队尾
        order_type = order.type
        if order_type not in ("VIP", "NORMAL"):
            raise ValueError("order.type must be 'VIP' or 'NORMAL'")
        with self._lock:
            if order_type == "VIP":
                self._vip.append(order)
            else:
                self._normal.append(order)
            self._not_empty.notify()

    def peek_next(self) -> Optional[Order]:
        """窥视下一个将被取走的订单（非破坏性）。

        - 若 VIP 非空，返回 VIP 队头；否则返回 Normal 队头；若都为空，返回 None
        - 仅用于展示/调试，不改变队列状态
        """
        with self._lock:
            if self._vip:
                return self._vip[0]
            if self._normal:
                return self._normal[0]
            return None

    def return_to_head(self, order: Order) -> None:
        """将订单按其类型放回对应子队列队首（left）。

        用途：在移除 Bot（-bot）时，正在处理的订单需要立即回到同优先级队列的队首，
        以便其他 Bot 立刻接手处理。
        """
        order_type = order.type
        if order_type not in ("VIP", "NORMAL"):
            raise ValueError("order.type must be 'VIP' or 'NORMAL'")
        with self._lock:
            if order_type == "VIP":
                self._vip.appendleft(order)
            else:
                self._normal.appendleft(order)
            self._not_empty.notify()

    # -------------------- 查询/快照 API --------------------

    def size_total(self) -> int:
        """返回 Pending 总长度：len(VIP) + len(Normal)。"""
        with self._lock:
            return len(self._vip) + len(self._normal)

    def size_vip(self) -> int:
        """返回 VIP 子队列长度。"""
        with self._lock:
            return len(self._vip)

    def size_normal(self) -> int:
        """返回 Normal 子队列长度。"""
        with self._lock:
            return len(self._normal)

    def is_empty(self) -> bool:
        """返回是否两个子队列都为空。"""
        with self._lock:
            return not self._vip and not self._normal

    def snapshot(self, max_items_per_queue: Optional[int] = None) -> Dict[str, Any]:
        """返回队列当前快照（浅拷贝），用于 CLI 展示。

        返回结构建议：
        {
          "vip": [order, ...],       # 最多 max_items_per_queue 个，None 表示不限制
          "normal": [order, ...],
          "vip_size": int,
          "normal_size": int,
          "total_size": int
        }
        注意：外部不应修改返回的订单对象；该方法仅用于只读展示。
        """
        with self._lock:
            def head(dq: Deque[Order]) -> list:
                if max_items_per_queue is None:
                    return list(dq)
                # 仅拷贝前 N 个，避免持锁太久
                res = []
                cnt = 0
                for item in dq:
                    if max_items_per_queue is not None and cnt >= max_items_per_queue:
                        break
                    res.append(item)
                    cnt += 1
                return res

            vip_list = head(self._vip)
            normal_list = head(self._normal)
            vip_size = len(self._vip)
            normal_size = len(self._normal)
            return {
                "vip": vip_list,
                "normal": normal_list,
                "vip_size": vip_size,
                "normal_size": normal_size,
                "total_size": vip_size + normal_size,
            }

    # -------------------- 等待/同步 API --------------------

    def wait_for_not_empty(self, timeout: Optional[float] = None) -> bool:
        """当两队皆空时阻塞等待，直到有订单入队或超时。

        参数：
        - timeout: 超时时间（秒），None 表示无限等待

        返回：
        - True 表示被唤醒且当前不为空；False 表示超时后仍为空
        """
        with self._lock:
            if self._vip or self._normal:
                return True
            signaled = self._not_empty.wait(timeout)
            return signaled and (bool(self._vip) or bool(self._normal))
