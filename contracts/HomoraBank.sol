pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/proxy/Initializable.sol';

import './Governable.sol';
import '../interfaces/IBank.sol';
import '../interfaces/ICErc20.sol';
import '../interfaces/IOracle.sol';

contract HomoraCaster {
  /// @dev Call to the target using the given data.
  /// @param target The address target to call.
  /// @param data The data used in the call.
  function cast(address target, bytes calldata data) external payable {
    (bool ok, bytes memory returndata) = target.call{value: msg.value}(data);
    if (!ok) {
      if (returndata.length > 0) {
        // The easiest way to bubble the revert reason is using memory via assembly
        // solhint-disable-next-line no-inline-assembly
        assembly {
          let returndata_size := mload(returndata)
          revert(add(32, returndata), returndata_size)
        }
      } else {
        revert('bad cast call');
      }
    }
  }
}

contract HomoraBank is Initializable, Governable, IBank {
  using SafeMath for uint;
  using SafeERC20 for IERC20;

  uint private constant _NOT_ENTERED = 1;
  uint private constant _ENTERED = 2;
  uint private constant _NO_ID = uint(-1);
  address private constant _NO_ADDRESS = address(1);

  struct Bank {
    bool isListed; // Whether this market exists.
    address cToken; // The CToken to draw liquidity from.
    uint reserve; // The reserve portion allocated to Homora protocol.
    uint pendingReserve; // The pending reserve portion waiting to be resolve.
    uint totalDebt; // The last recorded total debt since last action.
    uint totalShare; // The total debt share count across all open positions.
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

  /// @dev Return the current executor (the owner of the current position).
  function EXECUTOR() external view override returns (address) {
    uint positionId = POSITION_ID;
    require(positionId != _NO_ID, 'not under execution');
    return positions[positionId].owner;
  }

  /// @dev Trigger interest accrual for the given bank.
  /// @param token The underlying token to trigger the interest accrual.
  function accrue(address token) public {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exists');
    uint totalDebt = bank.totalDebt;
    uint debt = ICErc20(bank.cToken).borrowBalanceCurrent(address(this));
    if (debt > totalDebt) {
      uint fee = debt.sub(totalDebt).mul(feeBps).div(10000);
      bank.totalDebt = debt;
      bank.pendingReserve = bank.pendingReserve.add(fee);
    } else if (totalDebt != debt) {
      // We should never reach here because CREAMv2 does not support *repayBorrowBehalf*
      // functionality. We set bank.totalDebt = debt nonetheless to ensure consistency. But do
      // note that if *repayBorrowBehalf* exists, an attacker can maliciously deflate debt
      // share value and potentially make this contract stop working due to math overflow.
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

  /// @dev Trigger reserve resolve by borrowing the pending amount for reserve.
  /// @param token The underlying token to trigger reserve resolve.
  function resolveReserve(address token) public lock {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exists');
    uint pendingReserve = bank.pendingReserve;
    bank.pendingReserve = 0;
    bank.reserve = bank.reserve.add(doBorrow(token, pendingReserve));
  }

  /// @dev Convenient function to trigger reserve resolve for the list of banks.
  /// @param tokens The list of banks to trigger reserve resolve.
  function resolveReserveAll(address[] memory tokens) external {
    for (uint idx = 0; idx < tokens.length; idx++) {
      resolveReserve(tokens[idx]);
    }
  }

  /// @dev Return the borrow balance for given positon and token without trigger interest accrual.
  /// @param positionId The position to query for borrow balance.
  /// @param token The token to query for borrow balance.
  function borrowBalanceStored(uint positionId, address token) public view override returns (uint) {
    uint totalDebt = banks[token].totalDebt;
    uint totalShare = banks[token].totalShare;
    uint share = positions[positionId].debtShareOf[token];
    if (share == 0 || totalDebt == 0) {
      return 0;
    } else {
      return share.mul(totalDebt).div(totalShare);
    }
  }

  /// @dev Trigger interest accrual and return the current borrow balance.
  /// @param positionId The position to query for borrow balance.
  /// @param token The token to query for borrow balance.
  function borrowBalanceCurrent(uint positionId, address token) external override returns (uint) {
    accrue(token);
    return borrowBalanceStored(positionId, token);
  }

  /// @dev Return bank information for the given token.
  /// @param token The token address to query for bank information.
  function getBankInfo(address token)
    external
    view
    override
    returns (
      bool isListed,
      address cToken,
      uint reserve,
      uint totalDebt,
      uint totalShare
    )
  {
    Bank storage bank = banks[token];
    return (bank.isListed, bank.cToken, bank.reserve, bank.totalDebt, bank.totalShare);
  }

  /// @dev Return position information for the given position id.
  /// @param positionId The position id to query for position information.
  function getPositionInfo(uint positionId)
    external
    view
    override
    returns (
      address owner,
      address collateralToken,
      uint collateralSize
    )
  {
    Position storage position = positions[positionId];
    return (position.owner, position.collateralToken, position.collateralSize);
  }

  /// @dev Return the total collateral value of the given position in ETH.
  /// @param positionId The position ID to query for the collateral value.
  function getCollateralETHValue(uint positionId) public view returns (uint) {
    Position storage position = positions[positionId];
    uint size = position.collateralSize;
    return size == 0 ? 0 : oracle.asETHCollateral(position.collateralToken, size);
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
    IERC20(token).safeApprove(cToken, uint(-1));
    allBanks.push(token);
    emit AddBank(token, cToken);
  }

  /// @dev Upgrade cToken contract address to a new address. Must be used with care!
  /// @param token The underlying token for the bank.
  /// @param cToken The address of the cToken smart contract.
  function setCToken(address token, address cToken) external onlyGov {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exists');
    bank.cToken = cToken;
    emit SetCToken(token, cToken);
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
  function withdrawReserve(address token, uint amount) external onlyGov lock {
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
  /// @param data Extra data to pass to the target for the execution.
  function execute(
    uint positionId,
    address spell,
    bytes memory data
  ) external payable lock returns (uint) {
    if (positionId == 0) {
      positionId = nextPositionId++;
      Position storage position = positions[positionId];
      position.owner = msg.sender;
    } else {
      require(positionId < nextPositionId, 'position id not exists');
      Position storage position = positions[positionId];
      require(msg.sender == position.owner, 'not position owner');
    }
    POSITION_ID = positionId;
    SPELL = spell;
    HomoraCaster(caster).cast{value: msg.value}(spell, data);
    uint collateralValue = getCollateralETHValue(positionId);
    uint borrowValue = getBorrowETHValue(positionId);
    require(collateralValue >= borrowValue, 'insufficient collateral');
    POSITION_ID = _NO_ID;
    SPELL = _NO_ADDRESS;
    return positionId;
  }

  /// @dev Borrow tokens from tha bank. Must only be called while under execution.
  /// @param token The token to borrow from the bank.
  /// @param amount The amount of tokens to borrow.
  function borrow(address token, uint amount) external override inExec poke(token) {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exists');
    Position storage position = positions[POSITION_ID];
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint share = totalShare == 0 ? amount : amount.mul(totalDebt).div(totalShare);
    bank.totalShare = bank.totalShare.add(share);
    position.debtShareOf[token] = position.debtShareOf[token].add(share);
    doTransferOut(token, doBorrow(token, amount));
    emit Borrow(POSITION_ID, msg.sender, token, amount, share);
  }

  /// @dev Repay tokens to the bank. Must only be called while under execution.
  /// @param token The token to repay to the bank.
  /// @param amountCall The amount of tokens to repay via transferFrom.
  function repay(address token, uint amountCall) external override inExec poke(token) {
    (uint amount, uint share) = repayInternal(POSITION_ID, token, amountCall);
    emit Repay(POSITION_ID, msg.sender, token, amount, share);
  }

  /// @dev Perform repay action. Return the amount actually taken and the debt share reduced.
  /// @param positionId The position ID to repay the debt.
  /// @param token The bank token to pay the debt.
  /// @param amountCall The amount to repay by calling transferFrom, or -1 for debt size.
  function repayInternal(
    uint positionId,
    address token,
    uint amountCall
  ) internal returns (uint, uint) {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exists');
    Position storage position = positions[positionId];
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint oldShare = position.debtShareOf[token];
    uint oldDebt = oldShare.mul(totalDebt).div(totalShare);
    if (amountCall == uint(-1)) {
      amountCall = oldDebt;
    }
    uint paid = doRepay(token, doTransferIn(token, amountCall));
    require(paid <= oldDebt, 'paid exceeds debt'); // prevent share overflow attack
    uint lessShare = paid == oldDebt ? oldShare : paid.mul(totalShare).div(totalDebt);
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
  /// @param collateralToken The token to collateral.
  /// @param amountCall The amount of tokens to put via transferFrom.
  function putCollateral(address collateralToken, uint amountCall) external override inExec {
    Position storage position = positions[POSITION_ID];
    if (position.collateralToken != collateralToken) {
      require(oracle.support(collateralToken), 'collateral token not supported');
      require(position.collateralSize == 0, 'another type of collateral already exists');
      position.collateralToken = collateralToken;
    }
    uint amount = doTransferIn(collateralToken, amountCall);
    position.collateralSize = position.collateralSize.add(amount);
    emit PutCollateral(POSITION_ID, msg.sender, collateralToken, amount);
  }

  /// @dev Take some collateral back. Must only be called during execution.
  /// @param collateralToken The token to take back.
  /// @param amount The amount of tokens to take back via transfer.
  function takeCollateral(address collateralToken, uint amount) external override inExec {
    Position storage position = positions[POSITION_ID];
    require(collateralToken == position.collateralToken, 'invalid collateral token');
    if (amount == uint(-1)) {
      amount = position.collateralSize;
    }
    position.collateralSize = position.collateralSize.sub(amount);
    doTransferOut(collateralToken, amount);
    emit TakeCollateral(POSITION_ID, msg.sender, collateralToken, amount);
  }

  /// @dev Internal function to perform borrow from the bank and return the amount received.
  /// @param token The token to perform borrow action.
  /// @param amountCall The amount use in the transferFrom call.
  /// NOTE: Caller must ensure that cToken interest was already accrued up to this block.
  function doBorrow(address token, uint amountCall) internal returns (uint) {
    Bank storage bank = banks[token]; // assume the input is already sanity checked.
    uint balanceBefore = IERC20(token).balanceOf(address(this));
    require(ICErc20(bank.cToken).borrow(amountCall) == 0, 'bad borrow');
    uint balanceAfter = IERC20(token).balanceOf(address(this));
    bank.totalDebt = bank.totalDebt.add(amountCall);
    return balanceAfter.sub(balanceBefore);
  }

  /// @dev Internal function to perform repay to the bank and return the amount actually repaid.
  /// @param token The token to perform repay action.
  /// @param amountCall The amount to use in the repay call.
  /// NOTE: Caller must ensure that cToken interest was already accrued up to this block.
  function doRepay(address token, uint amountCall) internal returns (uint) {
    Bank storage bank = banks[token]; // assume the input is already sanity checked.
    ICErc20 cToken = ICErc20(bank.cToken);
    uint oldDebt = bank.totalDebt;
    cToken.repayBorrow(amountCall);
    uint newDebt = cToken.borrowBalanceStored(address(this));
    bank.totalDebt = newDebt;
    return oldDebt.sub(newDebt);
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
}
