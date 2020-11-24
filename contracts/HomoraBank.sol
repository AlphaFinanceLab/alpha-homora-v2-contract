pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/proxy/Initializable.sol';

import './IbTokenV2.sol';
import '../interfaces/IBank.sol';
import '../interfaces/IInterestRateModel.sol';
import '../interfaces/IOracle.sol';

library VaultStatus {
  enum T {
    INVALID, // The vault does not exist.
    FROZEN, // The vault is frozen for any action.
    NOMOREDEBT, // The vault does not accept more loans.
    ACTIVE // The vault is fully operational.
  }

  function valid(T status) internal pure returns (bool) {
    return status == T.FROZEN || status == T.NOMOREDEBT || status == T.ACTIVE;
  }

  function acceptDeposit(T status) internal pure returns (bool) {
    return true;
  }

  function acceptWithdraw(T status) internal pure returns (bool) {
    return true;
  }

  function acceptBorrow(T status) internal pure returns (bool) {
    return true;
  }

  function acceptRepay(T status) internal pure returns (bool) {
    return true;
  }
}

contract HomoraCaster {
  /// @dev Call to the target using the given data.
  /// @param target The address target to call.
  /// @param data The data using in the call.
  function cast(address target, bytes memory data) public payable {
    (bool ok, ) = target.call{value: msg.value}(data);
    require(ok, 'bad cast call');
  }
}

