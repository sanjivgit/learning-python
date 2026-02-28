fake_db = {
    "1234": "Shipped",
    "5678": "Processing",
    "9999": "Delivered",
}


def create_order(status: str) -> str:
    order_id = str(len(fake_db) + 1).zfill(4)
    fake_db[order_id] = status
    return order_id


def get_order_status(order_id: str) -> str:
    return fake_db.get(order_id, "Order not found")