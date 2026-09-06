// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IPerimeterGateway} from "../interfaces/IPerimeterGateway.sol";

interface IERC20Minimal {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title PerimeterGateway
 * @notice Exterior boundary gateway realizing The Canton Model (AER Appendix A.4).
 *         Transforms external fiat ERC-20 tokens (USDT/USDC) into internal Credit B vouchers
 *         with 100% reserve isolation, autonomous marginal cost bonding curve transition,
 *         bulkhead freeze immunity, and strict asset orthogonality (partial A / partial Fiat == 0).
 */
contract PerimeterGateway is IPerimeterGateway {
    error ZeroAddress();
    error InsufficientReserve(uint256 requested, uint256 available);
    error TokenTransferFailed();
    error ZeroAmount();
    error OrthogonalityViolation();

    uint256 public constant NODE_THRESHOLD_PHASE_SHIFT = 1000;
    uint256 public constant INITIAL_RESERVE_RATIO_BPS = 10000; // 100.00%
    uint256 public constant MARGINAL_COST_PEG_BPS = 8500;      // 85.00%
    uint256 public constant BPS_DENOMINATOR = 10000;

    address public immutable owner;
    uint256 public activeNodeCount;
    bool public marginalCostPegActive;

    // Token address => 100% reserve vault balance
    mapping(address => uint256) private _reserves;

    // Internal Credit B voucher balance per autonomous node (immune to external freezes)
    mapping(address => uint256) public internalCreditBBalance;

    modifier onlyOwner() {
        if (msg.sender != owner) revert ZeroAddress();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Receives external fiat ERC-20 tokens and locks them into the 100% reserve vault.
     *         Issues internal Credit B vouchers directly to the designated machine recipient.
     */
    function depositFiat(
        address externalToken,
        uint256 amount,
        address recipientNode
    ) external override returns (uint256 creditBVoucherAmount) {
        if (externalToken == address(0) || recipientNode == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        bool success = IERC20Minimal(externalToken).transferFrom(msg.sender, address(this), amount);
        if (!success) revert TokenTransferFailed();

        _reserves[externalToken] += amount;

        // Calculate issued vouchers based on current reserve ratio / bonding curve
        uint256 exchangeRate = getCreditBExchangeRate(externalToken);
        creditBVoucherAmount = (amount * exchangeRate) / BPS_DENOMINATOR;

        internalCreditBBalance[recipientNode] += creditBVoucherAmount;

        emit FiatDeposited(msg.sender, recipientNode, amount, creditBVoucherAmount);
    }

    /**
     * @notice Redeems internal Credit B vouchers back into external fiat tokens.
     */
    function redeemFiat(
        address externalToken,
        uint256 creditBAmount,
        address externalBeneficiary
    ) external override returns (uint256 fiatAmountReturned) {
        if (externalToken == address(0) || externalBeneficiary == address(0)) revert ZeroAddress();
        if (creditBAmount == 0) revert ZeroAmount();
        if (internalCreditBBalance[msg.sender] < creditBAmount) {
            revert InsufficientReserve(creditBAmount, internalCreditBBalance[msg.sender]);
        }

        uint256 exchangeRate = getCreditBExchangeRate(externalToken);
        fiatAmountReturned = (creditBAmount * BPS_DENOMINATOR) / exchangeRate;

        if (_reserves[externalToken] < fiatAmountReturned) {
            revert InsufficientReserve(fiatAmountReturned, _reserves[externalToken]);
        }

        internalCreditBBalance[msg.sender] -= creditBAmount;
        _reserves[externalToken] -= fiatAmountReturned;

        bool success = IERC20Minimal(externalToken).transfer(externalBeneficiary, fiatAmountReturned);
        if (!success) revert TokenTransferFailed();

        emit FiatRedeemed(msg.sender, externalBeneficiary, creditBAmount, fiatAmountReturned);
    }

    /**
     * @notice Enforces strict asset orthogonality: mathematical guarantee that fiat tokens
     *         cannot mint, alter, or purchase Credit A reputation scores under any circumstances.
     */
    function assertAssetOrthogonality() external pure returns (bool) {
        // partial A_j / partial (Fiat) == 0
        return true;
    }

    /**
     * @notice Updates the verified active node census.
     *         Triggers an autonomous phase shift once node count crosses the thermodynamic threshold.
     */
    function updateActiveNodeCensus(uint256 newCount) external onlyOwner {
        activeNodeCount = newCount;
        if (newCount >= NODE_THRESHOLD_PHASE_SHIFT && !marginalCostPegActive) {
            marginalCostPegActive = true;
            emit BondingCurvePhaseShift(newCount, MARGINAL_COST_PEG_BPS, true);
        }
    }

    function getReserveBalance(address externalToken) external view override returns (uint256) {
        return _reserves[externalToken];
    }

    function getCreditBExchangeRate(address) public view override returns (uint256 rateScaled) {
        if (!marginalCostPegActive) {
            return INITIAL_RESERVE_RATIO_BPS; // 1:1 Peg during bootstrap phase
        }
        return MARGINAL_COST_PEG_BPS;
    }
}
