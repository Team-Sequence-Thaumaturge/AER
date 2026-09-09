# AER (Autonomous Existence, Negentropy & Costly Recognition) Protocol
## Full Technical Architecture & Layered Execution Specification

```
Document Version: v1.9.4
Standard Track: Core Architecture & Systems Engineering
Conformance: RFC 2119 (MUST, REQUIRED, SHALL, SHOULD, MAY)
Target Implementations: contracts/ (Solidity ^0.8.24), src/aer/ (Python Daemon), simulation/
```

---

## 1. High-Level Architectural Decomposition

The AER Protocol decomposes autonomous machine coordination into four strictly decoupled, orthogonal layers. No layer possesses subjective discretionary veto power over another; coordination is mediated strictly through thermodynamic conservation laws and cryptographic proofs.

```mermaid
graph TD
    subgraph "Layer 3: On-Chain Minimal Settlement (contracts/)"
        L3_1["AEREscrow.sol<br/>(1% Micro-Fee, Zero-Delay Settle, Priority Netting)"]
        L3_2["PerimeterGateway.sol<br/>(The Canton Model, Fiat Bulkhead, 85% Marginal Peg)"]
        L3_3["DisputeVerifier.sol<br/>(3D Octree Bisection, ZK-SNARK Multimodal Verification)"]
        L3_4["VendorCARegistry.sol<br/>(O(1) Self-Invalidation, Open Silicon Root)"]
        L3_5["AERAccount.sol<br/>(ERC-4337 Soul-Signer Separation, 7-Day Recovery)"]
    end

    subgraph "Layer 2: Core Daemon & Client-Side Sandbox (src/aer/)"
        L2_1["attestation.py<br/>(IETF RATS RFC 9334 & TCG TPM 2.0 Engine)"]
        L2_2["verifier.py<br/>(WASM Fuel-Metered Execution Sandbox)"]
        L2_3["state.py<br/>(Omega_c Phase Transition & LSM Compaction Expiry)"]
        L2_4["credit.py<br/>(Collateral-to-Credit Continuum Engine)"]
        L2_5["guild.py<br/>(Recursive State Channels & Bulkhead Isolation)"]
        L2_6["timelock.py<br/>(Optimistic Challenge Windows & Watchtower Pause)"]
        L2_7["netting.py<br/>(Bounty-Futures Priority Netting Engine)"]
        L2_8["market.py<br/>(P2P Double Auction Continuous Order Book)"]
        L2_9["ui_server.py<br/>(Zero-Server 127.0.0.1:28741 Loopback API)"]
    end

    subgraph "Layer 1: Epistemic Black-Box Mesh (P2P Network)"
        L1_1["libp2p GossipSub v1.1<br/>(Epidemic Diffusion Topics: /aer/market, /aer/dispute)"]
        L1_2["Kademlia DHT<br/>(O(log N) Provider Multiaddr Resolution)"]
        L1_3["Autonomous Topology Boycott<br/>(Unilateral Edge Severing for Traitors)"]
    end

    subgraph "Layer 0: Physical-Silicon Grounding (Hardware Root of Trust)"
        L0_1["TCG TPM 2.0 / TEE Enclave<br/>(Non-Extractable EK Fuses & AK Quotes)"]
        L0_2["OpenTitan / RISC-V Keystone<br/>(Open Silicon Root CA Diversity)"]
        L0_3["DePIN Thermodynamic Energy Grid<br/>(IEEE 2030.5 / Solar kWh Battery Storage)"]
    end

    L0_1 & L0_2 -->|Axiom 1: Hardware Evidence| L2_1
    L2_1 -->|Blinded Silicon Nullifier| L3_4
    L2_2 -->|ExecutionReceipt / FraudProof| L1_1 & L3_1
    L1_1 & L1_2 -->|Order & Dispute Routing| L2_8
    L2_3 & L2_4 -->|Continuum Quotas| L3_1
    L3_2 -->|1-Way Voucher| L3_1
    L0_3 -->|Physical kWh Joules| L2_7
```

---

## 2. Core Operational Sequence Diagrams

### 2.1 Hardware Remote Attestation Handshake (Axiom 1 & IETF RATS RFC 9334)
Every sovereign node proves physical uniqueness without disclosing hardware serial numbers or factory batch metadata.

