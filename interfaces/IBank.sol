pragma solidity 0.6.12;

interface IBank {
  /// The governor sets the address of the oracle smart contract.
  event SetOracle(address oracle);
  /// The governor sets the basis point fee of the bank.
  event SetFeeBps(uint feeBps);
  /// The governor adds a new bank gets added to the system.
  event AddBank(address token, address cToken, bool status);
  /// The governor updates the status of a bank.
  event UpdateStatus(address token, bool status);
  /// The governor withdraw tokens from the reserve of a bank.
  event WithdrawReserve(address user, address token, uint amount);
  /// Someone borrows tokens from a bank via a spell caller.
  event Borrow(address user, address caller, address token, uint amount, uint share);
  /// Someone repays tokens to a bank via a spell caller.
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

  /// @dev Borrow tokens from the bank.
  function borrow(address token, uint amount) external;

  /// @dev Repays tokens to the bank.
  function repay(address token, uint amountCall) external payable;

  /// @dev Transmit user assets to the spell.
  function transmit(address token, uint amount) external;

  /// @dev Put more collateral for users.
  function putCollateral(address token, uint amountCall) external;

  /// @dev Take some collateral back.
  function takeCollateral(address token, uint amount) external;
}
