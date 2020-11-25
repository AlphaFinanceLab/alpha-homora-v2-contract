pragma solidity 0.6.12;

import '../../interfaces/IOracle.sol';
import '../../interfaces/IBaseOracle.sol';

contract ProxyOracle is IOracle {
  /// @dev Return whether the oracle supports evaluating value of the given address.
  /// @param token The ERC-20 token to check the acceptence.
  function support(address token) external view override returns (bool) {
    return true;
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
    return 0;
  }

  /// @dev Return the value of the given input as ETH for collateral purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETHCollateral(address token, uint amount) external view override returns (uint) {
    return 0;
  }

  /// @dev Return the value of the given input as ETH for borrow purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETHBorrow(address token, uint amount) external view override returns (uint) {
    return 0;
  }
}
