// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @dev ERC-4337 UserOperation struct definition conforming to v0.6/v0.7 specification.
 */
struct UserOperation {
    address sender;
    uint256 nonce;
    bytes initCode;
    bytes callData;
    uint256 callGasLimit;
    uint256 verificationGasLimit;
    uint256 preVerificationGas;
    uint256 maxFeePerGas;
    uint256 maxPriorityFeePerGas;
    bytes paymasterAndData;
    bytes signature;
}

/**
 * @title IAERAccount
 * @notice ERC-4337 compliant smart account interface decoupling machine persistent state/vault
 *         from transient physical silicon roots of trust.
 */
interface IAERAccount {
    event SignerHandoverExecuted(
        address indexed oldSigner,
        address indexed newSigner,
        bytes32 zeroizationDigest,
        uint256 timestamp
    );

    event EmergencyRecoveryInitiated(
        address indexed proposedSigner,
        uint256 quarantineDeadline,
        uint256 witnessCount
    );

    event EmergencyRecoveryCancelled(address indexed currentSigner);

    event EmergencyRecoveryFinalized(address indexed previousSigner, address indexed newSigner);

    function validateUserOp(
        UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 missingAccountFunds
    ) external returns (uint256 validationData);

    function executeGracefulHandover(
        address newSigner,
        bytes calldata oldSignerSig,
        bytes calldata newSignerSig,
        bytes32 zeroizationDigest
    ) external;

    function initiateEmergencyRecovery(
        address proposedSigner,
        address[] calldata guildWitnesses,
        bytes[] calldata witnessSignatures
    ) external;

    function cancelEmergencyRecovery() external;

    function finalizeEmergencyRecovery() external;

    function getSigner() external view returns (address);

    function getRecoveryState()
        external
        view
        returns (
            address proposedSigner,
            uint256 quarantineDeadline,
            bool isRecoveryActive
        );
}
