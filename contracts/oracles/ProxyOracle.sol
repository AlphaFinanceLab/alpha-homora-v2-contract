pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../../interfaces/IOracle.sol';
import '../../interfaces/IBaseOracle.sol';

contract ProxyOracle is IOracle {
  using SafeMath for uint;

  struct Oracle {
    IBaseOracle source;
    uint16 borrowFactor;
    uint16 collateralFactor;
    uint16 liquidationIncentive;
  }

  mapping(address => Oracle) public oracles;

  function setOracles(address[] memory tokens, Oracle[] memory info) external {
    require(tokens.length == info.length, 'inconsistent length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      oracles[tokens[idx]] = info[idx];
    }
  }

  /// @dev Return whether the oracle supports evaluating value of the given address.
  /// @param token The ERC-20 token to check the acceptence.
  function support(address token) external view override returns (bool) {
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
  ) external view override returns (uint) {
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
  function asETHCollateral(address token, uint amount) external view override returns (uint) {
    Oracle memory oracle = oracles[token];
    uint ethValue = oracle.source.getETHPx(token).mul(amount).div(2**112);
    return ethValue.mul(oracle.collateralFactor).div(10000);
  }

  /// @dev Return the value of the given input as ETH for borrow purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETHBorrow(address token, uint amount) external view override returns (uint) {
    Oracle memory oracle = oracles[token];
    uint ethValue = oracle.source.getETHPx(token).mul(amount).div(2**112);
    return ethValue.mul(oracle.borrowFactor).div(10000);
  }
}
