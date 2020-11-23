pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/proxy/Initializable.sol';

import './IbToken.sol';
import '../interfaces/IBank.sol';
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

contract Bank is Initializable, IBank {
  using SafeMath for uint;
  using SafeERC20 for IERC20;
  using VaultStatus for VaultStatus.T;

  uint public constant MAX_ASSET_COUNT = 10;

  uint private constant _NOT_ENTERED = 1;
  uint private constant _ENTERED = 2;
  address private constant _NO_ADDRESS = address(1);

  uint public _GENERAL_LOCK;
  uint public _IN_EXEC_LOCK;
  address public _EXECUTOR;
  address public _GOBLIN;

  address public governor;
  address public pendingGovernor;
  IOracle public oracle;

  struct Vault {
    VaultStatus.T status;
    IbToken ib;
    uint lastAccrueTime;
    uint reserve;
    uint totalValue;
    uint totalDebt;
    uint totalDebtShare;
    mapping(address => uint) debtShareOf;
  }

  address[] public allTokens;
  mapping(address => bool) public goblinOk;
  mapping(address => Vault) public vaults;
  mapping(address => address[]) public assetsOf;
  mapping(address => mapping(address => uint)) public assetAmountOf;

  /// @dev Reentrancy lock guard.
  modifier lock() {
    require(_GENERAL_LOCK == _NOT_ENTERED, 'general lock');
    _GENERAL_LOCK = _ENTERED;
    _;
    _GENERAL_LOCK = _NOT_ENTERED;
  }

  /// @dev Ensure that the function is called from an approved goblin within execution scope.
  modifier inExec() {
    require(_EXECUTOR != address(-1), 'not within execution');
    require(_GOBLIN != msg.sender, 'bad caller');
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
    _GOBLIN = _NO_ADDRESS;
    governor = msg.sender;
    pendingGovernor = address(0);
    oracle = _oracle;
  }

  /// @dev Return the length of the vault token list.
  function allTokensLength() public view returns (uint) {
    return allTokens.length;
  }

  /// @dev Return the length of the assets of the given user.
  function assetsLength(address user) public view returns (uint) {
    return assetsOf[user].length;
  }

  /// @dev Trigger interest accrual for the given vault.
  /// @param token The vault token to trigger the interest accrual.
  function accrue(address token) public {
    Vault storage v = vaults[token];
    require(v.status.valid(), 'vault does not exist');
    if (now > v.lastAccrueTime) {
      uint timeElapsed = now - v.lastAccrueTime;
      uint interest = v.totalDebt.mul(timeElapsed).div(3650 days); // TODO: Make it better than 10% per year
      uint reserve = interest / 10; // 10% of fee to reserve
      v.totalDebtShare = v.totalDebt.add(interest);
      v.reserve = v.reserve.add(reserve);
      v.totalValue = v.totalValue.add(interest.sub(reserve));
      v.lastAccrueTime = now;
    }
  }

  /// @dev Convenient function to trigger interest accrual for all vaults.
  function accrueAll() public {
    for (uint idx = 0; idx < allTokens.length; idx++) {
      accrue(allTokens[idx]);
    }
  }

  /// @dev Return the total collateral value of the given user in ETH.
  /// @param user The user to query for the collateral value.
  function getCollateralETHValue(address user) public view returns (uint) {
    uint value = 0;
    for (uint idx = 0; idx < assetsOf[user].length; idx++) {
      address token = assetsOf[user][idx];
      value = value.add(oracle.asETHCollateral(token, assetAmountOf[user][token]));
    }
    return value;
  }

  /// @dev Return the total borrow value of the given user in ETH.
  /// @param user The user to query for the borrow value.
  function getBorrowETHValue(address user) public view returns (uint) {
    uint value = 0;
    for (uint idx = 0; idx < allTokens.length; idx++) {
      address token = allTokens[idx];
      Vault storage v = vaults[token];
      uint share = v.debtShareOf[user];
      if (share > 0) {
        uint debt = share.mul(v.totalDebt).div(v.totalDebtShare);
        value = value.add(oracle.asETHBorrow(token, debt));
      }
    }
    return value;
  }

  /// @dev Set the pending governor, which will be the governor once accepted.
  /// @param _pendingGovernor The address to become the pending governor.
  function setPendingGovernor(address _pendingGovernor) public {
    require(msg.sender == governor, '!governor');
    pendingGovernor = _pendingGovernor;
  }

  /// @dev Accept to become the new governor. Must be called by the pending governor.
  function acceptGovernor() public {
    require(msg.sender == pendingGovernor, '!governor');
    pendingGovernor = address(0);
    governor = msg.sender;
  }

  /// @dev Add a new token to the set of vaults for depositing and borrowing.
  /// @param token The ERC-20 address of the token to become part of the vault.
  /// @param status The initial statue of the newly created vault.
  function addVault(address token, VaultStatus.T status) public lock {
    require(msg.sender == governor, 'not the governor');
    require(status.valid(), 'invalid status');
    Vault storage v = vaults[token];
    require(!v.status.valid(), 'vault already exists');
    v.status = status;
    v.ib = new IbToken(token);
    v.lastAccrueTime = now;
    allTokens.push(token);
  }

  /// @dev Set vault status for the given set of vaults.
  /// @param tokens The set of vault tokens to update the vault status.
  /// @param status The new vault status to set.
  function setVaultStatus(address[] memory tokens, VaultStatus.T status) public lock {
    require(msg.sender == governor, 'not the governor');
    require(status.valid(), 'invalid status');
    for (uint idx = 0; idx < tokens.length; idx++) {
      Vault storage v = vaults[tokens[idx]];
      require(v.status.valid(), 'vault does not exist');
      v.status = status;
    }
  }

  /// @dev Set goblin ok status. BE CAREFUL! DO NOT SET TOKEN CONTRACTS OR SELF AS GOBLINS. EVER.
  /// @param goblins The set of goblins to update status.
  /// @param ok Whether to set those goblins is ok or not.
  function setGoblinOk(address[] memory goblins, bool ok) public lock {
    require(msg.sender == governor, 'not the governor');
    for (uint idx = 0; idx < goblins.length; idx++) {
      address goblin = goblins[idx];
      require(goblin != address(this), 'DO NOT SET SELF AS GOBLIN');
      try IERC20(goblin).totalSupply() returns (uint) {
        revert('DO NOT SET TOKEN CONTRACT AS GOBLIN');
      } catch {}
      goblinOk[goblin] = ok;
    }
  }

  /// @dev Deposit tokens to the vault and get back the interest-bearing tokens.
  /// @param token The vault token to deposit.
  /// @param amountCall The amount to call transferFrom.
  function deposit(address token, uint amountCall) public lock poke(token) {
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
  function withdraw(address token, uint share) public lock poke(token) {
    Vault storage v = vaults[token];
    require(v.status.acceptWithdraw(), 'not accept withdraw');
    uint totalShare = v.ib.totalSupply();
    uint amount = share.mul(v.totalValue).div(totalShare);
    v.totalValue = v.totalValue.sub(amount);
    v.ib.burn(msg.sender, share);
    IERC20(token).safeTransfer(msg.sender, amount);
  }

  /// @dev Withdraw the reserve portion of the vault.
  /// @param amount The amount of tokens to withdraw.
  function withdrawReserve(address token, uint amount) public lock poke(token) {
    require(msg.sender == governor, 'not the governor');
    Vault storage v = vaults[token];
    require(v.status.acceptWithdraw(), 'not accept withdraw');
    v.reserve = v.reserve.sub(amount);
    IERC20(token).safeTransfer(msg.sender, amount);
  }

  function liquidate(
    address user,
    address debtToken,
    address collateralToen
  ) public lock {
    // TODO
  }

  /// @dev Execute the action via goblin, calling its work function with the supplied data.
  /// @param goblin The goblin to invoke the execution on.
  /// @param data Extra data to pass to the goblin for the execution.
  function execute(address goblin, bytes memory data) public lock {
    require(goblinOk[goblin], 'not ok goblin');
    _EXECUTOR = msg.sender;
    _GOBLIN = goblin;
    (bool ok, ) = goblin.call(data);
    require(ok, 'bad goblin call');
    uint colleteralValue = getCollateralETHValue(msg.sender);
    uint borrowValue = getBorrowETHValue(msg.sender);
    require(colleteralValue >= borrowValue, 'insufficient collateral');
    _EXECUTOR = _NO_ADDRESS;
    _GOBLIN = _NO_ADDRESS;
  }

  /// @dev Borrow tokens from the vault. Must only be called from the goblin while under execution.
  /// @param token The token to borrow from the vault.
  /// @param amount The amount of tokens to borrow.
  function borrow(address token, uint amount) public override inExec poke(token) {
    Vault storage v = vaults[token];
    require(v.status.acceptBorrow(), 'not accept borrow');
    uint fee = amount / 1000; // 0.1% origination fee
    uint reserve = fee / 10; // 10% of fee to reserve
    uint debt = amount.add(fee);
    uint debtShare = v.totalDebt == 0 ? debt : debt.mul(v.totalDebtShare).div(v.totalDebt);
    v.totalDebt = v.totalDebt.add(debt);
    v.totalDebtShare = v.totalDebtShare.add(debtShare);
    v.debtShareOf[_EXECUTOR] = v.debtShareOf[_EXECUTOR].add(debtShare);
    v.reserve = v.reserve.add(reserve);
    v.totalValue = v.totalValue.add(fee.sub(reserve));
    IERC20(token).safeTransfer(msg.sender, amount);
  }

  /// @dev Repays tokens to the vault. Must only be called from the goblin while under execution.
  /// @param token The token to repay to the vault.
  /// @param amountCall The amount of tokens to repay via transferFrom.
  function repay(address token, uint amountCall) public override inExec poke(token) {
    Vault storage v = vaults[token];
    require(v.status.acceptRepay(), 'not accept repay');
    uint amount = doTransferIn(token, amountCall);
    uint debtShare = amount.mul(v.totalDebtShare).div(v.totalDebt);
    if (debtShare > v.debtShareOf[_EXECUTOR]) {
      uint excessShare = debtShare.sub(v.debtShareOf[_EXECUTOR]);
      uint excessToken = excessShare.mul(v.totalDebt).div(v.totalDebtShare);
      IERC20(token).safeTransfer(msg.sender, excessToken);
      debtShare = debtShare.sub(excessShare);
      amount = amount.sub(excessToken);
    }
    v.totalDebt = v.totalDebt.sub(amount);
    v.totalDebtShare = v.totalDebtShare.sub(debtShare);
    v.debtShareOf[_EXECUTOR] = v.debtShareOf[_EXECUTOR].sub(debtShare);
  }

  /// @dev Transmit user assets to the goblin, so users only need to approve Bank for spending.
  /// @param token The token to transfer from user to the goblin.
  /// @param amount The amount to transfer.
  function transmit(address token, uint amount) public override inExec {
    require(oracle.support(token), 'token not supported');
    IERC20(token).safeTransferFrom(_EXECUTOR, msg.sender, amount);
  }

  /// @dev Put more collateral for users. Must only be called during execution by the goblin.
  /// @param token The token to put as collateral.
  /// @param amountCall The amount of tokens to put via transferFrom.
  function putCollateral(address token, uint amountCall) public override inExec {
    require(oracle.support(token), 'token not supported');
    uint amount = doTransferIn(token, amountCall);
    uint oldAmount = assetAmountOf[_EXECUTOR][token];
    uint newAmount = oldAmount.add(amount);
    if (oldAmount == 0 && newAmount != 0) {
      assetsOf[_EXECUTOR].push(token);
      require(assetsOf[_EXECUTOR].length <= MAX_ASSET_COUNT, 'too many collateral assets');
    }
    assetAmountOf[_EXECUTOR][token] = newAmount;
  }

  /// @dev Take some collateral back. Must only be called during execution by the goblin.
  /// @param token The token to take back from being collateral.
  /// @param amount The amount of tokens to take back via transfer.
  function takeCollateral(address token, uint amount) public override inExec {
    require(oracle.support(token), 'token not supported');
    uint oldAmount = assetAmountOf[_EXECUTOR][token];
    uint newAmount = oldAmount.sub(amount);
    if (oldAmount != 0 && newAmount == 0) {
      address[] storage assets = assetsOf[_EXECUTOR];
      for (uint idx = 0; idx < assets.length - 1; idx++) {
        if (assets[idx] == token) {
          assets[idx] = assets[assets.length - 1];
          break;
        }
      }
      assets.pop();
    }
    assetAmountOf[_EXECUTOR][token] = newAmount;
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
}
