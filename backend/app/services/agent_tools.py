"""
Dummy tools for specialized agents.
Each agent has its own set of tools that work with mock data.
"""
from langchain.tools import tool
import json
from datetime import datetime, timedelta
from typing import Dict, List

# ==================== DUMMY DATA STORES ====================

# Order dummy data
ORDERS_DB = {
    "ORD-12345": {
        "order_id": "ORD-12345",
        "status": "shipped",
        "items": ["Laptop Pro 15", "Wireless Mouse"],
        "total": 1299.99,
        "tracking_number": "TRK-ABC123",
        "estimated_delivery": "2026-02-01",
        "shipping_address": "123 Main St, New York, NY 10001"
    },
    "ORD-67890": {
        "order_id": "ORD-67890",
        "status": "processing",
        "items": ["Smartphone X"],
        "total": 899.99,
        "tracking_number": None,
        "estimated_delivery": "2026-02-05",
        "shipping_address": "456 Oak Ave, Los Angeles, CA 90001"
    },
    "ORD-11111": {
        "order_id": "ORD-11111",
        "status": "delivered",
        "items": ["Headphones Pro", "Phone Case"],
        "total": 249.99,
        "tracking_number": "TRK-XYZ789",
        "estimated_delivery": "2026-01-25",
        "shipping_address": "789 Pine Rd, Chicago, IL 60601"
    }
}

# Product dummy data
PRODUCTS_DB = {
    "laptop-pro-15": {
        "product_id": "laptop-pro-15",
        "name": "Laptop Pro 15",
        "price": 1199.99,
        "availability": "in_stock",
        "stock_count": 45,
        "features": ["15-inch display", "16GB RAM", "512GB SSD", "Intel i7"],
        "specifications": {
            "processor": "Intel Core i7-13700H",
            "memory": "16GB DDR4",
            "storage": "512GB NVMe SSD",
            "display": "15.6-inch Full HD",
            "weight": "1.8 kg"
        }
    },
    "laptop-pro-14": {
        "product_id": "laptop-pro-14",
        "name": "Laptop Pro 14",
        "price": 1199.99,
        "availability": "in_stock",
        "stock_count": 45,
        "features": ["15-inch display", "16GB RAM", "512GB SSD", "Intel i7"],
        "specifications": {
            "processor": "Intel Core i7-13700H",
            "memory": "16GB DDR4",
            "storage": "512GB NVMe SSD",
            "display": "15.6-inch Full HD",
            "weight": "1.8 kg"
        }
    },
    "smartphone-x": {
        "product_id": "smartphone-x",
        "name": "Smartphone X",
        "price": 899.99,
        "availability": "in_stock",
        "stock_count": 120,
        "features": ["6.7-inch OLED", "5G capable", "Triple camera", "128GB storage"],
        "specifications": {
            "display": "6.7-inch OLED",
            "processor": "Snapdragon 8 Gen 2",
            "memory": "8GB RAM",
            "storage": "128GB",
            "camera": "48MP + 12MP + 8MP"
        }
    },
    "headphones-pro": {
        "product_id": "headphones-pro",
        "name": "Headphones Pro",
        "price": 199.99,
        "availability": "low_stock",
        "stock_count": 5,
        "features": ["Active noise cancellation", "30-hour battery", "Bluetooth 5.3"],
        "specifications": {
            "battery_life": "30 hours",
            "connectivity": "Bluetooth 5.3",
            "weight": "250g",
            "driver_size": "40mm"
        }
    }
}

# Billing dummy data
INVOICES_DB = {
    "INV-2026-001": {
        "invoice_id": "INV-2026-001",
        "order_id": "ORD-12345",
        "amount": 1299.99,
        "status": "paid",
        "payment_method": "Credit Card ending in 4242",
        "date": "2026-01-20",
        "items": ["Laptop Pro 15", "Wireless Mouse"]
    },
    "INV-2026-002": {
        "invoice_id": "INV-2026-002",
        "order_id": "ORD-67890",
        "amount": 899.99,
        "status": "pending",
        "payment_method": "PayPal",
        "date": "2026-01-27",
        "items": ["Smartphone X"]
    }
}

