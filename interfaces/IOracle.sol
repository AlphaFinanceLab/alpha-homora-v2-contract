pragma solidity 0.6.12;

interface IOracle {
  /// @dev Return whether the oracle supports evaluating value of the given address.
  /// @param token The ERC-20 token to check the acceptence.
  function support(address token) external view returns (bool);

  /// @dev TODO
  /// @param tokenIn TODO
  /// @param tokenOut TODO
  /// @param amountIn TODO
  function convertForLiquidation(
    address tokenIn,
    address tokenOut,
    uint amountIn
  ) external view returns (uint);

  /// @dev Return the value of the given input as ETH for collateral purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETHCollateral(address token, uint amount) external view returns (uint);

  /// @dev Return the value of the given input as ETH for borrow purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETHBorrow(address token, uint amount) external view returns (uint);
}
