pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IOracle.sol';
import '../../interfaces/IBaseOracle.sol';

contract ProxyOracle is IOracle, Governable {
  using SafeMath for uint;

  /// The governor sets oracle information for a token.
  event SetOracle(address token, Oracle info);

  struct Oracle {
    IBaseOracle source; // The address to query price data, or zero if not supported.
    uint16 borrowFactor; // The borrow factor for this token, multiplied by 1e4.
    uint16 collateralFactor; // The collateral factor for this token, multiplied by 1e4.
    uint16 liquidationIncentive; // The liquidation incentive, multiplied by 1e4.
  }

  mapping(address => Oracle) public oracles; // Mapping from token address to oracle info.

  /// @dev Create the contract and initialize the first governor.
  constructor() public {
    Governable.initialize();
  }

  /// @dev Set oracle information for the given list of token addresses.
  /// @param tokens The list of tokens addresses to set oracle data.
  /// @param info The information corresponding to each token.
  function setOracles(address[] memory tokens, Oracle[] memory info) external onlyGov {
    require(tokens.length == info.length, 'inconsistent length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      require(info[idx].borrowFactor >= 10000, 'borrow factor must be at least 100%');
      require(info[idx].collateralFactor <= 10000, 'collateral factor must be at most 100%');
      require(info[idx].liquidationIncentive >= 10000, 'incentive must be at least 100%');
      require(info[idx].liquidationIncentive <= 20000, 'incentive must be at most 200%');
      oracles[tokens[idx]] = info[idx];
      emit SetOracle(tokens[idx], info[idx]);
    }
  }

  /// @dev Return whether the oracle supports evaluating value of the given address.
  /// @param token The ERC-20 token to check the acceptence.
  function support(address token) external override view returns (bool) {
    return address(oracles[token].source) != address(0);
  }

  /// @dev Return the amount of token out as liquidation reward for liquidating token in.
  /// @param tokenIn The token that gets liquidated.
  /// @param tokenOut The token to pay as reward.
  /// @param amountIn The amount of liquidating tokens.
  function convertForLiquidation(
    address tokenIn,
    address tokenOut,
    uint amountIn
  ) external override view returns (uint) {
    Oracle memory oracleIn = oracles[tokenIn];
    Oracle memory oracleOut = oracles[tokenOut];
    uint pxIn = oracleIn.source.getETHPx(tokenIn);
    uint pxOut = oracleOut.source.getETHPx(tokenOut);
    return
      amountIn
        .mul(pxIn)
        .div(pxOut)
        .mul(oracleIn.liquidationIncentive)
        .mul(oracleOut.liquidationIncentive)
        .div(10000 * 10000);
  }

  /// @dev Return the value of the given input as ETH for collateral purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETHCollateral(address token, uint amount) external override view returns (uint) {
    Oracle memory oracle = oracles[token];
    uint ethValue = oracle.source.getETHPx(token).mul(amount).div(2**112);
    return ethValue.mul(oracle.collateralFactor).div(10000);
  }

  /// @dev Return the value of the given input as ETH for borrow purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETHBorrow(address token, uint amount) external override view returns (uint) {
    Oracle memory oracle = oracles[token];
    uint ethValue = oracle.source.getETHPx(token).mul(amount).div(2**112);
    return ethValue.mul(oracle.borrowFactor).div(10000);
  }
}