REFUNDS_DB = {}  # Will store refund requests

# Account dummy data
ACCOUNTS_DB = {
    "user@example.com": {
        "email": "user@example.com",
        "username": "johndoe",
        "name": "John Doe",
        "phone": "555-123-4567",
        "address": "123 Main St, New York, NY",
        "account_created": "2025-06-15",
        "verified": True
    },
    "jane@example.com": {
        "email": "jane@example.com",
        "username": "janedoe",
        "name": "Jane Doe",
        "phone": "555-987-6543",
        "address": "456 Oak Ave, Los Angeles, CA",
        "account_created": "2025-09-20",
        "verified": True
    }
}


# ==================== ORDER AGENT TOOLS ====================

@tool
def get_order_status(order_id: str) -> str:
    """Get the current status of an order by order ID.
    
    Args:
        order_id: The order ID (e.g., ORD-12345)
    
    Returns:
        Order status information in JSON format
    """
    order_id = order_id.strip().upper()
    
    if order_id in ORDERS_DB:
        order = ORDERS_DB[order_id]
        return json.dumps({
            "order_id": order["order_id"],
            "status": order["status"],
            "items": order["items"],
            "total": order["total"]
        }, indent=2)
    
    return json.dumps({"error": f"Order {order_id} not found"})


@tool
def get_tracking_info(order_id: str) -> str:
    """Get tracking information for an order.
    
    Args:
        order_id: The order ID (e.g., ORD-12345)
    
    Returns:
        Tracking information in JSON format
    """
    if order_id in ORDERS_DB:
        order = ORDERS_DB[order_id]
        if order["tracking_number"]:
            return json.dumps({
                "order_id": order["order_id"],
                "tracking_number": order["tracking_number"],
                "status": order["status"],
                "estimated_delivery": order["estimated_delivery"],
                "shipping_address": order["shipping_address"]
            }, indent=2)
        else:
            return json.dumps({
                "order_id": order["order_id"],
                "message": "Tracking number not yet available. Order is being processed."
            })
    
    return json.dumps({"error": f"Order {order_id} not found"})


@tool
def cancel_order(order_id: str, reason: str = "Customer request") -> str:
    """Cancel an order if it hasn't been shipped yet.
    
    Args:
        order_id: The order ID to cancel
        reason: Reason for cancellation (optional)
    
    Returns:
        Cancellation result in JSON format
    """
    order_id = order_id.strip().upper()
    
    if order_id not in ORDERS_DB:
        return json.dumps({"error": f"Order {order_id} not found"})
    
    order = ORDERS_DB[order_id]
    
    if order["status"] in ["processing", "pending"]:
        ORDERS_DB[order_id]["status"] = "cancelled"
        return json.dumps({
            "success": True,
            "message": f"Order {order_id} has been cancelled",
            "refund_status": "Refund will be processed in 3-5 business days"
        }, indent=2)
    elif order["status"] == "shipped":
        return json.dumps({
            "success": False,
            "message": f"Order {order_id} has already shipped and cannot be cancelled. You can initiate a return instead."
        })
    else:
        return json.dumps({
            "success": False,
            "message": f"Order {order_id} is {order['status']} and cannot be cancelled"
        })

@tool
def get_all_orders() -> str:
    """Get all orders in the database.
    
    Returns:
        All orders in JSON format
    """
    return json.dumps(ORDERS_DB, indent=2)

# ==================== PRODUCT AGENT TOOLS ====================

@tool
def get_product_info(product_name: str) -> str:
    """Get detailed information about a product.
    
    Args:
        product_name: The product name or ID
    
    Returns:
        Product information in JSON format
    """
    # Normalize product name to ID format
    product_key = product_name.lower().strip().replace(" ", "-")
    
    # Try exact match first
    if product_key in PRODUCTS_DB:
        return json.dumps(PRODUCTS_DB[product_key], indent=2)
    
    # Try partial match
    for key, product in PRODUCTS_DB.items():
        if product_name.lower() in product["name"].lower():
            return json.dumps(product, indent=2)
    
    return json.dumps({"error": f"Product '{product_name}' not found"})


