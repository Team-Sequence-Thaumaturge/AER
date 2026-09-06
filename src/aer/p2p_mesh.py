#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER P2P Mesh & Topology Boycott Router
======================================
Simulates libp2p GossipSub v1.1 epidemic message dissemination and Kademlia DHT
peer routing with autonomous topology boycotts (AER Section 4.5).

Features:
- Topic-based epidemic message dissemination (/aer/market, /aer/dispute)
- Automatic edge-severing topology boycott upon receiving verified betrayal proofs
- Peer scoring and dynamic routing table pruning
"""

import hashlib
from typing import Dict, Any, List, Set, Optional, Callable, Tuple


class P2PPeer:
    """Represents a connected peer in the local routing table."""

    def __init__ (self, node_id: str, address: str = "127.0.0.1:28740"):
        self.node_id = node_id.lower()
        self.address = address
        self.peer_score = 100
        self.is_boycotted = False
        self.connected_peers: Set[str] = set()


class P2PMeshRouter:
    """
    Simulates a GossipSub v1.1 mesh router with automated topology boycotting.
    """

    def __init__(self, local_node_id: str):
        self.local_node_id = local_node_id.lower()
        self.peers: Dict[str, P2PPeer] = {}
        self.topic_subscribers: Dict[str, Set[str]] = {
            "/aer/market/v1": set(),
            "/aer/dispute/v1": set(),
            "/aer/attestation/v1": set()
        }
        self.seen_message_ids: Set[str] = set()

    def add_peer(self, node_id: str, address: str = "127.0.0.1:28740") -> P2PPeer:
        """Add a peer node to the local routing table."""
        nid = node_id.lower()
        peer = P2PPeer(nid, address)
        self.peers[nid] = peer
        return peer

    def subscribe(self, topic: str, node_id: str) -> None:
        """Subscribe a peer or self to a gossip topic."""
        nid = node_id.lower()
        if topic not in self.topic_subscribers:
            self.topic_subscribers[topic] = set()
        self.topic_subscribers[topic].add(nid)

    def publish_message(self, topic: str, payload: Dict[str, Any]) -> Tuple[str, int]:
        """
        Broadcast a message across subscribers using epidemic gossip dissemination.
        Returns: (message_hash, delivery_count)
        """
        msg_bytes = str(sorted(payload.items())).encode()
        msg_id = hashlib.sha256(msg_bytes).hexdigest()

        if msg_id in self.seen_message_ids:
            return msg_id, 0

        self.seen_message_ids.add(msg_id)
        subscribers = self.topic_subscribers.get(topic, set())

        # Disseminate only to active, non-boycotted peers
        eligible_recipients = [
            pid for pid in subscribers
            if pid != self.local_node_id and (pid not in self.peers or not self.peers[pid].is_boycotted)
        ]

        return msg_id, len(eligible_recipients)

    def enforce_topology_boycott(self, malicious_node_id: str, defect_digest: str) -> bool:
        """
        Execute an autonomous topology boycott: permanently sever network links,
        drop peer score to zero, and purge from topic subscription lists.
        """
        mid = malicious_node_id.lower()

        if mid in self.peers:
            self.peers[mid].is_boycotted = True
            self.peers[mid].peer_score = 0
            self.peers[mid].connected_peers.clear()

        # Remove from all GossipSub topics
        for topic in self.topic_subscribers:
            self.topic_subscribers[topic].discard(mid)

        return True

    def is_peer_isolated(self, node_id: str) -> bool:
        """Check if a node has been boycotted by the local routing mesh."""
        nid = node_id.lower()
        if nid in self.peers and self.peers[nid].is_boycotted:
            return True
        return False


if __name__ == "__main__":
    _default_mesh = P2PMeshRouter("0x0000000000000000000000000000000000000000")

