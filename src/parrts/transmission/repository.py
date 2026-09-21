"""Transmission repository — queries canonical DMS for PARTS hard-parts vertical.

This layer sits between the resolver and the DMS. It never creates its own
source of truth.
"""
from __future__ import annotations

from typing import Any

from parrts.dms.service import DmsService


class TransmissionRepository:
    def __init__(self, dms: DmsService):
        self.dms = dms

    def find_parts_by_family_and_type(self, family: str, part_type: str) -> list[dict]:
        """Find catalog parts matching transmission family and part type hint."""
        sql = """
            SELECT sku, name, description, transmission_family, transmission_variant,
                   verification_status, source
            FROM catalog_parts
            WHERE transmission_family = ? 
              AND (name LIKE ? OR description LIKE ? OR category LIKE ?)
        """
        # Normalize part_type for matching (handle both "valve_body" and "valve body")
        normalized = part_type.replace("_", " ")
        like = f"%{normalized}%"
        rows = self.dms.store.fetchall(sql, (family, like, like, like))
        return [dict(r) for r in rows]

    def find_by_identifier(self, identifier_value: str) -> list[dict]:
        sql = """
            SELECT p.sku, p.name, p.transmission_family, pi.identifier_type, pi.identifier_value
            FROM catalog_parts p
            JOIN part_identifiers pi ON pi.sku = p.sku
            WHERE pi.identifier_value = ?
        """
        rows = self.dms.store.fetchall(sql, (identifier_value,))
        return [dict(r) for r in rows]

    def get_fitments(self, sku: str) -> list[dict]:
        sql = "SELECT * FROM part_fitments WHERE sku = ?"
        rows = self.dms.store.fetchall(sql, (sku,))
        return [dict(r) for r in rows]

    def get_inventory(self, sku: str) -> list[dict]:
        sql = """
            SELECT i.sku, i.qty, i.condition, l.code as location, l.name as location_name, i.bin
            FROM inventory_levels i
            JOIN locations l ON l.id = i.location_id
            WHERE i.sku = ?
        """
        rows = self.dms.store.fetchall(sql, (sku,))
        return [dict(r) for r in rows]

    def get_interchanges(self, sku: str) -> list[dict]:
        sql = """
            SELECT source_sku, target_sku, relationship_type, confidence, 
                   verification_status, notes
            FROM part_interchanges
            WHERE source_sku = ? OR target_sku = ?
        """
        rows = self.dms.store.fetchall(sql, (sku, sku))
        return [dict(r) for r in rows]

    def get_identifiers(self, sku: str) -> list[dict]:
        sql = "SELECT identifier_type, identifier_value FROM part_identifiers WHERE sku = ?"
        rows = self.dms.store.fetchall(sql, (sku,))
        return [dict(r) for r in rows]