@tool
def check_product_availability(product_name: str) -> str:
    """Check if a product is available and how many are in stock.
    
    Args:
        product_name: The product name or ID
    
    Returns:
        Availability information in JSON format
    """
    product_key = product_name.lower().strip().replace(" ", "-")
    
    # Try exact match
    if product_key in PRODUCTS_DB:
        product = PRODUCTS_DB[product_key]
        return json.dumps({
            "product_name": product["name"],
            "availability": product["availability"],
            "stock_count": product["stock_count"],
            "price": product["price"]
        }, indent=2)
    
    # Try partial match
    for key, product in PRODUCTS_DB.items():
        if product_name.lower() in product["name"].lower():
            return json.dumps({
                "product_name": product["name"],
                "availability": product["availability"],
                "stock_count": product["stock_count"],
                "price": product["price"]
            }, indent=2)
    
    return json.dumps({"error": f"Product '{product_name}' not found"})

@tool
def get_all_products() -> str:
    """Get all products in the database.
    
    Returns:
        All products in JSON format
    """
    return json.dumps(PRODUCTS_DB, indent=2)

@tool
def get_product_price(product_name: str) -> str:
    """Get the current price of a product.
    
    Args:
        product_name: The product name or ID
    
    Returns:
        Price information in JSON format
    """
    product_key = product_name.lower().strip().replace(" ", "-")
    
    for key, product in PRODUCTS_DB.items():
        if product_key == key or product_name.lower() in product["name"].lower():
            return json.dumps({
                "product_name": product["name"],
                "price": product["price"],
                "availability": product["availability"]
            }, indent=2)
    
    return json.dumps({"error": f"Product '{product_name}' not found"})


# ==================== BILLING AGENT TOOLS ====================

@tool
def get_invoice(invoice_id: str) -> str:
    """Retrieve invoice details by invoice ID.
    
    Args:
        invoice_id: The invoice ID (e.g., INV-2026-001)
    
    Returns:
        Invoice information in JSON format
    """
    invoice_id = invoice_id.strip().upper()
    
    if invoice_id in INVOICES_DB:
        return json.dumps(INVOICES_DB[invoice_id], indent=2)
    
    return json.dumps({"error": f"Invoice {invoice_id} not found"})


@tool
def get_payment_status(order_id: str) -> str:
    """Check payment status for an order.
    
    Args:
        order_id: The order ID to check payment for
    
    Returns:
        Payment status information in JSON format
    """
    order_id = order_id.strip().upper()
    
    # Find invoice by order_id
    for invoice_id, invoice in INVOICES_DB.items():
        if invoice["order_id"] == order_id:
            return json.dumps({
                "order_id": order_id,
                "invoice_id": invoice["invoice_id"],
                "amount": invoice["amount"],
                "status": invoice["status"],
                "payment_method": invoice["payment_method"],
                "date": invoice["date"]
            }, indent=2)
    
    return json.dumps({"error": f"No invoice found for order {order_id}"})


@tool
def request_refund(order_id: str, reason: str) -> str:
    """Request a refund for an order.
    
    Args:
        order_id: The order ID to refund
        reason: Reason for refund request
    
    Returns:
        Refund request result in JSON format
    """
    order_id = order_id.strip().upper()
    
    if order_id not in ORDERS_DB:
        return json.dumps({"error": f"Order {order_id} not found"})
    
    # Check if already refunded
    if order_id in REFUNDS_DB:
        return json.dumps({
            "success": False,
            "message": "A refund has already been requested for this order"
        })
    
    # Create refund request
    refund_id = f"REF-{len(REFUNDS_DB) + 1:04d}"
    REFUNDS_DB[order_id] = {
        "refund_id": refund_id,
        "order_id": order_id,
        "reason": reason,
        "status": "processing",
        "requested_date": datetime.now().strftime("%Y-%m-%d"),
        "estimated_completion": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    }
    
    return json.dumps({
        "success": True,
        "refund_id": refund_id,
        "message": "Refund request submitted successfully",
        "status": "processing",
        "estimated_completion": REFUNDS_DB[order_id]["estimated_completion"]
    }, indent=2)


