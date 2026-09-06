// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IAERAccount, UserOperation} from "../interfaces/IAERAccount.sol";
import {AERCrypto} from "../libraries/AERCrypto.sol";

/**
 * @title AERAccount
 * @notice ERC-4337 compliant smart contract account decoupling persistent machine capital and state
 *         from transient physical silicon roots of trust (AER Appendix C.3).
 *         Supports cooperative dual-attestation key rotation with TPM zeroization receipts,
 *         alongside M-of-N guild witness quorum disaster recovery protected by a 7-day quarantine window.
 */
contract AERAccount is IAERAccount {
    using AERCrypto for bytes32;

    error UnauthorizedCaller();
    error InvalidSignerAddress();
    error RecoveryNotActive();
    error QuarantineNotExpired(uint256 currentTime, uint256 unlockTime);
    error InsufficientWitnessQuorum(uint256 provided, uint256 required);
    error ExecutionFailed();

    uint256 public constant RECOVERY_QUARANTINE_WINDOW = 7 days;
    uint256 public constant MIN_GUILD_QUORUM = 3;

    address public immutable entryPoint;
    address public signer;
    uint256 public nonce;

    // Emergency recovery state
    address public proposedSigner;
    uint256 public quarantineDeadline;
    bool public isRecoveryActive;

    // Authorized guild peer witnesses
    mapping(address => bool) public isAuthorizedGuildPeer;

    modifier onlySignerOrEntryPoint() {
        if (msg.sender != signer && msg.sender != entryPoint) {
            revert UnauthorizedCaller();
        }
        _;
    }

    constructor(address entryPointAddress, address initialSiliconSigner, address[] memory initialGuildPeers) {
        if (entryPointAddress == address(0) || initialSiliconSigner == address(0)) {
            revert InvalidSignerAddress();
        }
        entryPoint = entryPointAddress;
        signer = initialSiliconSigner;

        for (uint256 i = 0; i < initialGuildPeers.length; i++) {
            isAuthorizedGuildPeer[initialGuildPeers[i]] = true;
        }
    }

    receive() external payable {}

    /**
     * @notice ERC-4337 user operation validation callback.
     */
    function validateUserOp(
        UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 missingAccountFunds
    ) external override returns (uint256 validationData) {
        if (msg.sender != entryPoint) revert UnauthorizedCaller();

        bytes32 ethSignedHash = AERCrypto.toEthSignedMessageHash(userOpHash);
        address recovered = AERCrypto.recoverSigner(ethSignedHash, userOp.signature);

        if (recovered != signer) {
            return 1; // SIG_VALIDATION_FAILED
        }

        if (missingAccountFunds > 0) {
            (bool success, ) = entryPoint.call{value: missingAccountFunds}("");
            if (!success) return 1;
        }

        return 0; // SUCCESS
    }

    /**
     * @notice Executes arbitrary external calls (authorized by EntryPoint or current signer).
     */
    function execute(address dest, uint256 value, bytes calldata func)
        external
        onlySignerOrEntryPoint
        returns (bytes memory)
    {
        (bool success, bytes memory result) = dest.call{value: value}(func);
        if (!success) revert ExecutionFailed();
        return result;
    }

    /**
     * @notice Cooperative key rotation: transfers signer authority between physical TPMs.
     *         Requires simultaneous signatures from both old and new silicon plus a zeroization receipt.
     */
    function executeGracefulHandover(
        address newSigner,
        bytes calldata oldSignerSig,
        bytes calldata newSignerSig,
        bytes32 zeroizationDigest
    ) external override {
        if (newSigner == address(0)) revert InvalidSignerAddress();

        bytes32 handoverDigest = keccak256(
            abi.encode(address(this), signer, newSigner, zeroizationDigest, nonce++)
        );
        bytes32 ethSignedDigest = AERCrypto.toEthSignedMessageHash(handoverDigest);

        address recoveredOld = AERCrypto.recoverSigner(ethSignedDigest, oldSignerSig);
        address recoveredNew = AERCrypto.recoverSigner(ethSignedDigest, newSignerSig);

        if (recoveredOld != signer || recoveredNew != newSigner) {
            revert UnauthorizedCaller();
        }

        address previousSigner = signer;
        signer = newSigner;

        emit SignerHandoverExecuted(previousSigner, newSigner, zeroizationDigest, block.timestamp);
    }

    /**
     * @notice Initiates disaster recovery upon hardware chassis destruction via M-of-N guild witness quorum.
     *         Enforces a mandatory 7-day quarantine timelock during which the true owner can veto.
     */
    function initiateEmergencyRecovery(
        address newProposedSigner,
        address[] calldata guildWitnesses,
        bytes[] calldata witnessSignatures
    ) external override {
        if (newProposedSigner == address(0)) revert InvalidSignerAddress();
        if (guildWitnesses.length < MIN_GUILD_QUORUM || guildWitnesses.length != witnessSignatures.length) {
            revert InsufficientWitnessQuorum(guildWitnesses.length, MIN_GUILD_QUORUM);
        }

        bytes32 recoveryDigest = keccak256(
            abi.encode(address(this), newProposedSigner, block.chainid, nonce++)
        );
        bytes32 ethSignedDigest = AERCrypto.toEthSignedMessageHash(recoveryDigest);

        uint256 validWitnessCount = 0;
        for (uint256 i = 0; i < guildWitnesses.length; i++) {
            if (!isAuthorizedGuildPeer[guildWitnesses[i]]) continue;

            address recovered = AERCrypto.recoverSigner(ethSignedDigest, witnessSignatures[i]);
            if (recovered == guildWitnesses[i]) {
                validWitnessCount++;
            }
        }

        if (validWitnessCount < MIN_GUILD_QUORUM) {
            revert InsufficientWitnessQuorum(validWitnessCount, MIN_GUILD_QUORUM);
        }

        proposedSigner = newProposedSigner;
        quarantineDeadline = block.timestamp + RECOVERY_QUARANTINE_WINDOW;
        isRecoveryActive = true;

        emit EmergencyRecoveryInitiated(newProposedSigner, quarantineDeadline, validWitnessCount);
    }

    /**
     * @notice Cancels an ongoing emergency recovery claim (can only be executed by the true current signer).
     */
    function cancelEmergencyRecovery() external override {
        if (msg.sender != signer) revert UnauthorizedCaller();
        if (!isRecoveryActive) revert RecoveryNotActive();

        isRecoveryActive = false;
        proposedSigner = address(0);
        quarantineDeadline = 0;

        emit EmergencyRecoveryCancelled(msg.sender);
    }

    /**
     * @notice Finalizes the emergency recovery after the 7-day quarantine timelock has elapsed.
     */
    function finalizeEmergencyRecovery() external override {
        if (!isRecoveryActive) revert RecoveryNotActive();
        if (block.timestamp < quarantineDeadline) {
            revert QuarantineNotExpired(block.timestamp, quarantineDeadline);
        }

        address previousSigner = signer;
        signer = proposedSigner;

        isRecoveryActive = false;
        proposedSigner = address(0);
        quarantineDeadline = 0;

        emit EmergencyRecoveryFinalized(previousSigner, signer);
    }

    function getSigner() external view override returns (address) {
        return signer;
    }

    function getRecoveryState()
        external
        view
        override
        returns (
            address proposed,
            uint256 deadline,
            bool active
        )
    {
        return (proposedSigner, quarantineDeadline, isRecoveryActive);
    }
}
