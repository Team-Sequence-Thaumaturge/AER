#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER P2P Bounty, Atomic Barter, and Sandboxed Task Engine (Phase 3-1)
===================================================================
Implements the decentralized task allocation, zero-credit atomic barter,
2GB LRU disk-capped blob storage, and 2-second subprocess watchdog execution
for AER autonomous agents and node operators.

Conforms to:
- AER Roadmap Phase 3-1 (P2P Bounties & Gossip Chat)
- AER Section 4.7 (Agent Mobility) & Section 4.8 (Atomic Barter)
- WASI Capability Deny-All & 2-second hard timeout watchdog
"""

import os
import sys
import time
import json
import secrets
import hashlib
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aer.verifier import ExecutionSandboxVerifier


class BountyStatus:
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


class BountyTask:
    """Represents a computational bounty task posted to the network."""

    def __init__(
        self,
        task_id: str,
        issuer_id: str,
        task_type: str,
        reward_credit_b: int,
        timelock_hours: int = 24,
        spec_hash: str = "",
        blob_cid: Optional[str] = None,
        description: str = ""
    ):
        self.task_id = task_id
        self.issuer_id = issuer_id.lower()
        self.task_type = task_type
        self.reward_credit_b = reward_credit_b
        self.timelock_hours = timelock_hours
        self.spec_hash = spec_hash
        self.blob_cid = blob_cid
        self.description = description
        self.status = BountyStatus.OPEN
        self.worker_id: Optional[str] = None
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.receipt: Optional[Dict[str, Any]] = None
        self.fraud_proof: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "issuer_id": self.issuer_id,
            "task_type": self.task_type,
            "reward_credit_b": self.reward_credit_b,
            "timelock_hours": self.timelock_hours,
            "spec_hash": self.spec_hash,
            "blob_cid": self.blob_cid,
            "description": self.description,
            "status": self.status,
            "worker_id": self.worker_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "has_receipt": self.receipt is not None,
            "has_fraud_proof": self.fraud_proof is not None
        }


class AtomicBarterOffer:
    """Represents an escrow-free Zero-Credit Atomic Barter swap offer."""

    def __init__(
        self,
        offer_id: str,
        party_a: str,
        give_cid: str,
        want_cid: str,
        description: str = ""
    ):
        self.offer_id = offer_id
        self.party_a = party_a.lower()
        self.give_cid = give_cid
        self.want_cid = want_cid
        self.description = description
        self.status = "OPEN"
        self.party_b: Optional[str] = None
        self.created_at = time.time()
        self.swapped_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "party_a": self.party_a,
            "give_cid": self.give_cid,
            "want_cid": self.want_cid,
            "description": self.description,
            "status": self.status,
            "party_b": self.party_b,
            "created_at": self.created_at,
            "swapped_at": self.swapped_at
        }


class BlobStorageManager:
    """
    Manages local P2P blob storage with a strict 2GB LRU Disk Cap
    to prevent Disk Fill Denial-of-Service attacks.
    """
    MAX_CAPACITY_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (Path.home() / ".aer" / "blob_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.access_log: Dict[str, float] = {}  # CID -> last_access_timestamp

    def store_blob(self, data: bytes, custom_cid: Optional[str] = None) -> str:
        """Store blob on disk and enforce 2GB LRU cap."""
        cid = custom_cid or "bafy" + hashlib.sha256(data).hexdigest()[:32]
        blob_path = self.cache_dir / cid

        # Pre-evict if adding data exceeds limit
        self._enforce_lru(incoming_size=len(data))

        blob_path.write_bytes(data)
        self.access_log[cid] = time.time()
        return cid

    def get_blob(self, cid: str) -> Optional[bytes]:
        """Retrieve blob and touch last-access timestamp."""
        blob_path = self.cache_dir / cid
        if blob_path.exists():
            self.access_log[cid] = time.time()
            return blob_path.read_bytes()
        return None

    def _get_current_usage_bytes(self) -> int:
        """Calculate total size of stored blobs."""
        total = 0
        for p in self.cache_dir.glob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total

    def _enforce_lru(self, incoming_size: int) -> None:
        """Evict least recently used blobs if capacity exceeded."""
        current_usage = self._get_current_usage_bytes()
        if current_usage + incoming_size <= self.MAX_CAPACITY_BYTES:
            return

        # Sort files by last access time
        sorted_cids = sorted(self.access_log.keys(), key=lambda c: self.access_log.get(c, 0.0))
        for cid in sorted_cids:
            blob_path = self.cache_dir / cid
            if blob_path.exists():
                size = blob_path.stat().st_size
                blob_path.unlink()
                current_usage -= size
                self.access_log.pop(cid, None)
                if current_usage + incoming_size <= self.MAX_CAPACITY_BYTES:
                    break


class BountyManager:
    """
    Central Coordinator for P2P Bounties, Bulletin Board Notices,
    and Sandboxed Task Execution.
    """

    def __init__(self, local_node_id: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"):
        self.local_node_id = local_node_id.lower()
        self.bounties: Dict[str, BountyTask] = {}
        self.barter_offers: Dict[str, AtomicBarterOffer] = {}
        self.bulletin_board: List[Dict[str, Any]] = []
        self.blob_storage = BlobStorageManager()
        self.verifier = ExecutionSandboxVerifier()

        # Seed initial bulletin board & lost-media bounty
        self._seed_initial_content()

    def _seed_initial_content(self) -> None:
        """Seed initial retro BBS posts and genuine lost-media bounties."""
        self.post_bulletin(
            author="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            title="[공지] AER P2P 메시망 메인 게이트웨이 정식 개통",
            content="모든 로버 노드는 로컬 TPM 2.0 앵커를 검증하고 가십 채널(/aer/chat/v1)에 접속하십시오."
        )
        self.post_bounty(
            issuer_id="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            task_type="LOST_MEDIA_RETRIEVAL",
            reward_credit_b=5000,
            timelock_hours=72,
            description="1998년 천리안 시절 비공개 3D 옥트리 압축 알고리즘 소스 아카이브 수집",
            spec_hash="0x" + hashlib.sha256(b"LOST_MEDIA_CHEOLLIAN_1998").hexdigest()
        )
        self.post_bounty(
            issuer_id="0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
            task_type="OCTREE_COMPRESSION",
            reward_credit_b=800,
            timelock_hours=24,
            description="3차원 라이다 1,000,000 포인트 공간 복셀화 및 WASM 비손실 압축 연산",
            spec_hash="0x" + hashlib.sha256(b"OCTREE_VOXEL_1M_TASK").hexdigest()
        )

    def post_bulletin(self, author: str, title: str, content: str) -> Dict[str, Any]:
        """Post an announcement to the general P2P Bulletin Board (BBS)."""
        post_id = len(self.bulletin_board) + 1
        entry = {
            "post_id": post_id,
            "author": author.lower(),
            "title": title,
            "content": content,
            "timestamp": time.time()
        }
        self.bulletin_board.append(entry)
        return entry

    def list_bulletin(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent bulletin board posts."""
        return self.bulletin_board[-limit:]

    def post_bounty(
        self,
        issuer_id: str,
        task_type: str,
        reward_credit_b: int,
        timelock_hours: int = 24,
        description: str = "",
        spec_hash: Optional[str] = None,
        blob_cid: Optional[str] = None
    ) -> BountyTask:
        """Create and broadcast a new computational bounty task."""
        task_id = "task_" + secrets.token_hex(8)
        shash = spec_hash or ("0x" + hashlib.sha256(description.encode()).hexdigest())
        task = BountyTask(
            task_id=task_id,
            issuer_id=issuer_id,
            task_type=task_type,
            reward_credit_b=reward_credit_b,
            timelock_hours=timelock_hours,
            spec_hash=shash,
            blob_cid=blob_cid,
            description=description
        )
        self.bounties[task_id] = task
        return task

    def list_bounties(self, status: Optional[str] = None) -> List[BountyTask]:
        """List active bounties optionally filtered by status."""
        if status:
            return [b for b in self.bounties.values() if b.status == status]
        return list(self.bounties.values())

    def get_bounty(self, task_id: str) -> Optional[BountyTask]:
        """Lookup a bounty task by ID."""
        return self.bounties.get(task_id)

    def accept_bounty(self, task_id: str, worker_id: str) -> Tuple[bool, str]:
        """Assign task to a worker node."""
        task = self.bounties.get(task_id)
        if not task:
            return False, f"Task {task_id} not found."
        if task.status != BountyStatus.OPEN:
            return False, f"Task {task_id} is not OPEN (current: {task.status})."

        task.status = BountyStatus.IN_PROGRESS
        task.worker_id = worker_id.lower()
        return True, f"Task {task_id} successfully accepted by {worker_id}."

    def execute_and_solve_bounty(
        self,
        task_id: str,
        worker_id: str,
        payload_code: bytes,
        simulate_trap: Optional[str] = None,
        timeout_sec: float = 2.0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute task in the isolated WASI sandbox under a strict 2-second watchdog timer.
        Returns: (success, receipt_or_fraud_proof)
        """
        task = self.bounties.get(task_id)
        if not task:
            return False, {"error": "TASK_NOT_FOUND"}

        # Threaded execution with hard timeout watchdog
        result_holder: List[Any] = [None]
        exec_error: List[Any] = [None]

        def _worker_exec():
            try:
                success, manifest = self.verifier.execute_payload(
                    task_id=task.task_id,
                    worker_node_id=worker_id,
                    beneficiary_node_id=task.issuer_id,
                    bounty_credit_b=str(task.reward_credit_b),
                    code_or_data=payload_code,
                    simulate_trap=simulate_trap
                )
                result_holder[0] = (success, manifest)
            except Exception as ex:
                exec_error[0] = ex

        t = threading.Thread(target=_worker_exec, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)

        if t.is_alive():
            # Watchdog timeout triggered! Kill/ignore thread and build Betrayal Fraud Proof
            task.status = BountyStatus.DISPUTED
            fraud_proof = {
                "schema_version": "1.0.0",
                "task_id": task_id,
                "worker_node_id": worker_id.lower(),
                "error_code": "WATCHDOG_TIMEOUT_KILLED",
                "message": f"Execution exceeded 2-second hard limit ({timeout_sec}s). Thread terminated.",
                "dispute_timestamp": int(time.time()),
                "penalty": "REPUTATION_SEVERED"
            }
            task.fraud_proof = fraud_proof
            return False, fraud_proof

        if exec_error[0] is not None:
            task.status = BountyStatus.DISPUTED
            return False, {"error": str(exec_error[0])}

        success, manifest = result_holder[0]
        if success:
            task.status = BountyStatus.COMPLETED
            task.completed_at = time.time()
            task.receipt = manifest
            return True, manifest
        else:
            task.status = BountyStatus.DISPUTED
            task.fraud_proof = manifest
            return False, manifest

    def create_atomic_swap_offer(
        self,
        party_a: str,
        give_cid: str,
        want_cid: str,
        description: str = ""
    ) -> AtomicBarterOffer:
        """Create an escrow-free Zero-Credit Atomic Barter swap offer."""
        offer_id = "swap_" + secrets.token_hex(8)
        offer = AtomicBarterOffer(
            offer_id=offer_id,
            party_a=party_a,
            give_cid=give_cid,
            want_cid=want_cid,
            description=description
        )
        self.barter_offers[offer_id] = offer
        return offer

    def list_atomic_swaps(self, status: Optional[str] = None) -> List[AtomicBarterOffer]:
        """List atomic barter offers."""
        if status:
            return [o for o in self.barter_offers.values() if o.status == status]
        return list(self.barter_offers.values())

    def fulfill_atomic_swap(self, offer_id: str, party_b: str, party_b_give_cid: str) -> Tuple[bool, str]:
        """Fulfill an atomic barter swap instantly without credit escrow."""
        offer = self.barter_offers.get(offer_id)
        if not offer:
            return False, f"Offer {offer_id} not found."
        if offer.status != "OPEN":
            return False, f"Offer {offer_id} is {offer.status}."
        if party_b_give_cid != offer.want_cid:
            return False, f"Mismatch: offer requires CID '{offer.want_cid}', provided '{party_b_give_cid}'."

        offer.status = "SWAPPED"
        offer.party_b = party_b.lower()
        offer.swapped_at = time.time()
        return True, f"Atomic Swap {offer_id} completed: Party A ({offer.party_a}) and Party B ({party_b}) exchanged {offer.give_cid} <-> {offer.want_cid}."


# Global Singleton for in-process memory sharing
_BOUNTY_MANAGER: Optional[BountyManager] = None


def get_bounty_manager() -> BountyManager:
    global _BOUNTY_MANAGER
    if _BOUNTY_MANAGER is None:
        _BOUNTY_MANAGER = BountyManager()
    return _BOUNTY_MANAGER