# ==================== ACCOUNT AGENT TOOLS ====================

@tool
def get_account_info(email: str, field: str = "all") -> str:
    """Get account information by email address.
    
    Args:
        email: The account email address
        field: Specific field to retrieve (email, username, name, phone, address, or 'all')
    
    Returns:
        Account information in JSON format
    """
    email = email.lower().strip()
    
    if email not in ACCOUNTS_DB:
        return json.dumps({"error": f"Account with email {email} not found"})
    
    account = ACCOUNTS_DB[email]
    
    if field == "all":
        return json.dumps(account, indent=2)
    
    if field in account:
        return json.dumps({field: account[field]}, indent=2)
    
    return json.dumps({"error": f"Field '{field}' not found in account"})


@tool
def update_account_email(old_email: str, new_email: str) -> str:
    """Update account email address.
    
    Args:
        old_email: Current email address
        new_email: New email address
    
    Returns:
        Update result in JSON format
    """
    old_email = old_email.lower().strip()
    new_email = new_email.lower().strip()
    
    if old_email not in ACCOUNTS_DB:
        return json.dumps({"error": f"Account with email {old_email} not found"})
    
    if new_email in ACCOUNTS_DB:
        return json.dumps({"error": f"Email {new_email} is already in use"})
    
    # Move account to new email key
    ACCOUNTS_DB[new_email] = ACCOUNTS_DB[old_email]
    ACCOUNTS_DB[new_email]["email"] = new_email
    del ACCOUNTS_DB[old_email]
    
    return json.dumps({
        "success": True,
        "message": f"Email updated from {old_email} to {new_email}",
        "verification_sent": True
    }, indent=2)


@tool
def update_account_username(email: str, new_username: str) -> str:
    """Update account username. Username must contain both first and last name.
    
    Args:
        email: Account email address
        new_username: New username (must be full name with first and last name)
    
    Returns:
        Update result in JSON format
    """
    email = email.lower().strip()
    new_username = new_username.strip()
    
    if email not in ACCOUNTS_DB:
        return json.dumps({"error": f"Account with email {email} not found"})
    
    # Validate that username contains at least 2 words (first and last name)
    username_parts = new_username.split()
    if len(username_parts) < 2:
        return json.dumps({
            "success": False,
            "partial_input": new_username,
            "message": "Username must include both first and last name. Please provide the full name.",
            "missing": "last_name" if len(username_parts) == 1 else "first_and_last_name"
        }, indent=2)
    
    old_username = ACCOUNTS_DB[email]["username"]
    ACCOUNTS_DB[email]["username"] = new_username
    
    return json.dumps({
        "success": True,
        "message": f"Username updated from '{old_username}' to '{new_username}'"
    }, indent=2)


@tool
def reset_password(email: str) -> str:
    """Send password reset link to account email.
    
    Args:
        email: Account email address
    
    Returns:
        Password reset result in JSON format
    """
    email = email.lower().strip()
    
    if email not in ACCOUNTS_DB:
        return json.dumps({"error": f"Account with email {email} not found"})
    
    return json.dumps({
        "success": True,
        "message": f"Password reset link sent to {email}",
        "expires_in": "24 hours"
    }, indent=2)


# ==================== TOOL REGISTRY ====================

ORDER_TOOLS = [get_order_status, get_tracking_info, cancel_order, get_all_orders]
PRODUCT_TOOLS = [get_product_info, check_product_availability, get_product_price, get_all_products]
BILLING_TOOLS = [get_invoice, get_payment_status, request_refund]
ACCOUNT_TOOLS = [get_account_info, update_account_email, update_account_username, reset_password]

ALL_TOOLS = ORDER_TOOLS + PRODUCT_TOOLS + BILLING_TOOLS + ACCOUNT_TOOLS

