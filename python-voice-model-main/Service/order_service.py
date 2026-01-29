from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
import json


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ProductData:
    id: int
    name: str
    description: Optional[str]
    price: float
    stock_quantity: int
    sku: str


@dataclass(frozen=True)
class OrderData:
    id: int
    customer_id: int
    order_date: datetime
    total_amount: float
    status: OrderStatus


@dataclass(frozen=True)
class OrderItemData:
    order_id: int
    product_id: int
    quantity: int
    unit_price: float


class OrderService:
    """Static JSON-backed service that returns order details by ID."""

    _default_data_path = Path(__file__).resolve().parent.parent / "data" / "store.json"

    def __init__(self, data_path: Optional[Path] = None):
        self._data_path = data_path or self._default_data_path
        self._load_static_data()

    def _load_static_data(self) -> None:
        with self._data_path.open("r", encoding="utf-8") as handle:
            payload: Dict[str, Any] = json.load(handle)

        self._products: Dict[int, ProductData] = {
            product["id"]: ProductData(
                id=product["id"],
                name=product["name"],
                description=product.get("description"),
                price=float(product["price"]),
                stock_quantity=product.get("stock_quantity", 0),
                sku=product["sku"],
            )
            for product in payload.get("products", [])
        }

        self._orders_by_id: Dict[int, OrderData] = {
            order["id"]: OrderData(
                id=order["id"],
                customer_id=order["customer_id"],
                order_date=datetime.fromisoformat(order["order_date"]),
                total_amount=float(order["total_amount"]),
                status=OrderStatus(order["status"]),
            )
            for order in payload.get("orders", [])
        }

        self._order_items_by_order: Dict[int, List[OrderItemData]] = {}
        for item in payload.get("order_items", []):
            record = OrderItemData(
                order_id=item["order_id"],
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=float(item["unit_price"]),
            )
            self._order_items_by_order.setdefault(record.order_id, []).append(record)

    def get_order_by_id(self, order_id: int) -> Optional[OrderData]:
        return self._orders_by_id.get(order_id)

    def _get_order_items(self, order_id: int) -> List[Dict[str, Any]]:
        items = self._order_items_by_order.get(order_id, [])
        details: List[Dict[str, Any]] = []
        for item in items:
            product = self._products.get(item.product_id)
            if not product:
                continue
            total = item.unit_price * item.quantity
            details.append(
                {
                    "product_name": product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total": total,
                    "sku": product.sku,
                }
            )
        return details

    def format_order_details(self, order: OrderData) -> str:
        items = self._get_order_items(order.id)
        lines: List[str] = [
            f"Order #{order.id} Details:",
            f"- Order Date: {order.order_date.strftime('%Y-%m-%d %H:%M')}",
            f"- Status: {order.status.value}",
            f"- Total Amount: ${order.total_amount:.2f}",
            "",
            "Items:",
        ]

        if not items:
            lines.append("  No items recorded for this order.")
        else:
            for item in items:
                lines.append(f"  - {item['product_name']}")
                lines.append(f"    Quantity: {item['quantity']}")
                lines.append(f"    Price: ${item['unit_price']:.2f} each")
                lines.append(f"    Subtotal: ${item['total']:.2f}")

        return "\n".join(lines)