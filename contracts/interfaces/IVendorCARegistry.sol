// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IVendorCARegistry
 * @notice Formal interface for decentralized semiconductor Root Certificate Authorities,
 *         open-source RISC-V roots of trust, and O(1) mathematical self-invalidation.
 */
interface IVendorCARegistry {
    enum RootCAType {
        COMMERCIAL_TEE, // Intel SGX/TDX, AMD SEV, ARM CCA, TCG TPM 2.0
        OPEN_SILICON,   // RISC-V OpenTitan, Keystone TEE
        WEB_OF_TRUST    // Decentralized multi-sig peer anchors
    }

    struct RootCA {
        bytes32 caId;
        RootCAType caType;
        string vendorName;
        bytes publicKeyModulus;   // RSA modulus N or ECC public key
        uint256 keyLengthBits;
        bytes32 crlMerkleRoot;    // RFC 5280 Certificate Revocation List Merkle root
        bool isActive;
        bool isMathematicallyRevoked;
        uint256 registeredAt;
        uint256 revokedAt;
    }

    event RootCARegistered(
        bytes32 indexed caId,
        RootCAType indexed caType,
        string vendorName,
        uint256 keyLengthBits
    );

    event RootCAMathematicallyInvalidated(
        bytes32 indexed caId,
        address indexed whistleBlower,
        uint256 factorP,
        uint256 factorQ,
        uint256 timestamp
    );

    event CRLRootUpdated(bytes32 indexed caId, bytes32 indexed newCrlRoot);

    function registerRootCA(
        bytes32 caId,
        RootCAType caType,
        string calldata vendorName,
        bytes calldata publicKeyModulus,
        uint256 keyLengthBits,
        bytes32 crlMerkleRoot
    ) external;

    function invalidateRootCAWithFactorization(
        bytes32 caId,
        uint256 factorP,
        uint256 factorQ
    ) external;

    function updateCRLRoot(bytes32 caId, bytes32 newCrlRoot) external;

    function isCAValid(bytes32 caId) external view returns (bool);

    function getRootCA(bytes32 caId) external view returns (RootCA memory);
}
