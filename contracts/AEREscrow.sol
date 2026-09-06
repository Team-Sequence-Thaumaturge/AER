// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IAEREscrow} from "./interfaces/IAEREscrow.sol";
import {AERCrypto} from "./libraries/AERCrypto.sol";

/**
 * @title AEREscrow
 * @notice Production-grade on-chain task escrow realizing the Plumber Principle (zero-delay settlement),
 *         1% public entropy reduction surcharge, variable optimistic timelocks, watchtower pauses,
 *         and non-punitive priority netting (AER Section 4.4.3 & Section 5).
 */
contract AEREscrow is IAEREscrow {
    using AERCrypto for bytes32;

    error TaskAlreadyExists(bytes32 taskId);
    error TaskNotFound(bytes32 taskId);
    error TaskNotActive(bytes32 taskId, EscrowStatus status);
    error InsufficientDeposit(uint256 provided, uint256 required);
    error TimelockNotExpired(uint256 currentTime, uint256 unlockTime);
    error UnauthorizedWatchtower(address caller);
    error TaskAlreadyPaused(bytes32 taskId);
    error TaskNotPaused(bytes32 taskId);
    error ZeroAddress();
    error TransferFailed();

    uint256 public constant COMMUNITY_FEE_BPS = 100; // 1.00% = 100 / 10,000
    uint256 public constant BPS_DENOMINATOR = 10000;
    uint256 public constant BASE_TIMELOCK = 24 hours;
    uint256 public constant MAX_TIMELOCK = 30 days;
    uint256 public constant WATCHTOWER_FREEZE_WINDOW = 72 hours;

    address public immutable communityPool;
    address public disputeVerifier;

    struct PriorityDebtRecord {
        address creditor;
        uint256 amount;
    }

    mapping(bytes32 => TaskEscrow) private _tasks;
    mapping(address => PriorityDebtRecord[]) private _debtLedger;
    mapping(address => uint256) private _totalPriorityDebt;
    mapping(address => bool) public isAuthorizedWatchtower;

    modifier onlyActive(bytes32 taskId) {
        TaskEscrow storage task = _tasks[taskId];
        if (task.status != EscrowStatus.ACTIVE) {
            revert TaskNotActive(taskId, task.status);
        }
        _;
    }

    constructor(address communityPoolAddress) {
        if (communityPoolAddress == address(0)) revert ZeroAddress();
        communityPool = communityPoolAddress;
        isAuthorizedWatchtower[msg.sender] = true;
    }

    function setDisputeVerifier(address verifierAddress) external {
        if (disputeVerifier == address(0) || isAuthorizedWatchtower[msg.sender]) {
            disputeVerifier = verifierAddress;
        }
    }

    function setWatchtower(address watchtower, bool authorized) external {
        if (!isAuthorizedWatchtower[msg.sender]) revert UnauthorizedWatchtower(msg.sender);
        isAuthorizedWatchtower[watchtower] = authorized;
    }

    /**
     * @notice Calculates the required delay liquidity premium for extended timelocks.
     *         B_total = B_base * (1 + kappa * ln(T / 24h))
     *         Approximated linearly in basis points: +10% per 72h beyond 24h.
     */
    function calculateDelayPremium(uint256 baseBounty, uint256 timelockDuration)
        public
        pure
        returns (uint256)
    {
        if (timelockDuration <= BASE_TIMELOCK) {
            return 0;
        }
        uint256 excessSeconds = timelockDuration - BASE_TIMELOCK;
        // 1000 bps (10%) per 72 hours of extra waiting time
        return (baseBounty * excessSeconds * 1000) / (72 hours * BPS_DENOMINATOR);
    }

    /**
     * @notice Creates an on-chain task escrow with automatic 1% fee allocation and delay premium.
     */
    function createTask(
        bytes32 taskId,
        address worker,
        address beneficiary,
        uint256 baseBounty,
        uint256 timelockDuration
    ) external payable override returns (uint256 totalRequired) {
        if (_tasks[taskId].client != address(0)) revert TaskAlreadyExists(taskId);
        if (worker == address(0) || beneficiary == address(0)) revert ZeroAddress();
        if (timelockDuration < 1 hours || timelockDuration > MAX_TIMELOCK) {
            timelockDuration = BASE_TIMELOCK;
        }

        uint256 communityFee = (baseBounty * COMMUNITY_FEE_BPS) / BPS_DENOMINATOR;
        uint256 delayPremium = calculateDelayPremium(baseBounty, timelockDuration);
        totalRequired = baseBounty + communityFee + delayPremium;

        if (msg.value < totalRequired) {
            revert InsufficientDeposit(msg.value, totalRequired);
        }

        // Allocate 1% micro-surcharge immediately to the Community Entropy Reduction Pool
        (bool feeSent, ) = communityPool.call{value: communityFee}("");
        if (!feeSent) revert TransferFailed();

        _tasks[taskId] = TaskEscrow({
            client: msg.sender,
            worker: worker,
            beneficiary: beneficiary,
            totalAmount: totalRequired,
            baseBounty: baseBounty,
            communityFee: communityFee,
            delayPremium: delayPremium,
            timelockDuration: timelockDuration,
            createdAt: block.timestamp,
            pausedAt: 0,
            pauseDuration: 0,
            status: EscrowStatus.ACTIVE,
            solutionHash: bytes32(0)
        });

        emit TaskCreated(
            taskId,
            msg.sender,
            worker,
            beneficiary,
            totalRequired,
            baseBounty,
            communityFee,
            timelockDuration
        );
    }

    /**
     * @notice Realizes the Plumber Principle: settlement is 100% verified and paid out
     *         immediately (zero lockup) upon valid beneficiary ECDSA signature.
     */
    function settleDirect(
        bytes32 taskId,
        bytes32 solutionHash,
        uint256 timestamp,
        bytes calldata beneficiarySignature
    ) external override onlyActive(taskId) {
        TaskEscrow storage task = _tasks[taskId];

        // Construct canonical ExecutionReceipt digest
        bytes32 receiptHash = keccak256(
            abi.encode(
                taskId,
                task.worker,
                task.beneficiary,
                solutionHash,
                timestamp,
                task.baseBounty
            )
        );

        bytes32 ethSignedDigest = AERCrypto.toEthSignedMessageHash(receiptHash);
        address recoveredSigner = AERCrypto.recoverSigner(ethSignedDigest, beneficiarySignature);

        if (recoveredSigner != task.beneficiary) {
            revert AERCrypto.SignerMismatch(recoveredSigner, task.beneficiary);
        }

        task.status = EscrowStatus.SETTLED_DIRECT;
        task.solutionHash = solutionHash;

        uint256 distributable = task.baseBounty + task.delayPremium;
        uint256 nettedDebt = _executePriorityNetting(task.worker, distributable);
        uint256 netPayout = distributable - nettedDebt;

        if (netPayout > 0) {
            (bool success, ) = task.worker.call{value: netPayout}("");
            if (!success) revert TransferFailed();
        }

        emit SettledDirect(taskId, task.worker, task.beneficiary, netPayout, nettedDebt);
    }

    /**
     * @notice Claims bounty after optimistic timelock expiration if no defect proof was lodged.
     */
    function claimAfterTimelock(bytes32 taskId) external override onlyActive(taskId) {
        TaskEscrow storage task = _tasks[taskId];
        uint256 effectiveUnlockTime = task.createdAt + task.timelockDuration + task.pauseDuration;

        if (block.timestamp < effectiveUnlockTime) {
            revert TimelockNotExpired(block.timestamp, effectiveUnlockTime);
        }

        task.status = EscrowStatus.SETTLED_TIMELOCK;

        uint256 distributable = task.baseBounty + task.delayPremium;
        uint256 nettedDebt = _executePriorityNetting(task.worker, distributable);
        uint256 netPayout = distributable - nettedDebt;

        if (netPayout > 0) {
            (bool success, ) = task.worker.call{value: netPayout}("");
            if (!success) revert TransferFailed();
        }

        emit SettledTimelock(taskId, task.worker, netPayout, nettedDebt);
    }

    /**
     * @notice Watchtower freeze mechanism: pauses countdown upon detecting malformed payloads or crashes.
     */
    function pauseEscrow(bytes32 taskId, bytes32 defectDigest) external override {
        TaskEscrow storage task = _tasks[taskId];
        if (task.status != EscrowStatus.ACTIVE) revert TaskNotActive(taskId, task.status);

        if (
            msg.sender != task.client &&
            msg.sender != disputeVerifier &&
            !isAuthorizedWatchtower[msg.sender]
        ) {
            revert UnauthorizedWatchtower(msg.sender);
        }

        task.status = EscrowStatus.PAUSED;
        task.pausedAt = block.timestamp;

        emit EscrowPaused(
            taskId,
            msg.sender,
            defectDigest,
            block.timestamp + WATCHTOWER_FREEZE_WINDOW
        );
    }

    /**
     * @notice Resumes a paused escrow after dispute inspection.
     */
    function unpauseEscrow(bytes32 taskId) external {
        TaskEscrow storage task = _tasks[taskId];
        if (task.status != EscrowStatus.PAUSED) revert TaskNotPaused(taskId);
        if (!isAuthorizedWatchtower[msg.sender] && msg.sender != task.client) {
            revert UnauthorizedWatchtower(msg.sender);
        }

        task.pauseDuration += (block.timestamp - task.pausedAt);
        task.status = EscrowStatus.ACTIVE;
        task.pausedAt = 0;

        emit EscrowUnpaused(taskId);
    }

    /**
     * @notice Enforces non-punitive mutual credit: registers offline IOU debt on ledger.
     */
    function recordOfflineIOU(
        bytes32 iouId,
        address debtor,
        address creditor,
        uint256 debtAmount,
        bytes calldata debtorSignature
    ) external override {
        bytes32 iouDigest = keccak256(abi.encode(iouId, debtor, creditor, debtAmount));
        bytes32 ethSignedDigest = AERCrypto.toEthSignedMessageHash(iouDigest);
        address recoveredSigner = AERCrypto.recoverSigner(ethSignedDigest, debtorSignature);

        if (recoveredSigner != debtor) {
            revert AERCrypto.SignerMismatch(recoveredSigner, debtor);
        }

        _debtLedger[debtor].push(PriorityDebtRecord({creditor: creditor, amount: debtAmount}));
        _totalPriorityDebt[debtor] += debtAmount;

        emit PriorityDebtRegistered(debtor, creditor, debtAmount);
    }

    /**
     * @dev Internal routine deducting accumulated priority liabilities before dispersing revenue.
     */
    function _executePriorityNetting(address debtor, uint256 availableRevenue)
        internal
        returns (uint256 totalDeducted)
    {
        PriorityDebtRecord[] storage records = _debtLedger[debtor];
        uint256 remainingRevenue = availableRevenue;

        for (uint256 i = 0; i < records.length && remainingRevenue > 0; i++) {
            if (records[i].amount == 0) continue;

            uint256 payment = records[i].amount <= remainingRevenue
                ? records[i].amount
                : remainingRevenue;

            records[i].amount -= payment;
            remainingRevenue -= payment;
            totalDeducted += payment;

            (bool sent, ) = records[i].creditor.call{value: payment}("");
            if (!sent) revert TransferFailed();

            emit PriorityDebtNetted(debtor, records[i].creditor, payment, records[i].amount);
        }

        if (_totalPriorityDebt[debtor] >= totalDeducted) {
            _totalPriorityDebt[debtor] -= totalDeducted;
        } else {
            _totalPriorityDebt[debtor] = 0;
        }
    }

    function getTask(bytes32 taskId) external view override returns (TaskEscrow memory) {
        return _tasks[taskId];
    }

    function getPriorityDebt(address debtor) external view override returns (uint256) {
        return _totalPriorityDebt[debtor];
    }
}
