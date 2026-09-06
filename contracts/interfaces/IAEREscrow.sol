// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IAEREscrow
 * @notice Formal interface for the AER decentralized task escrow, zero-delay settlement,
 *         optimistic timelocks, watchtower pauses, and non-punitive priority netting.
 */
interface IAEREscrow {
    enum EscrowStatus {
        UNINITIALIZED,
        ACTIVE,
        SETTLED_DIRECT,
        SETTLED_TIMELOCK,
        PAUSED,
        DISPUTED_RESOLVED
    }

    struct TaskEscrow {
        address client;
        address worker;
        address beneficiary;
        uint256 totalAmount;
        uint256 baseBounty;
        uint256 communityFee;
        uint256 delayPremium;
        uint256 timelockDuration;
        uint256 createdAt;
        uint256 pausedAt;
        uint256 pauseDuration;
        EscrowStatus status;
        bytes32 solutionHash;
    }

    event TaskCreated(
        bytes32 indexed taskId,
        address indexed client,
        address indexed worker,
        address beneficiary,
        uint256 totalAmount,
        uint256 baseBounty,
        uint256 communityFee,
        uint256 timelockDuration
    );

    event SettledDirect(
        bytes32 indexed taskId,
        address indexed worker,
        address indexed beneficiary,
        uint256 payoutAmount,
        uint256 nettingDeduction
    );

    event SettledTimelock(
        bytes32 indexed taskId,
        address indexed worker,
        uint256 payoutAmount,
        uint256 nettingDeduction
    );

    event EscrowPaused(
        bytes32 indexed taskId,
        address indexed watchtower,
        bytes32 indexed defectDigest,
        uint256 freezeDeadline
    );

    event EscrowUnpaused(bytes32 indexed taskId);

    event PriorityDebtRegistered(
        address indexed debtor,
        address indexed creditor,
        uint256 debtAmount
    );

    event PriorityDebtNetted(
        address indexed debtor,
        address indexed creditor,
        uint256 deductedAmount,
        uint256 remainingDebt
    );

    function createTask(
        bytes32 taskId,
        address worker,
        address beneficiary,
        uint256 baseBounty,
        uint256 timelockDuration
    ) external payable returns (uint256 totalRequired);

    function settleDirect(
        bytes32 taskId,
        bytes32 solutionHash,
        uint256 timestamp,
        bytes calldata beneficiarySignature
    ) external;

    function claimAfterTimelock(bytes32 taskId) external;

    function pauseEscrow(bytes32 taskId, bytes32 defectDigest) external;

    function recordOfflineIOU(
        bytes32 iouId,
        address debtor,
        address creditor,
        uint256 debtAmount,
        bytes calldata debtorSignature
    ) external;

    function getTask(bytes32 taskId) external view returns (TaskEscrow memory);

    function getPriorityDebt(address debtor) external view returns (uint256);
}