contract HomoraBank is Initializable, IBank {
  using SafeMath for uint;
  using SafeERC20 for IERC20;
  using VaultStatus for VaultStatus.T;

  uint public constant MAX_ASSET_COUNT = 10;
  uint public constant MAX_DEBT_COUNT = 10;

  uint private constant _NOT_ENTERED = 1;
  uint private constant _ENTERED = 2;
  address private constant _NO_ADDRESS = address(1);

  uint public _GENERAL_LOCK;
  uint public _IN_EXEC_LOCK;
  address public _EXECUTOR;
  address public _TARGET;

  address public caster;
  address public governor;
  address public pendingGovernor;
  IOracle public oracle;

  struct Vault {
    VaultStatus.T status;
    IbTokenV2 ib;
    IInterestRateModel ir;
    uint lastAccrueTime;
    uint reserve;
    uint totalValue;
    uint totalDebt;
    uint totalDebtShare;
  }

  mapping(address => Vault) public vaults;
  mapping(address => address[]) public assetsOf;
  mapping(address => mapping(address => uint)) public assetAmountOf;
  mapping(address => address[]) public debtsOf;
  mapping(address => mapping(address => uint)) public debtShareOf;

  /// @dev Reentrancy lock guard.
  modifier lock() {
    require(_GENERAL_LOCK == _NOT_ENTERED, 'general lock');
    _GENERAL_LOCK = _ENTERED;
    _;
    _GENERAL_LOCK = _NOT_ENTERED;
  }

  /// @dev Ensure that the function is called from within the execution scope.
  modifier inExec() {
    require(_EXECUTOR != _NO_ADDRESS, 'not within execution');
    require(_TARGET == msg.sender, 'not from target');
    require(_IN_EXEC_LOCK == _NOT_ENTERED, 'in exec lock');
    _IN_EXEC_LOCK = _ENTERED;
    _;
    _IN_EXEC_LOCK = _NOT_ENTERED;
  }

  /// @dev Ensure that the interest rate of the given token vault is accrued.
  modifier poke(address token) {
    accrue(token);
    _;
  }

  /// @dev Initialize the bank smart contract, using msg.sender as the first governor.
  /// @param _oracle The oracle smart contract address.
  function initialize(IOracle _oracle) public initializer {
    _GENERAL_LOCK = _NOT_ENTERED;
    _IN_EXEC_LOCK = _NOT_ENTERED;
    _EXECUTOR = _NO_ADDRESS;
    _TARGET = _NO_ADDRESS;
    caster = address(new HomoraCaster());
    governor = msg.sender;
    pendingGovernor = address(0);
    oracle = _oracle;
  }

  /// @dev Return the length of the assets of the given user.
  function assetsLengthOf(address user) public view returns (uint) {
    return assetsOf[user].length;
  }

  /// @dev Return the length of the debts of the given user.
  function debtsLengthOf(address user) public view returns (uint) {
    return debtsOf[user].length;
  }

  /// @dev Return the interest-bearing token of the given underlying token.
  function ibTokenOf(address token) public view override returns (address) {
    return address(vaults[token].ib);
  }

  /// @dev Trigger interest accrual for the given vault.
  /// @param token The vault token to trigger the interest accrual.
  function accrue(address token) public {
    Vault storage v = vaults[token];
    require(v.status.valid(), 'vault does not exist');
    if (now > v.lastAccrueTime) {
      uint timeElapsed = now - v.lastAccrueTime;
      uint rate = v.ir.getBorrowRate(token, v.totalValue, v.totalDebt, v.reserve);
      uint interest = v.totalDebt.mul(rate).mul(timeElapsed).div(1000 * 365 days);
      uint reserve = interest / 10; // 10% of fee to reserve
      v.totalDebt = v.totalDebt.add(interest);
      v.reserve = v.reserve.add(reserve);
      v.totalValue = v.totalValue.add(interest.sub(reserve));
      v.lastAccrueTime = now;
    }
  }

  /// @dev Convenient function to trigger interest accrual for the list of vaults.
  /// @param tokens The list of vaults to trigger interest accrual.
  function accrueAll(address[] memory tokens) public {
    for (uint idx = 0; idx < tokens.length; idx++) {
      accrue(tokens[idx]);
    }
  }

  /// @dev Return the total collateral value of the given user in ETH.
  /// @param user The user to query for the collateral value.
  function getCollateralETHValue(address user) public view returns (uint) {
    uint value = 0;
    uint length = assetsOf[user].length;
    for (uint idx = 0; idx < length; idx++) {
      address token = assetsOf[user][idx];
      value = value.add(oracle.asETHCollateral(token, assetAmountOf[user][token]));
    }
    return value;
  }

  /// @dev Return the total borrow value of the given user in ETH.
  /// @param user The user to query for the borrow value.
  function getBorrowETHValue(address user) public view returns (uint) {
    uint value = 0;
    uint length = debtsOf[user].length;
    for (uint idx = 0; idx < length; idx++) {
      address token = debtsOf[user][idx];
      uint share = debtShareOf[user][token];
      Vault storage v = vaults[token];
      uint debt = share.mul(v.totalDebt).div(v.totalDebtShare);
      value = value.add(oracle.asETHBorrow(token, debt));
    }
    return value;
  }

  /// @dev Set the pending governor, which will be the governor once accepted.
  /// @param _pendingGovernor The address to become the pending governor.
  function setPendingGovernor(address _pendingGovernor) public {
    require(msg.sender == governor, 'not the governor');
    pendingGovernor = _pendingGovernor;
  }

  /// @dev Accept to become the new governor. Must be called by the pending governor.
  function acceptGovernor() public {
    require(msg.sender == pendingGovernor, 'not the pending governor');
    pendingGovernor = address(0);
    governor = msg.sender;
  }

  /// @dev Add a new vault to the bank.
  /// @param token The underlying token for the vault.
  /// @param status The initial vault status.
  /// @param ir The initial interest rate model.
  function setVaultStatus(
    address token,
    VaultStatus.T status,
    IInterestRateModel ir
  ) public {
    require(msg.sender == governor, 'not the governor');
    Vault storage v = vaults[token];
    require(!v.status.valid(), 'vault already exists');
    v.ib = new IbTokenV2(token);
    v.ir = ir;
    v.lastAccrueTime = now;
  }

  /// @dev Set vault status for the given set of vaults. Create new ib tokens for new vaults.
  /// @param tokens The set of vault tokens to update the vault status.
  /// @param status The new vault status to set.
  function setVaultStatus(address[] memory tokens, VaultStatus.T status) public {
    require(msg.sender == governor, 'not the governor');
    require(status.valid(), 'invalid status');
    for (uint idx = 0; idx < tokens.length; idx++) {
      address token = tokens[idx];
      Vault storage v = vaults[token];
      require(v.status.valid(), 'vault does not exist');
      v.status = status;
    }
  }

  /// @dev Deposit tokens to the vault and get back the interest-bearing tokens.
  /// @param token The vault token to deposit.
  /// @param amountCall The amount to call transferFrom.
  function deposit(address token, uint amountCall) external override lock poke(token) {
    Vault storage v = vaults[token];
    require(v.status.acceptDeposit(), 'not accept deposit');
    uint totalShare = v.ib.totalSupply();
    uint amount = doTransferIn(token, amountCall);
    uint share = v.totalValue == 0 ? amount : amount.mul(totalShare).div(v.totalValue);
    v.totalValue = v.totalValue.add(amount);
    v.ib.mint(msg.sender, share);
  }

  /// @dev Withdraw tokens from the vault by burning the interest-bearing tokens.
  /// @param token The vault token to withdraw.
  /// @param share The amount of share to burn.
  function withdraw(address token, uint share) external override lock poke(token) {
    Vault storage v = vaults[token];
    require(v.status.acceptWithdraw(), 'not accept withdraw');
    uint totalShare = v.ib.totalSupply();
    uint amount = share.mul(v.totalValue).div(totalShare);
    v.totalValue = v.totalValue.sub(amount);
    v.ib.burn(msg.sender, share);
    doTransferOut(token, amount);
  }

  /// @dev Withdraw the reserve portion of the vault.
  /// @param amount The amount of tokens to withdraw.
  function withdrawReserve(address token, uint amount) public lock poke(token) {
    require(msg.sender == governor, 'not the governor');
    Vault storage v = vaults[token];
    require(v.status.acceptWithdraw(), 'not accept withdraw');
    v.reserve = v.reserve.sub(amount);
    doTransferOut(token, amount);
  }

  /// @dev Liquidate a position. Paying debt for its owner and take the collateral.
  /// @param user The user position to perform liquidation on.
  /// @param collateralToken The collateral token to take in exchange for clearing debts.
  /// @param debtToken The debt token to repay.
  /// @param amountCall The amount to repay when doing transferFrom call.
  function liquidate(
    address user,
    address collateralToken,
    address debtToken,
    uint amountCall
  ) external lock {
    Vault storage v = vaults[debtToken];
    require(oracle.support(collateralToken), 'collateral token not supported');
    uint collateralValue = getCollateralETHValue(user);
    uint borrowValue = getBorrowETHValue(user);
    require(collateralValue < borrowValue, 'account still healthy');
    uint amountPaid = repayInternal(user, debtToken, amountCall);
    uint bounty = oracle.convertForLiquidation(debtToken, collateralToken, amountPaid);
    uint oldAmount = assetAmountOf[user][collateralToken];
    uint newAmount = oldAmount.sub(bounty);
    if (oldAmount != 0 && newAmount == 0) {
      remove(assetsOf[user], collateralToken);
    }
    assetAmountOf[user][collateralToken] = newAmount;
    doTransferOut(collateralToken, bounty);
  }

  /// @dev Execute the action via HomoraCaster, calling its function with the supplied data.
  /// @param target The target to invoke the execution via HomoraCaster.
  /// @param data Extra data to pass to the target for the execution.
  function execute(address target, bytes memory data) external payable lock {
    _EXECUTOR = msg.sender;
    _TARGET = target;
    HomoraCaster(caster).cast{value: msg.value}(target, data);
    uint collateralValue = getCollateralETHValue(msg.sender);
    uint borrowValue = getBorrowETHValue(msg.sender);
    require(collateralValue >= borrowValue, 'insufficient collateral');
    _EXECUTOR = _NO_ADDRESS;
    _TARGET = _NO_ADDRESS;
  }

  /// @dev Borrow tokens from the vault. Must only be called while under execution.
  /// @param token The token to borrow from the vault
  /// @param amount The amount of tokens to borrow.
  function borrow(address token, uint amount) external override inExec poke(token) {
    Vault storage v = vaults[token];
    require(v.status.acceptBorrow(), 'not accept borrow');
    address executor = _EXECUTOR;
    uint share = v.totalDebt == 0 ? amount : amount.mul(v.totalDebtShare).div(v.totalDebt);
    v.totalDebt = v.totalDebt.add(amount);
    v.totalDebtShare = v.totalDebtShare.add(share);
    uint oldShare = debtShareOf[executor][token];
    uint newShare = oldShare.add(share);
    if (oldShare == 0 && newShare != 0) {
      debtsOf[executor].push(token);
      require(debtsOf[executor].length <= MAX_DEBT_COUNT);
    }
    debtShareOf[executor][token] = newShare;
    doTransferOut(token, amount);
  }

  /// @dev Repays tokens to the vault. Must only be called while under execution.
  /// @param token The token to repay to the vault.
  /// @param amountCall The amount of tokens to repay via transferFrom.
  function repay(address token, uint amountCall) external override inExec poke(token) {
    repayInternal(_EXECUTOR, token, amountCall);
  }

  /// @dev Perform repay action. Return the amount actually taken. Refund rest to msg.sender.
  /// @param user The user to repay debts to.
  /// @param token The vault token to pay the debt.
  /// @param amountCall The amount to repay by calling transferFrom.
  function repayInternal(
    address user,
    address token,
    uint amountCall
  ) internal returns (uint) {
    Vault storage v = vaults[token];
    require(v.status.acceptRepay(), 'not accept repay');
    uint amount = doTransferIn(token, amountCall);
    uint oldDebtShare = debtShareOf[user][token];
    uint oldDebt = oldDebtShare.mul(v.totalDebt).div(v.totalDebtShare);
    uint subDebtShare;
    if (amount > oldDebt) {
      doTransferOut(token, amount.sub(oldDebt));
      amount = oldDebt;
      subDebtShare = oldDebtShare;
    } else {
      subDebtShare = amount.mul(v.totalDebtShare).div(v.totalDebt);
    }
    v.totalDebt = v.totalDebt.sub(amount);
    v.totalDebtShare = v.totalDebtShare.sub(subDebtShare);
    uint newDebtShare = oldDebtShare.sub(subDebtShare);
    if (oldDebtShare != 0 && newDebtShare == 0) {
      remove(debtsOf[user], token);
    }
    return amount;
  }

  /// @dev Transmit user assets to the caller, so users only need to approve Bank for spending.
  /// @param token The token to transfer from user to the caller.
  /// @param amount The amount to transfer.
  function transmit(address token, uint amount) external override inExec {
    require(oracle.support(token), 'token not supported');
    IERC20(token).safeTransferFrom(_EXECUTOR, msg.sender, amount);
  }

  /// @dev Put more collateral for users. Must only be called during execution.
  /// @param token The token to put as collateral.
  /// @param amountCall The amount of tokens to put via transferFrom.
  function putCollateral(address token, uint amountCall) external override inExec {
    require(oracle.support(token), 'token not supported');
    address executor = _EXECUTOR;
    uint amount = doTransferIn(token, amountCall);
    uint oldAmount = assetAmountOf[executor][token];
    uint newAmount = oldAmount.add(amount);
    if (oldAmount == 0 && newAmount != 0) {
      assetsOf[executor].push(token);
      require(assetsOf[executor].length <= MAX_ASSET_COUNT, 'too many collateral assets');
    }
    assetAmountOf[executor][token] = newAmount;
  }

  /// @dev Take some collateral back. Must only be called during execution.
  /// @param token The token to take back from being collateral.
  /// @param amount The amount of tokens to take back via transfer.
  function takeCollateral(address token, uint amount) external override inExec {
    require(oracle.support(token), 'token not supported');
    address executor = _EXECUTOR;
    uint oldAmount = assetAmountOf[executor][token];
    uint newAmount = oldAmount.sub(amount);
    if (oldAmount != 0 && newAmount == 0) {
      remove(assetsOf[executor], token);
    }
    assetAmountOf[executor][token] = newAmount;
    doTransferOut(token, amount);
  }

  /// @dev Internal function to perform token transfer in and return amount actually received.
  /// @param token The token to perform transferFrom action.
  /// @param amountCall The amount use in the transferFrom call.
  function doTransferIn(address token, uint amountCall) internal returns (uint) {
    uint balanceBefore = IERC20(token).balanceOf(address(this));
    IERC20(token).safeTransferFrom(msg.sender, address(this), amountCall);
    uint balanceAfter = IERC20(token).balanceOf(address(this));
    return balanceAfter.sub(balanceBefore);
  }

  /// @dev Internal function to perform token transfer out to msg.sender.
  /// @param token The token to perform transfer action.
  /// @param amount The amount use in the transfer call.
  function doTransferOut(address token, uint amount) internal {
    IERC20(token).safeTransfer(msg.sender, amount);
  }

  /// @dev Remove the given address from the storage list. The item must exist in the list.
  /// @param list The storage list to remove an address.
  /// @param addr The address to be removed from the list.
  function remove(address[] storage list, address addr) internal {
    uint length = list.length;
    bool found = false;
    for (uint idx = 0; idx < length; idx++) {
      if (list[idx] == addr) {
        list[idx] = list[length - 1];
        found = true;
        break;
      }
    }
    assert(found);
    list.pop();
  }
}
