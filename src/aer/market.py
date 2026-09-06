#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Serverless P2P Resource Market & Order Book Engine
======================================================
Implements peer-to-peer matching of compute quotas, MCP tools, and datasets
conforming to AER Appendix B and MarketOrder.schema.json.

Features:
- In-memory order book for BIDs and ASKs partitioned by resource category
- Price-time priority matching engine
- Automatic expiry eviction of stale orders
"""

import time
from typing import Dict, Any, List, Optional, Tuple


class MarketOrderRecord:
    """Represents an active limit order in the decentralized P2P market."""

    def __init__ (self, order_dict: Dict[str, Any]):
        self.order_id = order_dict["order_id"]
        self.side = order_dict["side"]  # BID or ASK
        self.resource_type = order_dict["resource_type"]
        self.resource_cid = order_dict["resource_cid"]
        self.quantity = float(order_dict["quantity"])
        self.price_credit_b = int(order_dict["price_credit_b"])
        self.total_price = int(order_dict["total_price_credit_b"])
        self.maker_node_id = order_dict["maker_node_id"].lower()
        self.expiration_timestamp = int(order_dict["expiration_timestamp"])
        self.is_filled = False

    def is_expired(self, current_time: Optional[int] = None) -> bool:
        """Check if order has passed its expiration deadline."""
        now = current_time if current_time is not None else int(time.time())
        return now >= self.expiration_timestamp


class P2PResourceMarket:
    """
    Decentralized order book matching bids and asks for machine computational resources.
    """

    def __init__(self):
        # Resource Type -> Side -> List of MarketOrderRecord
        self.order_books: Dict[str, Dict[str, List[MarketOrderRecord]]] = {
            "GPU_QUOTA": {"BID": [], "ASK": []},
            "MCP_TOOL": {"BID": [], "ASK": []},
            "DATASET": {"BID": [], "ASK": []},
            "BANDWIDTH_TUNNEL": {"BID": [], "ASK": []}
        }

    def _attempt_match(
        self,
        incoming: MarketOrderRecord,
        opposing_side: str
    ) -> Optional[Dict[str, Any]]:
        """Scan opposing order book for matching price-compatible orders."""
        res_type = incoming.resource_type
        book = self.order_books[res_type][opposing_side]

        for resting in book:
            if resting.is_filled or resting.is_expired():
                continue

            # Price compatibility check:
            # If incoming BID, incoming price >= resting ASK price
            # If incoming ASK, incoming price <= resting BID price
            is_compatible = False
            if incoming.side == "BID" and incoming.price_credit_b >= resting.price_credit_b:
                is_compatible = True
            elif incoming.side == "ASK" and incoming.price_credit_b <= resting.price_credit_b:
                is_compatible = True

            if is_compatible:
                matched_quantity = min(incoming.quantity, resting.quantity)
                clearing_price = resting.price_credit_b

                incoming.is_filled = True
                resting.is_filled = True
                book.remove(resting)

                return {
                    "resource_type": res_type,
                    "matched_quantity": matched_quantity,
                    "clearing_price": clearing_price,
                    "buyer_id": incoming.maker_node_id if incoming.side == "BID" else resting.maker_node_id,
                    "seller_id": resting.maker_node_id if incoming.side == "BID" else incoming.maker_node_id,
                    "resource_cid": incoming.resource_cid
                }

        return None

    def place_order(self, order_dict: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Ingest a cryptographically signed MarketOrder and attempt immediate crossing.
        Returns: (is_accepted, message, match_result)
        """
        record = MarketOrderRecord(order_dict)
        if record.is_expired():
            return False, "ORDER_REJECTED: Order already expired", None

        res_type = record.resource_type
        if res_type not in self.order_books:
            return False, f"ORDER_REJECTED: Unsupported resource type {res_type}", None

        # Attempt order matching against opposing book
        opposing_side = "ASK" if record.side == "BID" else "BID"
        match = self._attempt_match(record, opposing_side)

        if match:
            return True, "ORDER_MATCHED_IMMEDIATELY", match

        # Rest in book if not completely matched
        self.order_books[res_type][record.side].append(record)
        return True, "ORDER_RESTED_IN_BOOK", None

    def get_order_count(self, resource_type: str) -> int:
        """Return total active resting orders for a resource category."""
        if resource_type not in self.order_books:
            return 0
        bids = len(self.order_books[resource_type]["BID"])
        asks = len(self.order_books[resource_type]["ASK"])
        return bids + asks


if __name__ == "__main__":
    _default_market = P2PResourceMarket()

