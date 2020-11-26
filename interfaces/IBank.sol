pragma solidity 0.6.12;

interface IBank {
  /// The governor sets the address of the oracle smart contract.
  event SetOracle(address oracle);
  /// The governor adds a new vault gets added to the system.
  event AddVault(address token, uint8 status, address ib, address ir);
  /// The governor updates the status of a vault.
  event UpdateStatus(address token, uint8 status);
  /// The governor updates the interest rate model of a vault.
  event UpdateInterestRateModel(address token, address ir);
  /// Someone deposits tokens to a vault.
  event Deposit(address user, address token, uint amount, uint share);
  /// Someone withdraws tokens from a vault.
  event Withdraw(address user, address token, uint amount, uint share);
  /// The governor withdraw tokens from the reserve of a vault.
  event WithdrawReserve(address user, address token, uint amount);
  /// Someone borrows tokens from a vault via a spell caller.
  event Borrow(address user, address caller, address token, uint amount, uint share);
  /// Someone repays tokens to a vault via a spell caller.
  event Repay(address user, address caller, address token, uint amount, uint share);
  /// Someone puts tokens as collateral via a spell caller.
  event PutCollateral(address user, address caller, address token, uint amount);
  /// Someone takes tokens from collateral via a spell caller.
  event TakeCollateral(address user, address caller, address token, uint amount);
  /// Someone calls liquidatation on a position, paying debt and taking collateral tokens.
  event Liquidate(
    address owner,
    address liquidator,
    address debtToken,
    address collateralToken,
    uint amount,
    uint share,
    uint bounty
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