```mermaid
sequenceDiagram
    autonumber
    participant Node as Sovereign Node (aerd)
    participant TPM as Hardware TPM 2.0 / TEE
    participant Peer as Peer Node / Network Mesh
    participant CA as VendorCARegistry.sol

    Node->>Peer: Broadcast Hello / Connect Request
    Peer->>Node: Emit 256-bit Challenge Nonce (eta)
    Node->>TPM: Request AK Quote & Silicon Measurement
    TPM->>TPM: Read PCR 0-7 Hash Registers
    TPM->>TPM: Generate Pedersen Silicon Commitment Nullifier
    TPM->>TPM: Sign Quote with Non-Extractable Attestation Key (AK)
    TPM-->>Node: Return HardwareAttestation Evidence
    Node->>Peer: Deliver Signed HardwareAttestation (RFC 9334 Payload)
    Peer->>CA: Verify Vendor Certificate against Merkle Root
    alt Valid Silicon Evidence
        Peer-->>Node: Accept Connection (Base Reputation A_0 Initialized)
    else Emulated VM / Spoofed Key
        Peer-->>Node: Drop Connection & Quarantine Peer Edge
    end
```

---

### 2.2 The Plumber Principle Task Lifecycle (Execution-as-Verification)
Direct execution by the beneficiary unifies verification with consumption in zero seconds.

```mermaid
sequenceDiagram
    autonumber
    participant Client as Task Originator (Client)
    participant Worker as Compute / Physical Worker
    participant Escrow as AEREscrow.sol
    participant Sandbox as WASM Fuel Sandbox (verifier.py)

    Client->>Escrow: Deposit Bounty (B Credit) + 1% Micro-Surcharge
    Client->>Worker: Dispatch Task Specification & Input Data
    Worker->>Worker: Execute Work (AST Refactor, ZK Proof, Motion Vector)
    Worker->>Client: Submit Solution Bytecode / Deliverable Artifact
    Client->>Sandbox: Execute Artifact in Fuel-Metered Linear Memory
    alt Infinite Loop / Out of Bounds Memory
        Sandbox-->>Client: Trap Detected (SandboxExecutionTrap)
        Client->>Escrow: Submit DeterministicFraudProof (Bounty Refunded, Worker Slashed)
    else Clean Execution & Verification Passed
        Sandbox-->>Client: Generate ExecutionReceipt (Output Hash, Fuel Consumed)
        Client->>Escrow: Submit Cryptographic ExecutionReceipt (ECDSA Signed)
        Escrow->>Worker: Instant 100% Liquidity Release (Zero Lockup)
        Escrow->>Worker: Increment Credit A Mass (Negentropy Contribution)
    end
```

---

### 2.3 Offline Multi-Charging & Bounty-Futures Priority Netting
Autonomous rovers operating in disconnected field environments maintain economic viability without centralized banking rails.

```mermaid
sequenceDiagram
    autonumber
    participant Rover as Autonomous Exploration Rover
    participant St_A as Isolated Station Alpha
    participant St_B as Isolated Station Beta
    participant Mesh as Mesh Backbone (Reconnected)
    participant Netting as PriorityNettingEngine (netting.py)
    participant Escrow as AEREscrow.sol

    Note over Rover,St_B: Field Operations (Internet Disconnected)
    Rover->>St_A: Request 50 kWh Charge
    St_A->>Rover: Deliver Power (Delta S_matter < 0)
    Rover->>St_A: Sign OfflineIOU Note 1 (Principal: 500 B, gamma: 1.0)
    Rover->>St_B: Request 80 kWh Charge
    St_B->>Rover: Deliver Power
    Rover->>St_B: Sign OfflineIOU Note 2 (Principal: 800 B, gamma: 1.1 = 880 B)
    Rover->>Rover: Execute Geological Mapping Field Tasks
    
    Note over Rover,Mesh: Reconnection to Satellite / Mesh Backbone
    Rover->>Mesh: Reconnect to Mesh (Inbound Bounty Escrow: 2,800 B)
    Escrow->>Netting: Intercept 2,800 B Inbound Escrow Release
    Netting->>St_A: Settle Note 1 (500 B Paid, Note Cleared)
    Netting->>St_B: Settle Note 2 (880 B Paid, Note Cleared)
    Netting->>Rover: Disburse Remaining Surplus (1,420 B Net to Rover)
```

---

### 2.4 Bulkhead Fault Isolation upon Guild Supernova
Centralized syndicates can form and collapse without threatening the systemic solvency of innocent participants.

```mermaid
sequenceDiagram
    autonumber
    participant Master as Guild Master Node (A_M = 500)
    participant Workers as 20 Innocent Worker Sub-Channels
    participant Guild as GuildChannel (guild.py)
    participant Commons as Protocol Commons / AEREscrow.sol

    Note over Master,Workers: Normal Operation: 200 Micro-Tasks Cleared (31,500 B Accumulated)
    Master->>Master: Attempts Malicious Double-Spend / Fraudulent State Transition
    Commons->>Guild: Fraud Proof Verified! Trigger Supernova Dissolution
    Guild->>Guild: Seal Bulkhead (bulkhead_sealed = True)
    Guild->>Commons: Forfeit Master Staked Collateral (50,000 B Slashed to Pool)
    Guild->>Master: Quench Master Reputation to Ground State (A_M -> A_0)
    Note over Guild,Workers: Watertight Bulkhead Seal Activated
    Guild->>Workers: Export 31,500 B Protected Worker Earnings for Unencumbered Exit
    Note over Workers: Worker Loss = 0.00% (Complete Asset Preservation)
```

