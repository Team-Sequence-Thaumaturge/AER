// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IPerimeterGateway
 * @notice Formal interface for the exterior boundary gateway (The Canton Model).
 *         Translates external fiat ERC-20 tokens (USDT/USDC) into internal Credit B vouchers
 *         with 100% reserve vaults, autonomous marginal cost bonding curves, and bulkhead freeze immunity.
 */
interface IPerimeterGateway {
    event FiatDeposited(
        address indexed externalDepositor,
        address indexed recipientNode,
        uint256 fiatAmount,
        uint256 creditBIssued
    );

    event FiatRedeemed(
        address indexed node,
        address indexed externalBeneficiary,
        uint256 creditBBurned,
        uint256 fiatReturned
    );

    event BondingCurvePhaseShift(
        uint256 totalActiveNodes,
        uint256 reserveRatioBps,
        bool marginalCostPegActive
    );

    function depositFiat(
        address externalToken,
        uint256 amount,
        address recipientNode
    ) external returns (uint256 creditBVoucherAmount);

    function redeemFiat(
        address externalToken,
        uint256 creditBAmount,
        address externalBeneficiary
    ) external returns (uint256 fiatAmountReturned);

    function getReserveBalance(address externalToken) external view returns (uint256);

    function getCreditBExchangeRate(address externalToken) external view returns (uint256 rateScaled);
}
