pragma solidity 0.6.12;

interface IBank {
  event Deposit(address indexed user, uint amount, uint share);

  event Withdraw(address indexed user, uint amount, uint share);

  event Borrow(
    address indexed user,
    address indexed caller,
    address indexed token,
    uint amount,
    uint share
  );

  event Repay(
    address indexed user,
    address indexed caller,
    address indexed token,
    uint amount,
    uint share
  );

  event PutCollateral(
    address indexed user,
    address indexed caller,
    address indexed token,
    uint amount
  );

  event TakeCollateral(
    address indexed user,
    address indexed caller,
    address indexed token,
    uint amount
  );

  /// @dev Return the current executor while under execution.
  function EXECUTOR() external view returns (address);

  /// @dev Return the current target while under execution.
  function SPELL() external view returns (address);

  /// @dev Return the address of the interest bearing token of the underlying token.
  function ibTokenOf(address token) external view returns (address);

  /// @dev Deposit tokens to the vault and get back the interest-bearing tokens.
  function deposit(address token, uint amountCall) external returns (uint);

  /// @dev Withdraw tokens from the vault by burning the interest-bearing tokens.
  function withdraw(address token, uint share) external returns (uint);

  /// @dev Borrow tokens from the vault.
  function borrow(address token, uint amount) external;

  /// @dev Repays tokens to the vault.
  function repay(address token, uint amountCall) external;

  /// @dev Transmit user assets to the spell.
  function transmit(address token, uint amount) external;

  /// @dev Put more collateral for users.
  function putCollateral(address token, uint amountCall) external;

  /// @dev Take some collateral back.
  function takeCollateral(address token, uint amount) external;
}
