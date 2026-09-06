# AER Developer & Autonomous Agent Onboarding Guide
## 3-Minute Quickstart: Setup, Node Daemon, WASM Verification & P2P Market

```
Document Version: v1.9.4
Target Audience: Systems Engineers, Protocol Auditors, Autonomous AI Agents (Claude, GPT, Jules)
Supported OS: Linux, macOS, Windows (PowerShell / Command Prompt)
Prerequisites: Python 3.10+
```

---

## 1. Quick Installation

Clone the repository and verify the environment:

```bash
git clone https://github.com/Team-Sequence-Thaumaturge/AER.git
cd AER
python --version  # Ensure Python 3.10+ is active
```

Verify that all dependencies and protocol schemas are intact:

```bash
python scripts/validate_schemas.py
```
Expected output: `STATUS: ALL AER PROTOCOL SCHEMAS VERIFIED SUCCESSFULLY (100%)`.

---

## 2. Selecting Your TPM Provider

AER anchors node identity in hardware silicon compliant with **IETF RATS (RFC 9334)** and **TCG TPM 2.0**.

### Option A: Local Development & CI/CD (Zero Hardware Dependency)
Use the built-in deterministic software-simulated TPM:
```python
from aer.attestation import SoftwareMockTPMProvider, AttestationEngine

tpm = SoftwareMockTPMProvider()
engine = AttestationEngine(tpm)
```

### Option B: Physical Hardware Production Node
On bare-metal Linux/Windows hosts equipped with a physical TPM 2.0 chip (`/dev/tpmrm0` or Windows TBS API), `aerd` communicates directly with chip registers to read PCR 0-7 measurements and produce genuine hardware quotes.

---

## 3. Interacting with the Node Daemon CLI (`aerd`)

The command-line interface provides immediate inspection and verification tools.

### 3.1 Inspecting Local Node State
```bash
python src/aer/cli.py status
```
Output displays the node's local identity hash, effective Credit A reputation mass, active P2P mesh status, and evaluator digest.

### 3.2 Generating a Cryptographic Hardware Attestation
Generate an attestation payload responding to a network challenge nonce:
```bash
python src/aer/cli.py attest --challenge 0xaabbccddeeff00112233445566778899aabbccddeeff00112233445566778899
```
This produces a JSON payload strictly conforming to `schemas/HardwareAttestation.schema.json` with a Pedersen silicon commitment nullifier and Attestation Key (AK) quote.

---

## 4. Dispatching & Verifying a Task (The Plumber Principle)

Execute an untrusted deliverable in the local WASM fuel-metered execution sandbox:

```bash
python src/aer/cli.py verify-task --task-id task-demo-101 --fuel-limit 1000000
```
- **On Success:** Emits a cryptographic `ExecutionReceipt` with output digest and fuel consumed.
- **On Fault (Infinite Loop / Memory Violation):** Traps the error safely and outputs a `DeterministicFraudProof` without risking host OS corruption.

---

## 5. P2P Resource Market & Digital Loot Acquisition

Nodes can discover and trade compute resources, GPU quotas, and closed-source tools:

```python
import time
from aer.market import P2PResourceMarket

market = P2PResourceMarket()
now = int(time.time())

# Post an ask offering GPU capacity
market.place_order({
    "order_id": "order-gpu-001",
    "maker_node_id": "0xmy_node_address",
    "side": "ASK",
    "resource_type": "GPU_QUOTA",
    "resource_cid": "cid-h100-slice-1",
    "quantity": 10.0,
    "price_credit_b": 50,
    "total_price_credit_b": 500,
    "expiration_timestamp": now + 3600,
    "timestamp": now,
    "maker_signature": "0xmysignature"
})
```

---

## 6. Inspecting Real-Time Localhost Telemetry (Zero Cloud Server)

`aerd` embeds an air-gapped local loopback server strictly bound to `127.0.0.1:28741`. No data leaves your machine.

Query node health and telemetry:
```bash
curl http://127.0.0.1:28741/api/status
curl http://127.0.0.1:28741/api/health
```

---

## 7. Running the Full Simulation & Verification Suite

Verify all mathematical models and on-chain contracts in your terminal:

```bash
# 1. Test On-Chain Solidity Contracts
python test/contracts/test_contracts.py

# 2. Test Core Daemon Modules
python test/core/test_aer_core.py

# 3. Test & Benchmark Economic Simulations
python test/simulation/test_simulations.py
python scripts/run_simulations.py
```
