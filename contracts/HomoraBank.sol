// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC1155/IERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/Math.sol';

import './Governable.sol';
import './utils/ERC1155NaiveReceiver.sol';
import '../interfaces/IBank.sol';
import '../interfaces/ICErc20.sol';
import '../interfaces/IOracle.sol';

library HomoraSafeMath {
  using SafeMath for uint;

  /// @dev Computes round-up division.
  function ceilDiv(uint a, uint b) internal pure returns (uint) {
    return a.add(b).sub(1).div(b);
  }
}

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

contract HomoraBank is Governable, ERC1155NaiveReceiver, IBank {
  using SafeMath for uint;
  using HomoraSafeMath for uint;
  using SafeERC20 for IERC20;

  uint private constant _NOT_ENTERED = 1;
  uint private constant _ENTERED = 2;
  uint private constant _NO_ID = uint(-1);
  address private constant _NO_ADDRESS = address(1);

  struct Bank {
    bool isListed; // Whether this market exists.
    uint8 index; // Reverse look up index for this bank.
    address cToken; // The CToken to draw liquidity from.
    uint reserve; // The reserve portion allocated to Homora protocol.
    uint totalDebt; // The last recorded total debt since last action.
    uint totalShare; // The total debt share count across all open positions.
  }

  struct Position {
    address owner; // The owner of this position.
    address collToken; // The ERC1155 token used as collateral for this position.
    uint collId; // The token id used as collateral.
    uint collateralSize; // The size of collateral token for this position.
    uint debtMap; // Bitmap of nonzero debt. i^th bit is set iff debt share of i^th bank is nonzero.
    mapping(address => uint) debtShareOf; // The debt share for each token.
  }

  uint public _GENERAL_LOCK; // TEMPORARY: re-entrancy lock guard.
  uint public _IN_EXEC_LOCK; // TEMPORARY: exec lock guard.
  uint public override POSITION_ID; // TEMPORARY: position ID currently under execution.
  address public override SPELL; // TEMPORARY: spell currently under execution.

  address public caster; // The caster address for untrusted execution.
  IOracle public oracle; // The oracle address for determining prices.
  uint public feeBps; // The fee collected as protocol reserve in basis points from interest.
  uint public override nextPositionId; // Next available position ID, starting from 1 (see initialize).

  address[] public allBanks; // The list of all listed banks.
  mapping(address => Bank) public banks; // Mapping from token to bank data.
  mapping(address => bool) public cTokenInBank; // Mapping from cToken to its existence in bank.
  mapping(uint => Position) public positions; // Mapping from position ID to position data.

  bool public allowContractCalls; // The boolean status whether to allow call from contract (false = onlyEOA)
  mapping(address => bool) public whitelistedTokens; // Mapping from token to whitelist status
  mapping(address => bool) public whitelistedSpells; // Mapping from spell to whitelist status
  mapping(address => bool) public whitelistedUsers; // Mapping from user to whitelist status

  uint public bankStatus; // Each bit stores certain bank status, e.g. borrow allowed, repay allowed

  /// @dev Ensure that the function is called from EOA when allowContractCalls is set to false and caller is not whitelisted
  modifier onlyEOAEx() {
    if (!allowContractCalls && !whitelistedUsers[msg.sender]) {
      require(msg.sender == tx.origin, 'not eoa');
    }
    _;
  }

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
  function initialize(IOracle _oracle, uint _feeBps) external initializer {
    __Governable__init();
    _GENERAL_LOCK = _NOT_ENTERED;
    _IN_EXEC_LOCK = _NOT_ENTERED;
    POSITION_ID = _NO_ID;
    SPELL = _NO_ADDRESS;
    caster = address(new HomoraCaster());
    oracle = _oracle;
    require(address(_oracle) != address(0), 'bad oracle address');
    feeBps = _feeBps;
    nextPositionId = 1;
    bankStatus = 3; // allow both borrow and repay
    emit SetOracle(address(_oracle));
    emit SetFeeBps(_feeBps);
  }

  /// @dev Return the current executor (the owner of the current position).
  function EXECUTOR() external view override returns (address) {
    uint positionId = POSITION_ID;
    require(positionId != _NO_ID, 'not under execution');
    return positions[positionId].owner;
  }

  /// @dev Set allowContractCalls
  /// @param ok The status to set allowContractCalls to (false = onlyEOA)
  function setAllowContractCalls(bool ok) external onlyGov {
    allowContractCalls = ok;
  }

  /// @dev Set whitelist spell status
  /// @param spells list of spells to change status
  /// @param statuses list of statuses to change to
  function setWhitelistSpells(address[] calldata spells, bool[] calldata statuses)
    external
    onlyGov
  {
    require(spells.length == statuses.length, 'spells & statuses length mismatched');
    for (uint idx = 0; idx < spells.length; idx++) {
      whitelistedSpells[spells[idx]] = statuses[idx];
    }
  }

  /// @dev Set whitelist token status
  /// @param tokens list of tokens to change status
  /// @param statuses list of statuses to change to
  function setWhitelistTokens(address[] calldata tokens, bool[] calldata statuses)
    external
    onlyGov
  {
    require(tokens.length == statuses.length, 'tokens & statuses length mismatched');
    for (uint idx = 0; idx < tokens.length; idx++) {
      if (statuses[idx]) {
        // check oracle suppport
        require(support(tokens[idx]), 'oracle not support token');
      }
      whitelistedTokens[tokens[idx]] = statuses[idx];
    }
  }

  /// @dev Set whitelist user status
  /// @param users list of users to change status
  /// @param statuses list of statuses to change to
  function setWhitelistUsers(address[] calldata users, bool[] calldata statuses) external onlyGov {
    require(users.length == statuses.length, 'users & statuses length mismatched');
    for (uint idx = 0; idx < users.length; idx++) {
      whitelistedUsers[users[idx]] = statuses[idx];
    }
  }

  /// @dev Check whether the oracle supports the token
  /// @param token ERC-20 token to check for support
  function support(address token) public view override returns (bool) {
    return oracle.support(token);
  }

  /// @dev Set bank status
  /// @param _bankStatus new bank status to change to
  function setBankStatus(uint _bankStatus) external onlyGov {
    bankStatus = _bankStatus;
  }

  /// @dev Bank borrow status allowed or not
  /// @notice check last bit of bankStatus
  function allowBorrowStatus() public view returns (bool) {
    return (bankStatus & 0x01) > 0;
  }

  /// @dev Bank repay status allowed or not
  /// @notice Check second-to-last bit of bankStatus
  function allowRepayStatus() public view returns (bool) {
    return (bankStatus & 0x02) > 0;
  }

  /// @dev Trigger interest accrual for the given bank.
  /// @param token The underlying token to trigger the interest accrual.
  function accrue(address token) public override {
    Bank storage bank = banks[token];
    require(bank.isListed, 'bank not exist');
    uint totalDebt = bank.totalDebt;
    uint debt = ICErc20(bank.cToken).borrowBalanceCurrent(address(this));
    if (debt > totalDebt) {
      uint fee = debt.sub(totalDebt).mul(feeBps).div(10000);
      bank.totalDebt = debt;
      bank.reserve = bank.reserve.add(doBorrow(token, fee));
    } else if (totalDebt != debt) {
      // We should never reach here because CREAMv2 does not support *repayBorrowBehalf*
      // functionality. We set bank.totalDebt = debt nonetheless to ensure consistency. But do
      // note that if *repayBorrowBehalf* exists, an attacker can maliciously deflate debt
      // share value and potentially make this contract stop working due to math overflow.
      bank.totalDebt = debt;
    }
  }

  /// @dev Convenient function to trigger interest accrual for a list of banks.
  /// @param tokens The list of banks to trigger interest accrual.
  function accrueAll(address[] memory tokens) external {
    for (uint idx = 0; idx < tokens.length; idx++) {
      accrue(tokens[idx]);
    }
  }

  /// @dev Return the borrow balance for given position and token without triggering interest accrual.
  /// @param positionId The position to query for borrow balance.
  /// @param token The token to query for borrow balance.
  function borrowBalanceStored(uint positionId, address token) public view override returns (uint) {
    uint totalDebt = banks[token].totalDebt;
    uint totalShare = banks[token].totalShare;
    uint share = positions[positionId].debtShareOf[token];
    if (share == 0 || totalDebt == 0) {
      return 0;
    } else {
      return share.mul(totalDebt).ceilDiv(totalShare);
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
    public
    view
    override
    returns (
      address owner,
      address collToken,
      uint collId,
      uint collateralSize
    )
  {
    Position storage pos = positions[positionId];
    return (pos.owner, pos.collToken, pos.collId, pos.collateralSize);
  }

  /// @dev Return current position information
  function getCurrentPositionInfo()
    external
    view
    override
    returns (
      address owner,
      address collToken,
      uint collId,
      uint collateralSize
    )
  {
    require(POSITION_ID != _NO_ID, 'no id');
    return getPositionInfo(POSITION_ID);
  }

  /// @dev Return the debt share of the given bank token for the given position id.
  /// @param positionId position id to get debt of
  /// @param token ERC20 debt token to query
  function getPositionDebtShareOf(uint positionId, address token) external view returns (uint) {
    return positions[positionId].debtShareOf[token];
  }

  /// @dev Return the list of all debts for the given position id.
  /// @param positionId position id to get debts of
  function getPositionDebts(uint positionId)
    external
    view
    returns (address[] memory tokens, uint[] memory debts)
  {
    Position storage pos = positions[positionId];
    uint count = 0;
    uint bitMap = pos.debtMap;
    while (bitMap > 0) {
      if ((bitMap & 1) != 0) {
        count++;
      }
      bitMap >>= 1;
    }
    tokens = new address[](count);
    debts = new uint[](count);
    bitMap = pos.debtMap;
    count = 0;
    uint idx = 0;
    while (bitMap > 0) {
      if ((bitMap & 1) != 0) {
        address token = allBanks[idx];
        Bank storage bank = banks[token];
        tokens[count] = token;
        debts[count] = pos.debtShareOf[token].mul(bank.totalDebt).ceilDiv(bank.totalShare);
        count++;
      }
      idx++;
      bitMap >>= 1;
    }
  }

  /// @dev Return the total collateral value of the given position in ETH.
  /// @param positionId The position ID to query for the collateral value.
  function getCollateralETHValue(uint positionId) public view returns (uint) {
    Position storage pos = positions[positionId];
    uint size = pos.collateralSize;
    if (size == 0) {
      return 0;
    } else {
      require(pos.collToken != address(0), 'bad collateral token');
      return oracle.asETHCollateral(pos.collToken, pos.collId, size, pos.owner);
    }
  }

  /// @dev Return the total borrow value of the given position in ETH.
  /// @param positionId The position ID to query for the borrow value.
  function getBorrowETHValue(uint positionId) public view override returns (uint) {
    uint value = 0;
    Position storage pos = positions[positionId];
    address owner = pos.owner;
    uint bitMap = pos.debtMap;
    uint idx = 0;
    while (bitMap > 0) {
      if ((bitMap & 1) != 0) {
        address token = allBanks[idx];
        uint share = pos.debtShareOf[token];
        Bank storage bank = banks[token];
        uint debt = share.mul(bank.totalDebt).ceilDiv(bank.totalShare);
        value = value.add(oracle.asETHBorrow(token, debt, owner));
      }
      idx++;
      bitMap >>= 1;
    }
    return value;
  }

  /// @dev Add a new bank to the ecosystem.
  /// @param token The underlying token for the bank.
  /// @param cToken The address of the cToken smart contract.
  function addBank(address token, address cToken) external onlyGov {
    Bank storage bank = banks[token];
    require(!cTokenInBank[cToken], 'cToken already exists');
    require(!bank.isListed, 'bank already exists');
    cTokenInBank[cToken] = true;
    bank.isListed = true;
    require(allBanks.length < 256, 'reach bank limit');
    bank.index = uint8(allBanks.length);
    bank.cToken = cToken;
    IERC20(token).safeApprove(cToken, 0);
    IERC20(token).safeApprove(cToken, uint(-1));
    allBanks.push(token);
    emit AddBank(token, cToken);
  }

  /// @dev Set the oracle smart contract address.
  /// @param _oracle The new oracle smart contract address.
  function setOracle(IOracle _oracle) external onlyGov {
    require(address(_oracle) != address(0), 'cannot set zero address oracle');
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
    require(bank.isListed, 'bank not exist');
    bank.reserve = bank.reserve.sub(amount);
    IERC20(token).safeTransfer(msg.sender, amount);
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
  ) external override lock poke(debtToken) {
    uint collateralValue = getCollateralETHValue(positionId);
    uint borrowValue = getBorrowETHValue(positionId);
    require(collateralValue < borrowValue, 'position still healthy');
    Position storage pos = positions[positionId];
    (uint amountPaid, uint share) = repayInternal(positionId, debtToken, amountCall);
    require(pos.collToken != address(0), 'bad collateral token');
    uint bounty =
      Math.min(
        oracle.convertForLiquidation(debtToken, pos.collToken, pos.collId, amountPaid),
        pos.collateralSize
      );
    pos.collateralSize = pos.collateralSize.sub(bounty);
    IERC1155(pos.collToken).safeTransferFrom(address(this), msg.sender, pos.collId, bounty, '');
    emit Liquidate(positionId, msg.sender, debtToken, amountPaid, share, bounty);
  }

  /// @dev Execute the action via HomoraCaster, calling its function with the supplied data.
  /// @param positionId The position ID to execute the action, or zero for new position.
  /// @param spell The target spell to invoke the execution via HomoraCaster.
  /// @param data Extra data to pass to the target for the execution.
  function execute(
    uint positionId,
    address spell,
    bytes memory data
  ) external payable lock onlyEOAEx returns (uint) {
    require(whitelistedSpells[spell], 'spell not whitelisted');
    if (positionId == 0) {
      positionId = nextPositionId++;
      positions[positionId].owner = msg.sender;
    } else {
      require(positionId < nextPositionId, 'position id not exists');
      require(msg.sender == positions[positionId].owner, 'not position owner');
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

  /// @dev Borrow tokens from that bank. Must only be called while under execution.
  /// @param token The token to borrow from the bank.
  /// @param amount The amount of tokens to borrow.
  function borrow(address token, uint amount) external override inExec poke(token) {
    require(allowBorrowStatus(), 'borrow not allowed');
    require(whitelistedTokens[token], 'token not whitelisted');
    Bank storage bank = banks[token];
    Position storage pos = positions[POSITION_ID];
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint share = totalShare == 0 ? amount : amount.mul(totalShare).ceilDiv(totalDebt);
    bank.totalShare = bank.totalShare.add(share);
    uint newShare = pos.debtShareOf[token].add(share);
    pos.debtShareOf[token] = newShare;
    if (newShare > 0) {
      pos.debtMap |= (1 << uint(bank.index));
    }
    IERC20(token).safeTransfer(msg.sender, doBorrow(token, amount));
    emit Borrow(POSITION_ID, msg.sender, token, amount, share);
  }

  /// @dev Repay tokens to the bank. Must only be called while under execution.
  /// @param token The token to repay to the bank.
  /// @param amountCall The amount of tokens to repay via transferFrom.
  function repay(address token, uint amountCall) external override inExec poke(token) {
    require(allowRepayStatus(), 'repay not allowed');
    require(whitelistedTokens[token], 'token not whitelisted');
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
    Position storage pos = positions[positionId];
    uint totalShare = bank.totalShare;
    uint totalDebt = bank.totalDebt;
    uint oldShare = pos.debtShareOf[token];
    uint oldDebt = oldShare.mul(totalDebt).ceilDiv(totalShare);
    if (amountCall == uint(-1)) {
      amountCall = oldDebt;
    }
    uint paid = doRepay(token, doERC20TransferIn(token, amountCall));
    require(paid <= oldDebt, 'paid exceeds debt'); // prevent share overflow attack
    uint lessShare = paid == oldDebt ? oldShare : paid.mul(totalShare).div(totalDebt);
    bank.totalShare = totalShare.sub(lessShare);
    uint newShare = oldShare.sub(lessShare);
    pos.debtShareOf[token] = newShare;
    if (newShare == 0) {
      pos.debtMap &= ~(1 << uint(bank.index));
    }
    return (paid, lessShare);
  }

  /// @dev Transmit user assets to the caller, so users only need to approve Bank for spending.
  /// @param token The token to transfer from user to the caller.
  /// @param amount The amount to transfer.
  function transmit(address token, uint amount) external override inExec {
    Position storage pos = positions[POSITION_ID];
    IERC20(token).safeTransferFrom(pos.owner, msg.sender, amount);
  }

  /// @dev Put more collateral for users. Must only be called during execution.
  /// @param collToken The ERC1155 token to collateral.
  /// @param collId The token id to collateral.
  /// @param amountCall The amount of tokens to put via transferFrom.
  function putCollateral(
    address collToken,
    uint collId,
    uint amountCall
  ) external override inExec {
    Position storage pos = positions[POSITION_ID];
    if (pos.collToken != collToken || pos.collId != collId) {
      require(oracle.supportWrappedToken(collToken, collId), 'collateral not supported');
      require(pos.collateralSize == 0, 'another type of collateral already exists');
      pos.collToken = collToken;
      pos.collId = collId;
    }
    uint amount = doERC1155TransferIn(collToken, collId, amountCall);
    pos.collateralSize = pos.collateralSize.add(amount);
    emit PutCollateral(POSITION_ID, msg.sender, collToken, collId, amount);
  }

  /// @dev Take some collateral back. Must only be called during execution.
  /// @param collToken The ERC1155 token to take back.
  /// @param collId The token id to take back.
  /// @param amount The amount of tokens to take back via transfer.
  function takeCollateral(
    address collToken,
    uint collId,
    uint amount
  ) external override inExec {
    Position storage pos = positions[POSITION_ID];
    require(collToken == pos.collToken, 'invalid collateral token');
    require(collId == pos.collId, 'invalid collateral token');
    if (amount == uint(-1)) {
      amount = pos.collateralSize;
    }
    pos.collateralSize = pos.collateralSize.sub(amount);
    IERC1155(collToken).safeTransferFrom(address(this), msg.sender, collId, amount, '');
    emit TakeCollateral(POSITION_ID, msg.sender, collToken, collId, amount);
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
    require(cToken.repayBorrow(amountCall) == 0, 'bad repay');
    uint newDebt = cToken.borrowBalanceStored(address(this));
    bank.totalDebt = newDebt;
    return oldDebt.sub(newDebt);
  }

  /// @dev Internal function to perform ERC20 transfer in and return amount actually received.
  /// @param token The token to perform transferFrom action.
  /// @param amountCall The amount use in the transferFrom call.
  function doERC20TransferIn(address token, uint amountCall) internal returns (uint) {
    uint balanceBefore = IERC20(token).balanceOf(address(this));
    IERC20(token).safeTransferFrom(msg.sender, address(this), amountCall);
    uint balanceAfter = IERC20(token).balanceOf(address(this));
    return balanceAfter.sub(balanceBefore);
  }

  /// @dev Internal function to perform ERC1155 transfer in and return amount actually received.
  /// @param token The token to perform transferFrom action.
  /// @param id The id to perform transferFrom action.
  /// @param amountCall The amount use in the transferFrom call.
  function doERC1155TransferIn(
    address token,
    uint id,
    uint amountCall
  ) internal returns (uint) {
    uint balanceBefore = IERC1155(token).balanceOf(address(this), id);
    IERC1155(token).safeTransferFrom(msg.sender, address(this), id, amountCall, '');
    uint balanceAfter = IERC1155(token).balanceOf(address(this), id);
    return balanceAfter.sub(balanceBefore);
  }
}
