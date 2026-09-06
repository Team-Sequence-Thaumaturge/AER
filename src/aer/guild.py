#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AER Guild Sub-Channel & Bulkhead Isolation Engine
=================================================
Manages recursive off-chain sub-state channels and bulkhead blast radius containment
(AER Section 4.5 & Roadmap Phase 3).

Features:
- Federated mutual credit pools for worker clusters
- Bulkhead compartment isolation preventing systemic contagion
- Supernova explosion containment: guild master betrayal destroys only master collateral
  while preserving innocent worker balances and downstream escrows
"""

from typing import Dict, Any, List, Optional, Set


class GuildMember:
    """Represents a worker node operating within a federated guild channel."""

    def __init__ (self, node_id: str, allocated_credit: int = 0):
        self.node_id = node_id.lower()
        self.allocated_credit = allocated_credit
        self.earned_balance = 0
        self.is_active = True


class GuildChannel:
    """
    Off-chain state channel pooling credit under a supervising guild master node.
    """

    def __init__ (self, guild_id: str, master_node_id: str, collateral_deposit: int):
        self.guild_id = guild_id
        self.master_node_id = master_node_id.lower()
        self.master_collateral = collateral_deposit
        self.members: Dict[str, GuildMember] = {}
        self.is_compromised = False
        self.bulkhead_sealed = False

    def add_member(self, node_id: str, credit_allocation: int) -> bool:
        """Admit a worker node into the guild channel with an allocated credit quota."""
        if self.bulkhead_sealed or self.is_compromised:
            return False
        nid = node_id.lower()
        self.members[nid] = GuildMember(nid, credit_allocation)
        return True

    def credit_member_earnings(self, node_id: str, amount: int) -> bool:
        """Credit task payout directly to guild member internal balance."""
        nid = node_id.lower()
        if nid in self.members:
            self.members[nid].earned_balance += amount
            return True
        return False

    def trigger_bulkhead_isolation(self) -> Dict[str, Any]:
        """
        Execute emergency bulkhead isolation upon guild master default or betrayal.
        Containment Rule:
        - Master collateral is forfeited/burned
        - Worker balances are sealed and protected for unencumbered on-chain exit
        """
        self.bulkhead_sealed = True
        self.is_compromised = True

        forfeited_master_capital = self.master_collateral
        self.master_collateral = 0

        protected_worker_assets = {
            m.node_id: m.earned_balance for m in self.members.values()
        }

        return {
            "guild_id": self.guild_id,
            "master_node_id": self.master_node_id,
            "master_collateral_forfeited": forfeited_master_capital,
            "protected_worker_assets": protected_worker_assets,
            "blast_radius_contained": True
        }


class GuildChannelManager:
    """
    Registry tracking all active guild state channels across the local daemon.
    """

    def __init__(self):
        self.guilds: Dict[str, GuildChannel] = {}

    def create_guild(self, guild_id: str, master_node_id: str, collateral: int) -> GuildChannel:
        """Instantiate a new guild sub-state channel."""
        channel = GuildChannel(guild_id, master_node_id, collateral)
        self.guilds[guild_id] = channel
        return channel

    def get_guild(self, guild_id: str) -> Optional[GuildChannel]:
        """Lookup guild channel by identifier."""
        return self.guilds.get(guild_id)


if __name__ == "__main__":
    _default_guild_manager = GuildChannelManager()

