pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/proxy/Initializable.sol';

import './Governable.sol';
import './IbTokenV2.sol';
import '../interfaces/IBank.sol';
import '../interfaces/ICErc20.sol';
import '../interfaces/ICEther.sol';
import '../interfaces/IInterestRateModel.sol';
import '../interfaces/IOracle.sol';

contract HomoraCaster {
  /// @dev Call to the target using the given data.
  /// @param target The address target to call.
  /// @param data The data using in the call.
  function cast(address target, bytes calldata data) external payable {
    (bool ok, ) = target.call{value: msg.value}(data);
    require(ok, 'bad cast call');
  }
}

contract HomoraBank is Initializable, Governable, IBank {
  using SafeMath for uint;
  using SafeERC20 for IERC20;

  address public constant ETH = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
  uint public constant MAX_ASSET_COUNT = 10;
  uint public constant MAX_DEBT_COUNT = 10;

  uint private constant _NOT_ENTERED = 1;
  uint private constant _ENTERED = 2;
  address private constant _NO_ADDRESS = address(1);

  uint public _GENERAL_LOCK;
  uint public _IN_EXEC_LOCK;
  address public override EXECUTOR;
  address public override SPELL;
  uint public override CONTEXT_ID;

  address public caster;
  IOracle public oracle;
  uint public feeBps;

  struct Bank {
    bool active;
    address cToken;
    uint reserve;
    uint totalDebt;
    uint totalShare;
  }

  mapping(address => Bank) public banks;
  mapping(address => mapping(uint => address[])) public assetsOf;
  mapping(address => mapping(uint => mapping(address => uint))) public assetAmountOf;
  mapping(address => mapping(uint => address[])) public debtsOf;
  mapping(address => mapping(uint => mapping(address => uint))) public debtShareOf;

  /// @dev Reentrancy lock guard.
  modifier lock() {
    require(_GENERAL_LOCK == _NOT_ENTERED, 'general lock');
    _GENERAL_LOCK = _ENTERED;
    _;
    _GENERAL_LOCK = _NOT_ENTERED;
  }

  /// @dev Ensure that the function is called from within the execution scope.
  modifier inExec() {
    require(EXECUTOR != _NO_ADDRESS, 'not within execution');
    require(SPELL == msg.sender, 'not from spell');
    require(_IN_EXEC_LOCK == _NOT_ENTERED, 'in exec lock');
    _IN_EXEC_LOCK = _ENTERED;
    _;
    _IN_EXEC_LOCK = _NOT_ENTERED;
  }

  /// @dev Ensure that the interest rate of the given token is accrued.
  modifier poke(address token) {
    accrue(token);
    _;
  }

  /// @dev Initialize the bank smart contract, using msg.sender as the first governor.
  /// @param _oracle The oracle smart contract address.
  /// @param _feeBps The fee collected to Homora bank.
  function initialize(IOracle _oracle, uint _feeBps) public initializer {
    Governable.initialize();
    _GENERAL_LOCK = _NOT_ENTERED;
    _IN_EXEC_LOCK = _NOT_ENTERED;
    EXECUTOR = _NO_ADDRESS;
    SPELL = _NO_ADDRESS;
    CONTEXT_ID = uint(-1);
    caster = address(new HomoraCaster());
    oracle = _oracle;
    feeBps = _feeBps;
    emit SetOracle(address(_oracle));
    emit SetFeeBps(_feeBps);
  }

  /// @dev Return the length of the assets of the given user.
  function assetsLengthOf(address user, uint contextId) public view returns (uint) {
    return assetsOf[user][contextId].length;
  }

  /// @dev Return the length of the debts of the given user.
  function debtsLengthOf(address user, uint contextId) public view returns (uint) {
    return debtsOf[user][contextId].length;
  }

  /// @dev Trigger interest accrual for the given bank.
  /// @param token The underlying token to trigger the interest accrual.
  function accrue(address token) public {
    Bank storage bank = banks[token];
    require(bank.active, 'bank not active');
    uint totalDebt = bank.totalDebt;
    uint debt = ICErc20(bank.cToken).borrowBalanceCurrent(address(this));
    if (debt > totalDebt) {
      uint fee = debt.sub(totalDebt).mul(feeBps).div(10000);
      bank.totalDebt = debt;
      bank.reserve = bank.reserve.add(doBorrow(token, fee));
    } else {
      bank.totalDebt = debt;
    }
  }

  /// @dev Convenient function to trigger interest accrual for the list of banks.
  /// @param tokens The list of banks to trigger interest accrual.
  function accrueAll(address[] memory tokens) public {
    for (uint idx = 0; idx < tokens.length; idx++) {
      accrue(tokens[idx]);
    }
  }

  /// @dev Return the total collateral value of the given user in ETH.
  /// @param user The user to query for the collateral value.
  function getCollateralETHValue(address user, uint contextId) public view returns (uint) {
    uint value = 0;
    uint length = assetsOf[user][contextId].length;
    for (uint idx = 0; idx < length; idx++) {
      address token = assetsOf[user][contextId][idx];
      value = value.add(oracle.asETHCollateral(token, assetAmountOf[user][contextId][token]));
    }
    return value;
  }

  /// @dev Return the total borrow value of the given user in ETH.
  /// @param user The user to query for the borrow value.
  function getBorrowETHValue(address user, uint contextId) public view returns (uint) {
    uint value = 0;
    uint length = debtsOf[user][contextId].length;
    for (uint idx = 0; idx < length; idx++) {
      address token = debtsOf[user][contextId][idx];
      uint share = debtShareOf[user][contextId][token];
      Bank storage bank = banks[token];
      uint debt = share.mul(bank.totalDebt).div(bank.totalShare);
      value = value.add(oracle.asETHBorrow(token, debt));
    }
    return value;
  }

  /// @dev Add a new bank to the ecosystem.
  /// @param token The underlying token for the bank.
  /// @param cToken The address of the cToken smart contract.
  /// @param status The initial bank status.
  function addBank(
    address token,
    address cToken,
    bool status
  ) public onlyGov {
    Bank storage bank = banks[token];
    require(cToken != address(0), 'bad cToken');
    require(bank.cToken != address(0), 'bank already exists');
    bank.cToken = cToken;
    bank.active = status;
    emit AddBank(token, cToken, status);
  }

  /// @dev Set bank status for the given set of banks.
  /// @param tokens The set of bank tokens to update the bank status.
  /// @param status The new bank status to set.
  function setBankStatus(address[] memory tokens, bool status) public onlyGov {
    for (uint idx = 0; idx < tokens.length; idx++) {
      address token = tokens[idx];
      Bank storage bank = banks[token];
      bank.active = status;
    }
  }

  /// @dev Set the oracle smart contract address.
  /// @param _oracle The new oracle smart contract address.
  function setOracle(IOracle _oracle) public onlyGov {
    oracle = _oracle;
    emit SetOracle(address(_oracle));
  }

  /// @dev Set the fee bps value that Homora bank charges.
  /// @param _feeBps The new fee bps value.
  function setFeeBps(uint _feeBps) public onlyGov {
    require(_feeBps <= 10000, 'fee too high');
    feeBps = _feeBps;
    emit SetFeeBps(_feeBps);
  }

  /// @dev Withdraw the reserve portion of the bank.
  /// @param amount The amount of tokens to withdraw.
  function withdrawReserve(address token, uint amount) public onlyGov lock poke(token) {
    Bank storage bank = banks[token];
    bank.reserve = bank.reserve.sub(amount);
    doTransferOut(token, amount);
    emit WithdrawReserve(msg.sender, token, amount);
  }

  /// @dev Liquidate a position. Pay debt for its owner and take the collateral.
  /// @param user The user position to perform liquidation on.
  /// @param debtToken The debt token to repay.
  /// @param collateralToken The collateral token to take in exchange for clearing debts.
  /// @param amountCall The amount to repay when doing transferFrom call.
  function liquidate(
    address user,
    address debtToken,
    address collateralToken,
    uint amountCall
  ) external lock poke(debtToken) {
    // TODO
    // require(oracle.support(collateralToken), 'collateral token not supported');
    // uint collateralValue = getCollateralETHValue(user);
    // uint borrowValue = getBorrowETHValue(user);
    // require(collateralValue < borrowValue, 'account still healthy');
    // (uint amountPaid, uint share) = repayInternal(user, debtToken, amountCall);
    // uint bounty = oracle.convertForLiquidation(debtToken, collateralToken, amountPaid);
    // uint oldAmount = assetAmountOf[user][collateralToken];
    // uint newAmount = oldAmount.sub(bounty);
    // if (oldAmount != 0 && newAmount == 0) {
    //   remove(assetsOf[user], collateralToken);
    // }
    // assetAmountOf[user][collateralToken] = newAmount;
    // doTransferOut(collateralToken, bounty);
    // emit Liquidate(user, msg.sender, debtToken, collateralToken, amountPaid, share, bounty);
  }

  /// @dev Execute the action via HomoraCaster, calling its function with the supplied data.
  /// @param spell The target spell to invoke the execution via HomoraCaster.
  /// @param data Extra data to pass to the target for the execution.
  function execute(
    uint contextId,
    address spell,
    bytes memory data
  ) external payable lock {
    EXECUTOR = msg.sender;
    SPELL = spell;
    CONTEXT_ID = contextId;
    HomoraCaster(caster).cast{value: msg.value}(spell, data);
    uint collateralValue = getCollateralETHValue(msg.sender, contextId);
    uint borrowValue = getBorrowETHValue(msg.sender, contextId);
    require(collateralValue >= borrowValue, 'insufficient collateral');
    EXECUTOR = _NO_ADDRESS;
    SPELL = _NO_ADDRESS;
    CONTEXT_ID = uint(-1);
  }

  /// @dev Borrow implementation that work both for ETH and ERC20 tokens.
  /// @param token The token to borrow from the bank.
  function borrow(address token, uint amount) external override inExec poke(token) {
    Bank storage bank = banks[token];
    require(bank.active, 'bank not active');
    address executor = EXECUTOR;
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint received = doBorrow(token, amount);
    uint share = totalShare == 0 ? amount : amount.mul(totalDebt).div(totalShare);
    bank.totalShare = totalShare.add(share);
    uint oldShare = debtShareOf[executor][token];
    uint newShare = oldShare.add(share);
    if (oldShare == 0 && newShare != 0) {
      debtsOf[executor].push(token);
      require(debtsOf[executor].length <= MAX_DEBT_COUNT, 'too many borrow assets');
    }
    debtShareOf[executor][token] = newShare;
    doTransferOut(token, received);
    emit Borrow(executor, msg.sender, token, amount, share);
  }

  /// @dev Repays tokens to the bank. Must only be called while under execution.
  /// @param token The token to repay to the bank.
  /// @param amountCall The amount of tokens to repay via transferFrom.
  function repay(address token, uint amountCall) external payable override inExec poke(token) {
    address executor = EXECUTOR;
    (uint amount, uint share) = repayInternal(executor, token, amountCall);
    emit Repay(executor, msg.sender, token, amount, share);
  }

  /// @dev Perform repay action. Refund rest to msg.sender.
  /// @param user The user to repay debts to.
  /// @param token The bank token to pay the debt.
  /// @param amountCall The amount to repay by calling transferFrom.
  /// @return The amount actually taken and the debt share reduced.
  function repayInternal(
    address user,
    address token,
    uint amountCall
  ) internal returns (uint, uint) {
    Bank storage bank = banks[token];
    require(bank.active, 'bank not active');
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint oldShare = debtShareOf[user][token];
    uint oldDebt = oldShare.mul(totalDebt).div(totalShare);
    if (amountCall == uint(-1)) {
      amountCall = oldDebt;
    }
    uint amount = doRepay(token, doTransferIn(token, amountCall));
    uint lessShare = amount >= oldDebt ? oldShare : amount.mul(totalShare).div(totalDebt);
    bank.totalShare = totalShare.sub(lessShare);
    uint newShare = oldDebt.sub(lessShare);
    if (oldDebt != 0 && newShare == 0) {
      remove(debtsOf[user], token);
    }
    return (amount, lessShare);
  }

  /// @dev Transmit user assets to the caller, so users only need to approve Bank for spending.
  /// @param token The token to transfer from user to the caller.
  /// @param amount The amount to transfer.
  function transmit(address token, uint amount) external override inExec {
    require(oracle.support(token), 'token not supported');
    IERC20(token).safeTransferFrom(EXECUTOR, msg.sender, amount);
  }

  /// @dev Put more collateral for users. Must only be called during execution.
  /// @param token The token to put as collateral.
  /// @param amountCall The amount of tokens to put via transferFrom.
  function putCollateral(address token, uint amountCall) external override inExec {
    require(oracle.support(token), 'token not supported');
    address executor = EXECUTOR;
    uint amount = doTransferIn(token, amountCall);
    uint oldAmount = assetAmountOf[executor][token];
    uint newAmount = oldAmount.add(amount);
    if (oldAmount == 0 && newAmount != 0) {
      assetsOf[executor].push(token);
      require(assetsOf[executor].length <= MAX_ASSET_COUNT, 'too many collateral assets');
    }
    assetAmountOf[executor][token] = newAmount;
    emit PutCollateral(executor, msg.sender, token, amount);
  }

  /// @dev Take some collateral back. Must only be called during execution.
  /// @param token The token to take back from being collateral.
  /// @param amount The amount of tokens to take back via transfer.
  function takeCollateral(address token, uint amount) external override inExec {
    require(oracle.support(token), 'token not supported');
    address executor = EXECUTOR;
    uint oldAmount = assetAmountOf[executor][token];
    uint newAmount = oldAmount.sub(amount);
    if (oldAmount != 0 && newAmount == 0) {
      remove(assetsOf[executor], token);
    }
    assetAmountOf[executor][token] = newAmount;
    doTransferOut(token, amount);
    emit TakeCollateral(executor, msg.sender, token, amount);
  }

  /// @dev Internal function to perform borrow from the bank and return the amount received.
  /// @param token The token to perform borrow action.
  /// @param amountCall The amount use in the transferFrom call.
  /// NOTE: Caller must ensure that cToken interest was already accrued up to this block.
  function doBorrow(address token, uint amountCall) internal returns (uint) {
    Bank storage bank = banks[token]; // assume the input is already sanity checked.
    if (token == ETH) {
      ICEther cToken = ICEther(bank.cToken);
      require(cToken.borrow(amountCall) == 0, 'bad borrow');
      bank.totalDebt = cToken.borrowBalanceStored(address(this));
      return amountCall;
    } else {
      ICErc20 cToken = ICErc20(bank.cToken);
      uint balanceBefore = IERC20(token).balanceOf(address(this));
      require(cToken.borrow(amountCall) == 0, 'bad borrow');
      uint balanceAfter = IERC20(token).balanceOf(address(this));
      bank.totalDebt = cToken.borrowBalanceStored(address(this));
      return balanceAfter.sub(balanceBefore);
    }
  }

  /// @dev Internal function to perform repay to the bank and return the amount actually repaid.
  /// @param token The token to perform repay action.
  /// @param amountCall The amount to use in the repay call.
  /// NOTE: Caller must ensure that cToken interest was already accrued up to this block.
  function doRepay(address token, uint amountCall) internal returns (uint) {
    Bank storage bank = banks[token]; // assume the input is already sanity checked.
    if (token == ETH) {
      ICEther cToken = ICEther(bank.cToken);
      cToken.repayBorrow{value: amountCall}();
      bank.totalDebt = cToken.borrowBalanceStored(address(this));
      return amountCall;
    } else {
      ICErc20 cToken = ICErc20(bank.cToken);
      uint balanceBefore = IERC20(token).balanceOf(address(this));
      cToken.repayBorrow(amountCall);
      uint balanceAfter = IERC20(token).balanceOf(address(this));
      bank.totalDebt = cToken.borrowBalanceStored(address(this));
      return balanceBefore.sub(balanceAfter);
    }
  }

  /// @dev Internal function to perform token transfer in and return amount actually received.
  /// @param token The token to perform transferFrom action.
  /// @param amountCall The amount use in the transferFrom call.
  function doTransferIn(address token, uint amountCall) internal returns (uint) {
    if (token == ETH) {
      require(msg.value == amountCall); // Actually no-op. Do not call this twice per context.
      return msg.value;
    } else {
      uint balanceBefore = IERC20(token).balanceOf(address(this));
      IERC20(token).safeTransferFrom(msg.sender, address(this), amountCall);
      uint balanceAfter = IERC20(token).balanceOf(address(this));
      return balanceAfter.sub(balanceBefore);
    }
  }

  /// @dev Internal function to perform token transfer out to msg.sender.
  /// @param token The token to perform transfer action.
  /// @param amount The amount use in the transfer call.
  function doTransferOut(address token, uint amount) internal {
    if (token == ETH) {
      (bool success, ) = msg.sender.call{value: amount}(new bytes(0));
      require(success, 'doTransferOut failed');
    } else {
      IERC20(token).safeTransfer(msg.sender, amount);
    }
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

  /// @dev Only accept ETH sent from the cETH token smart contract.
  receive() external payable {
    require(msg.sender == banks[ETH].cToken, 'not from cETH');
  }
}
