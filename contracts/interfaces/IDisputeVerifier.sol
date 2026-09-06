// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IDisputeVerifier
 * @notice Formal interface for resolving physical robotics and software execution disputes
 *         via interactive 3D octree Merkle bisection and succinct ZK-SNARK conservation proofs.
 */
interface IDisputeVerifier {
    struct SpatiotemporalVoxel {
        int256 x;
        int256 y;
        int256 z;
        uint256 timestampFrameMs;
        uint256 frameDurationMs;
    }

    struct PhysicalDisputePayload {
        bytes32 disputeId;
        bytes32 taskId;
        address challenger;
        address defendant;
        uint8 disputeCategory;
        SpatiotemporalVoxel voxel;
        bytes32[7][] merklePath;
        uint8[] octantIndices;
        bytes32 telemetryLeafHash;
        uint256[2] a;
        uint256[2][2] b;
        uint256[2] c;
        uint256[] publicSignals;
    }

    event DisputeLodged(
        bytes32 indexed disputeId,
        bytes32 indexed taskId,
        address indexed challenger,
        address defendant,
        uint8 disputeCategory
    );

    event DisputeVoxelVerified(
        bytes32 indexed disputeId,
        bytes32 indexed leafHash,
        bool zkProofValid
    );

    function verifyAndResolveDispute(PhysicalDisputePayload calldata payload)
        external
        returns (bool disputeUpheld);

    function isDisputed(bytes32 taskId) external view returns (bool);
}
