// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title AERCrypto
 * @notice Cryptographic helper library for signature verification, 3D Octree Merkle proofs,
 *         and EIP-712 structured data hashing within the AER protocol.
 */
library AERCrypto {
    error InvalidSignatureLength();
    error InvalidSignatureV();
    error InvalidSignatureS();
    error SignerMismatch(address recovered, address expected);
    error InvalidOctreeProof();

    /// @dev SECP256k1 curve order half-point to prevent signature malleability.
    bytes32 private constant SECP256K1_N_DIV_2 =
        0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0;

    /**
     * @notice Recovers the ECDSA signer address from a 32-byte message hash and 65-byte signature.
     * @param messageHash 32-byte digest of the signed payload.
     * @param signature 65-byte packed ECDSA signature (r, s, v).
     * @return signer Recovered Ethereum address.
     */
    function recoverSigner(bytes32 messageHash, bytes memory signature)
        internal
        pure
        returns (address signer)
    {
        if (signature.length != 65) {
            revert InvalidSignatureLength();
        }

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }

        // Enforce canonical upper bound on s to prevent signature malleability
        if (uint256(s) > uint256(SECP256K1_N_DIV_2)) {
            revert InvalidSignatureS();
        }

        // Support standard Ethereum v formats (27 or 28)
        if (v < 27) {
            v += 27;
        }
        if (v != 27 && v != 28) {
            revert InvalidSignatureV();
        }

        signer = ecrecover(messageHash, v, r, s);
        if (signer == address(0)) {
            revert SignerMismatch(address(0), address(0));
        }
    }

    /**
     * @notice Formats an Ethereum signed message hash according to EIP-191 personal_sign standard.
     * @param messageHash Raw 32-byte digest.
     * @return ethSignedHash "\x19Ethereum Signed Message:\n32" concatenated digest.
     */
    function toEthSignedMessageHash(bytes32 messageHash)
        internal
        pure
        returns (bytes32 ethSignedHash)
    {
        assembly {
            mstore(0x00, "\x19Ethereum Signed Message:\n32")
            mstore(0x1c, messageHash)
            ethSignedHash := keccak256(0x00, 0x3c)
        }
    }

    /**
     * @notice Verifies an 8-ary 3D Octree Merkle inclusion path isolating a dispute voxel.
     * @param root Expected Merkle root of the spatiotemporal octree.
     * @param leaf Hash of the specific disputed telemetry voxel.
     * @param path Array of 7 sibling octant hashes for each level from leaf to root.
     * @param octantIndices Array of octant positions (0 to 7) indicating child position at each level.
     * @return isValid True if the reconstructed root matches the expected root.
     */
    function verifyOctreeMerkleProof(
        bytes32 root,
        bytes32 leaf,
        bytes32[7][] memory path,
        uint8[] memory octantIndices
    ) internal pure returns (bool isValid) {
        if (path.length != octantIndices.length) {
            return false;
        }

        bytes32 current = leaf;
        uint256 depth = path.length;

        for (uint256 i = 0; i < depth; i++) {
            uint8 idx = octantIndices[i];
            if (idx > 7) {
                return false;
            }

            bytes32[8] memory children;
            uint256 siblingIdx = 0;

            for (uint8 j = 0; j < 8; j++) {
                if (j == idx) {
                    children[j] = current;
                } else {
                    children[j] = path[i][siblingIdx];
                    siblingIdx++;
                }
            }

            current = keccak256(abi.encodePacked(children));
        }

        return (current == root);
    }
}
