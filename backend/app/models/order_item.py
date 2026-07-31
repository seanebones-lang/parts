"""Compatibility re-export — OrderItem lives in order.py."""

from app.models.order import OrderItem

__all__ = ["OrderItem"]
