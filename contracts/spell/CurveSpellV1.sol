pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import './BasicSpell.sol';
import '../utils/HomoraMath.sol';
import '../../interfaces/ICurvePool.sol';

contract CurveSpellV1 is BasicSpell {
  using SafeMath for uint;
  using HomoraMath for uint;

  mapping(address => address[]) public pools; // lpToken -> underlying token array
  mapping(address => address) public poolOf; // lpToken -> pool

  constructor(IBank _bank, address _werc20)
    public
    BasicSpell(_bank, _werc20, 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2)
  {}

  // TODO:
  function addPoolOf(address lp, address pool) public {
    poolOf[lp] = pool;
  }

  // TODO:
  function addPools(address lp, address[] calldata tokens) public {
    pools[lp] = tokens;
  }

  event Y1(uint pos, address spell);
  event Y2(uint pos, address spell);
  event Y3(uint pos, address spell);
  event Y4(uint pos, address spell);
  event Y5(uint pos, address spell);
  event YX(uint pos, address spell);

  function ensureApproveAll(address lp) public {
    address pool = poolOf[lp];
    for (uint idx = 0; ; idx++) {
      if (idx == 0) emit Y1(bank.POSITION_ID(), bank.SPELL());
      if (idx == 1) emit Y2(bank.POSITION_ID(), bank.SPELL());
      if (idx == 2) emit Y3(bank.POSITION_ID(), bank.SPELL());
      if (idx == 3) emit Y4(bank.POSITION_ID(), bank.SPELL());
      try ICurvePool(pool).coins(idx) returns (address coin) {
        ensureApprove(coin, pool);
      } catch (bytes memory) {
        emit YX(bank.POSITION_ID(), bank.SPELL());
        break;
      }
    }
    emit Y5(bank.POSITION_ID(), bank.SPELL());
  }

  event X1(uint pos, address spell);
  event X2(uint pos, address spell);
  event X3(uint pos, address spell);

  function addLiquidity(
    address lp,
    uint[] calldata amtsUser,
    uint amtLPUser,
    uint[] calldata amtsBorrow,
    uint amtLPBorrow,
    uint[] calldata amtsMin
  ) external payable {
    emit X1(bank.POSITION_ID(), bank.SPELL());
    uint l = amtsUser.length;
    address[] memory tokens = pools[lp];

    emit X2(bank.POSITION_ID(), bank.SPELL());
    // 0. Ensure approve
    ensureApproveAll(lp);

    emit X3(bank.POSITION_ID(), bank.SPELL());
    doTransmit(tokens[1], 1);
    return;

    // 1. Get user input amounts
    for (uint i = 0; i < l; i++) doTransmit(tokens[i], amtsUser[i]);
    doTransmit(lp, amtLPUser);

    // 2. Borrow specified amounts
    for (uint i = 0; i < l; i++) doBorrow(tokens[i], amtsBorrow[i]);
    doBorrow(lp, amtLPBorrow);

    // 3. add liquidity
    uint[] memory suppliedAmts = new uint[](l);
    for (uint i = 0; i < l; i++) {
      suppliedAmts[i] = IERC20(pools[lp][i]).balanceOf(address(this));
    }
    ICurvePool(poolOf[lp]).add_liquidity(suppliedAmts, amtsMin);

    // 4. Put collateral
    doPutCollateral(lp, IERC20(lp).balanceOf(address(this)));

    // 5. Refund
    for (uint i = 0; i < l; i++) doRefund(tokens[i]);
  }

  function removeLiquidity(
    address lp,
    uint amtLPTake,
    uint amtLPWithdraw,
    uint[] calldata amtsRepay,
    uint amtLPRepay,
    uint[] calldata amtsMin
  ) external payable {
    uint l = amtsRepay.length;
    uint positionId = bank.POSITION_ID();
    address[] memory tokens = pools[lp];
    uint[] memory amtsDesired = amtsRepay;
    for (uint i = 0; i < l; i++) amtsDesired[i] += amtsMin[i]; // repay amt + slippage control

    // 0. Ensure approve
    ensureApproveAll(lp);

    // 1. Compute repay amount if MAX_INT is supplied (max debt)
    uint[] memory actualAmtsRepay = amtsRepay;
    for (uint i = 0; i < l; i++) {
      if (amtsRepay[i] == uint(-1)) {
        actualAmtsRepay[i] = bank.borrowBalanceCurrent(positionId, tokens[i]);
      }
    }

    // 2. Take out collateral
    doTakeCollateral(lp, amtLPTake);

    // 3. Compute amount to actually remove
    uint amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);

    // 4. Remove to repay just enough
    ICurvePool(poolOf[lp]).remove_liquidity_imbalance(amtsDesired, uint(-1));

    // 5. Repay
    for (uint i = 0; i < l; i++) {
      doRepay(tokens[i], amtsRepay[i]);
    }
    doRepay(lp, amtLPRepay);

    // 6. Refund
    for (uint i = 0; i < l; i++) {
      doRefund(tokens[i]);
    }
    doRefund(lp);
  }
}
