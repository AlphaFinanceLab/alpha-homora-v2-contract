pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/proxy/Initializable.sol';

import './Governable.sol';
import '../interfaces/IBank.sol';
import '../interfaces/ICToken.sol';
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
  uint private constant _NOT_ENTERED = 1;
  uint private constant _ENTERED = 2;
  uint private constant _NO_ID = uint(-1);
  address private constant _NO_ADDRESS = address(1);

  struct Bank {
    bool isListed; // Whether this market exists.
    address cToken; // The CToken to draw liquidity from.
    uint reserve; // The reserve portion allocated to Homora.
    uint totalDebt; // The last recorded total debt since last action.
    uint totalShare; // The total debt share count across all positions.
  }

  struct Position {
    address owner; // The owner of this position.
    address collateralToken; // The token used as collateral for this position.
    uint collateralSize; // The size of collateral token for this position.
    mapping(address => uint) debtShareOf; // The debt share for each token.
  }

  uint public _GENERAL_LOCK; // TEMPORARY: re-entrancy lock guard.
  uint public _IN_EXEC_LOCK; // TEMPORARY: exec lock guard.
  uint public override POSITION_ID; // TEMPORARY: position ID currently under execution.
  address public override SPELL; // TEMPORARY: spell currently under execution.

  address public caster; // The caster address for untrusted execution.
  IOracle public oracle; // The oracle address for determining prices.
  uint public feeBps; // The fee collected as protocol reserve in basis point from interest.
  uint public nextPositionId; // Next available position ID, starting from 1 (see initialize).

  address[] public allBanks; // The list of all listed banks.
  mapping(address => Bank) public banks; // Mapping from token to bank data.
  mapping(uint => Position) public positions; // Mapping from position ID to position data.

  /// @dev Reentrancy lock guard.
  modifier lock() {
    require(_GENERAL_LOCK == _NOT_ENTERED, 'general lock');
    _GENERAL_LOCK = _ENTERED;
    _;
    _GENERAL_LOCK = _NOT_ENTERED;
  }

  /// @dev Ensure that the function is called from within the execution scope.
  modifier inExec() {
    require(POSITION_ID != _NO_ID, 'not within execution');
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
    POSITION_ID = _NO_ID;
    SPELL = _NO_ADDRESS;
    caster = address(new HomoraCaster());
    oracle = _oracle;
    feeBps = _feeBps;
    nextPositionId = 1;
    emit SetOracle(address(_oracle));
    emit SetFeeBps(_feeBps);
  }

  /// @dev Trigger interest accrual for the given bank.
  /// @param token The underlying token to trigger the interest accrual.
  function accrue(address token) public {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exist');
    uint totalDebt = bank.totalDebt;
    uint debt = ICToken(bank.cToken).borrowBalanceCurrent(address(this));
    if (debt > totalDebt) {
      uint fee = debt.sub(totalDebt).mul(feeBps).div(10000);
      bank.reserve = bank.reserve.add(doBorrow(token, fee)); // totalDebt gets updated in doBorrow.
    } else {
      bank.totalDebt = debt;
    }
  }

  /// @dev Convenient function to trigger interest accrual for the list of banks.
  /// @param tokens The list of banks to trigger interest accrual.
  function accrueAll(address[] memory tokens) external {
    for (uint idx = 0; idx < tokens.length; idx++) {
      accrue(tokens[idx]);
    }
  }

  /// @dev Return the total collateral value of the given position in ETH.
  /// @param positionId The position ID to query for the collateral value.
  function getCollateralETHValue(uint positionId) public view returns (uint) {
    Position storage position = positions[positionId];
    return oracle.asETHCollateral(position.collateralToken, position.collateralSize);
  }

  /// @dev Return the total borrow value of the given position in ETH.
  /// @param positionId The position ID to query for the borrow value.
  function getBorrowETHValue(uint positionId) public view returns (uint) {
    uint value = 0;
    uint length = allBanks.length;
    Position storage position = positions[positionId];
    for (uint idx = 0; idx < length; idx++) {
      address token = allBanks[idx];
      uint share = position.debtShareOf[token];
      if (share != 0) {
        Bank storage bank = banks[token];
        uint debt = share.mul(bank.totalDebt).div(bank.totalShare);
        value = value.add(oracle.asETHBorrow(token, debt));
      }
    }
    return value;
  }

  /// @dev Add a new bank to the ecosystem.
  /// @param token The underlying token for the bank.
  /// @param cToken The address of the cToken smart contract.
  function addBank(address token, address cToken) external onlyGov {
    Bank storage bank = banks[token];
    require(!bank.isListed, 'bank already exists');
    bank.isListed = true;
    bank.cToken = cToken;
    allBanks.push(token);
    emit AddBank(token, cToken);
  }

  /// @dev Set the oracle smart contract address.
  /// @param _oracle The new oracle smart contract address.
  function setOracle(IOracle _oracle) external onlyGov {
    oracle = _oracle;
    emit SetOracle(address(_oracle));
  }

  /// @dev Set the fee bps value that Homora bank charges.
  /// @param _feeBps The new fee bps value.
  function setFeeBps(uint _feeBps) external onlyGov {
    require(_feeBps <= 10000, 'fee too high');
    feeBps = _feeBps;
    emit SetFeeBps(_feeBps);
  }

  /// @dev Withdraw the reserve portion of the bank.
  /// @param amount The amount of tokens to withdraw.
  function withdrawReserve(address token, uint amount) external onlyGov lock poke(token) {
    Bank storage bank = banks[token];
    bank.reserve = bank.reserve.sub(amount);
    doTransferOut(token, amount);
    emit WithdrawReserve(msg.sender, token, amount);
  }

  /// @dev Liquidate a position. Pay debt for its owner and take the collateral.
  /// @param positionId The position ID to liquidate.
  /// @param debtToken The debt token to repay.
  /// @param amountCall The amount to repay when doing transferFrom call.
  function liquidate(
    uint positionId,
    address debtToken,
    uint amountCall
  ) external lock poke(debtToken) {
    uint collateralValue = getCollateralETHValue(positionId);
    uint borrowValue = getBorrowETHValue(positionId);
    require(collateralValue < borrowValue, 'position still healthy');
    Position storage position = positions[positionId];
    (uint amountPaid, uint share) = repayInternal(positionId, debtToken, amountCall);
    uint bounty = oracle.convertForLiquidation(debtToken, position.collateralToken, amountPaid);
    doTransferOut(position.collateralToken, bounty);
    emit Liquidate(positionId, msg.sender, debtToken, amountPaid, share, bounty);
  }

  /// @dev Execute the action via HomoraCaster, calling its function with the supplied data.
  /// @param positionId The position ID to execution the action, or zero for new position.
  /// @param spell The target spell to invoke the execution via HomoraCaster.
  /// @param collateralToken The collateral token for this position.
  /// @param data Extra data to pass to the target for the execution.
  function execute(
    uint positionId,
    address spell,
    address collateralToken,
    bytes memory data
  ) external payable lock {
    if (positionId == 0) {
      require(oracle.support(collateralToken), 'collateral token not supported');
      positionId = nextPositionId++;
      Position storage position = positions[positionId];
      position.owner = msg.sender;
      position.collateralToken = collateralToken;
    } else {
      require(positionId < nextPositionId, 'position id not exists');
      Position storage position = positions[positionId];
      require(msg.sender == position.owner, 'not position owner');
      require(collateralToken == position.collateralToken, 'bad position token');
    }
    POSITION_ID = positionId;
    SPELL = spell;
    HomoraCaster(caster).cast{value: msg.value}(spell, data);
    uint collateralValue = getCollateralETHValue(positionId);
    uint borrowValue = getBorrowETHValue(positionId);
    require(collateralValue >= borrowValue, 'insufficient collateral');
    POSITION_ID = _NO_ID;
    SPELL = _NO_ADDRESS;
  }

  /// @dev Borrow implementation that work both for ETH and ERC20 tokens.
  /// @param token The token to borrow from the bank.
  /// @param amount The amount of tokens to borrow.
  function borrow(address token, uint amount) external override inExec poke(token) {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exist');
    Position storage position = positions[POSITION_ID];
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint share = totalShare == 0 ? amount : amount.mul(totalDebt).div(totalShare);
    position.debtShareOf[token] = position.debtShareOf[token].add(share);
    doTransferOut(token, doBorrow(token, amount));
    emit Borrow(POSITION_ID, msg.sender, token, amount, share);
  }

  /// @dev Repays tokens to the bank. Must only be called while under execution.
  /// @param token The token to repay to the bank.
  /// @param amountCall The amount of tokens to repay via transferFrom.
  function repay(address token, uint amountCall) external payable override inExec poke(token) {
    (uint amount, uint share) = repayInternal(POSITION_ID, token, amountCall);
    emit Repay(POSITION_ID, msg.sender, token, amount, share);
  }

  /// @dev Perform repay action. Return the amount actually taken and the debt share reduced.
  /// @param positionId The position ID to repay the debt.
  /// @param token The bank token to pay the debt.
  /// @param amountCall The amount to repay by calling transferFrom, or 0 for debt size.
  function repayInternal(
    uint positionId,
    address token,
    uint amountCall
  ) internal returns (uint, uint) {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exist');
    Position storage position = positions[positionId];
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint oldShare = position.debtShareOf[token];
    uint oldDebt = oldShare.mul(totalDebt).div(totalShare);
    uint paid = doRepay(token, doTransferIn(token, amountCall == uint(-1) ? oldDebt : amountCall));
    uint lessShare = paid >= oldDebt ? oldShare : paid.mul(totalShare).div(totalDebt);
    bank.totalShare = totalShare.sub(lessShare);
    position.debtShareOf[token] = oldShare.sub(lessShare);
    return (paid, lessShare);
  }

  /// @dev Transmit user assets to the caller, so users only need to approve Bank for spending.
  /// @param token The token to transfer from user to the caller.
  /// @param amount The amount to transfer.
  function transmit(address token, uint amount) external override inExec {
    Position storage position = positions[POSITION_ID];
    IERC20(token).safeTransferFrom(position.owner, msg.sender, amount);
  }

  /// @dev Put more collateral for users. Must only be called during execution.
  /// @param amountCall The amount of tokens to put via transferFrom.
  function putCollateral(uint amountCall) external override inExec {
    Position storage position = positions[POSITION_ID];
    uint amount = doTransferIn(position.collateralToken, amountCall);
    position.collateralSize = position.collateralSize.add(amount);
    emit PutCollateral(POSITION_ID, msg.sender, amount);
  }

  /// @dev Take some collateral back. Must only be called during execution.
  /// @param amount The amount of tokens to take back via transfer.
  function takeCollateral(uint amount) external override inExec {
    Position storage position = positions[POSITION_ID];
    position.collateralSize = position.collateralSize.sub(amount);
    emit TakeCollateral(POSITION_ID, msg.sender, amount);
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

  /// @dev Only accept ETH sent from the cETH token smart contract.
  receive() external payable {
    require(msg.sender == banks[ETH].cToken, 'not from cETH');
  }
}
