pragma solidity 0.6.12;

interface IBank {
  /// @dev Borrow tokens from the vault.
  function borrow(address token, uint amount) external;

  /// @dev Repays tokens to the vault.
  function repay(address token, uint amountCall) external;

  /// @dev Transmit user assets to the goblin.
  function transmit(address token, uint amount) external;

  /// @dev Put more collateral for users.
  function putCollateral(address token, uint amountCall) external;

  /// @dev Take some collateral back.
  function takeCollateral(address token, uint amount) external;
}
