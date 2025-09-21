"""
Domain models: 统一的订单定义

只在此处定义 Order，其他模块一律从这里导入，避免重复定义。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


OrderType = Literal["VIP", "NORMAL"]
OrderStatus = Literal["PENDING", "PROCESSING", "COMPLETE"]


@dataclass
class Order:
    """订单实体

    - id: 唯一递增整数，由管理类负责生成
    - type: 'VIP' | 'NORMAL'
    - status: 'PENDING' | 'PROCESSING' | 'COMPLETE'（默认 PENDING）
    """

    id: int
    type: OrderType
    status: OrderStatus = "PENDING"
