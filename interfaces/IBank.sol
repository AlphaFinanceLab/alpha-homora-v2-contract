pragma solidity 0.6.12;

interface IBank {
  /// @dev Return the current executor while under execution.
  function EXECUTOR() external view returns (address);

  /// @dev Return the current target while under execution.
  function TARGET() external view returns (address);

  /// @dev Return the address of the interest bearing token of the underlying token.
  function ibTokenOf(address token) external view returns (address);

  /// @dev Deposit tokens to the vault and get back the interest-bearing tokens.
  function deposit(address token, uint amountCall) external;

  /// @dev Withdraw tokens from the vault by burning the interest-bearing tokens.
  function withdraw(address token, uint share) external;

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
