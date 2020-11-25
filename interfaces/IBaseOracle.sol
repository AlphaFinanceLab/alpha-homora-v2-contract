pragma solidity 0.6.12;

interface IBaseOracle {
  /// @dev Return the value of the given input as ETH as fair price purpose.
  /// @param token The ERC-20 token to check the value.
  /// @param amount The amount of tokens to check the value.
  function asETH(address token, uint amount) external view returns (uint);
}