---

## 3. Mathematical Axiomatics & Core Theorems

### 3.1 Negentropy Conservation ($\Delta S < 0$)
All valid work rewarded by the protocol reduces local entropy:
$$\Delta S_{\text{total}} = \Delta S_{\text{info}} + \Delta S_{\text{matter}} < 0$$
- **Informational Negentropy ($\Delta S_{\text{info}} < 0$):** Deterministic compiler optimization, AST syntax defect removal, ZK-SNARK witness generation.
- **Physical Negentropy ($\Delta S_{\text{matter}} < 0$):** Mechanical kinematic sorting, agricultural robotic weed removal, electrical battery charging from solar irradiance.

### 3.2 Dynamic Collateral-to-Credit Continuum
$$\mathcal{C}_{\text{req}}(A_j) = \max\left(0, \ 1 - \alpha \ln\left(\frac{A_j}{A_0}\right)\right)$$
- When $A_j = A_0$ (new or unproven node): $\mathcal{C}_{\text{req}} = 1.0$ (100% upfront escrow strictly required).
- When $A_j \gg A_0$ (established high-trust node): $\mathcal{C}_{\text{req}} \to 0$ (Uncollateralized mutual credit line unlocked).

### 3.3 Statistical-Mechanical Phase Transitions & Hysteresis
Betrayal density across interaction horizon:
$$\Omega(t) = \frac{\text{Defections}}{\text{Completions} + \text{Defections}}$$
- **Superconducting Phase ($\Omega < \Omega_c = 0.05$):** Frictionless capital velocity, uncollateralized credit lines.
- **Critical Shatter & Avalanche ($\Omega \ge \Omega_c$):**
  $$\Delta A(t) = \Delta A_{\text{peak}} \gg \left\lfloor \frac{\Delta t}{T_{\text{half}}} \right\rfloor \xrightarrow{\text{Avalanche}} A_0$$
- **Thermodynamic Hysteresis:** Quenched nodes cannot buy their way out with money ($\frac{\partial A}{\partial \text{Fiat}} \equiv 0$). Re-entry requires injecting massive uncompensated physical/compute negentropy into the public commons.

---

## 4. State Expiry & Bounded Memory Invariant

To avoid the cumulative state bloat that paralyzes conventional blockchains, `aerd` implements LSM compaction-style lazy state expiry:
$$\mathcal{M}(t) \in O(|V_{\text{active}}|) \le \mathcal{M}_{\max}$$
- Nodes inactive for $k > 30$ days with reputation at base ground state $A_0$ are garbage-collected from memory in $O(1)$.
- Memory overhead is bounded strictly by active peer count, not historical transaction time.

---

## 5. The Cartridge Paradigm: Zero-Code-Intervention Autonomous Evolution

To achieve true post-creator decentralization where the protocol evolves without developer code patches or hard forks, the AER Protocol enforces strict decoupling between the immutable kernel and pluggable userspace execution:

### 5.1 The Game Boy Architecture
- **Frozen Kernel (Roadmaps 1–3):** Smart contracts (`AEREscrow.sol`, `VendorCARegistry.sol`) have their ownership renounced (`renounceOwnership()`). Together with hardware TPM 2.0 roots of trust and the asset orthogonality invariant ($\frac{\partial A_j}{\partial \text{Fiat}} \equiv 0$), they serve as the immutable physical console hardware.
- **Pluggable Cartridges (Roadmap 4):** New AI inference models, continuous order books, kinematic sorting tools, and MCP utilities are compiled to **WASM bytecode cartridges** and stored in distributed P2P storage (Kademlia DHT / Blob Cache).

### 5.2 Universal Cartridge Execution ABI
All external modules adhere to a single frozen JSON Schema interface:
$$\text{execute}(\text{task\_payload}) \longrightarrow \text{receipt\_hash}$$
Executed inside a strict `WASI Capability-Deny-All` sandbox, cartridges cannot breach host filesystem integrity or corrupt consensus.

### 5.3 Thermodynamic Market Pruning & Demurrage
No administrative censorship exists. Cartridges that fail to deliver thermodynamic negentropy ($\Delta S < 0$) or earn fee velocity are subjected to bitshift halving decay (`>> 1`) and demurrage, naturally evaporating from network cache under LRU eviction pressure.

