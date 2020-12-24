pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import './BasicSpell.sol';
import '../utils/HomoraMath.sol';
import '../../interfaces/ICurvePool.sol';
import '../../interfaces/ICurveRegistry.sol';

contract CurveSpellV1 is BasicSpell {
  using SafeMath for uint;
  using HomoraMath for uint;

  ICurveRegistry registry;
  mapping(address => address[]) public ulTokens; // lpToken -> underlying token array
  mapping(address => address) public poolOf; // lpToken -> pool

  constructor(
    IBank _bank,
    address _werc20,
    address _weth,
    address _registry
  ) public BasicSpell(_bank, _werc20, _weth) {
    registry = ICurveRegistry(_registry);
  }

  /// @dev Return pool address given LP token and update pool info if not exist.
  /// @param lp LP token to find the corresponding pool.
  function getPool(address lp) public returns (address) {
    address pool = poolOf[lp];
    if (pool == address(0)) {
      require(lp != address(0), 'no lp token');
      pool = registry.get_pool_from_lp_token(lp);
      require(pool != address(0), 'no corresponding pool for lp token');
      poolOf[lp] = pool;
      uint n = registry.get_n_coins(pool);
      address[8] memory tokens = registry.get_coins(pool);
      ulTokens[lp] = new address[](n);
      for (uint i = 0; i < n; i++) {
        ulTokens[lp][i] = tokens[i];
      }
    }
    return pool;
  }

  function ensureApprove3(address lp) public {
    require(ulTokens[lp].length == 3, 'incorrect pool length');
    address pool = poolOf[lp];
    for (uint idx = 0; idx < 3; idx++) {
      address coin = ICurvePool(pool).coins(idx);
      ensureApprove(coin, pool);
    }
  }

  /// @dev add liquidity for pools with 3 underlying tokens
  function addLiquidity3(
    address lp,
    uint[3] calldata amtsUser,
    uint amtLPUser,
    uint[3] calldata amtsBorrow,
    uint amtLPBorrow,
    uint minLPMint
  ) external payable {
    address pool = getPool(lp);
    require(ulTokens[lp].length == 3, 'incorrect pool length');
    address[] memory tokens = ulTokens[lp];

    // 0. Ensure approve 3 underlying tokens
    ensureApprove3(lp);

    // 1. Get user input amounts
    for (uint i = 0; i < 3; i++) doTransmit(tokens[i], amtsUser[i]);
    doTransmit(lp, amtLPUser);

    // 2. Borrow specified amounts
    for (uint i = 0; i < 3; i++) doBorrow(tokens[i], amtsBorrow[i]);
    doBorrow(lp, amtLPBorrow);

    // 3. add liquidity
    uint[3] memory suppliedAmts;
    for (uint i = 0; i < 3; i++) {
      suppliedAmts[i] = IERC20(tokens[i]).balanceOf(address(this));
    }
    ICurvePool(pool).add_liquidity(suppliedAmts, minLPMint);

    // 4. Put collateral
    doPutCollateral(lp, IERC20(lp).balanceOf(address(this)));

    // 5. Refund
    for (uint i = 0; i < 3; i++) doRefund(tokens[i]);
  }

  function removeLiquidity3(
    address lp,
    uint amtLPTake,
    uint amtLPWithdraw,
    uint[3] calldata amtsRepay,
    uint amtLPRepay,
    uint[3] calldata amtsMin
  ) external payable {
    address pool = getPool(lp);
    uint positionId = bank.POSITION_ID();
    address[] memory tokens = ulTokens[lp];

    // 0. Ensure approve
    ensureApprove3(lp);

    // 1. Compute repay amount if MAX_INT is supplied (max debt)
    uint[3] memory actualAmtsRepay;
    for (uint i = 0; i < 3; i++) {
      actualAmtsRepay[i] = amtsRepay[i] == uint(-1)
        ? bank.borrowBalanceCurrent(positionId, tokens[i])
        : amtsRepay[i];
    }
    uint[3] memory amtsDesired;
    for (uint i = 0; i < 3; i++) amtsDesired[i] += actualAmtsRepay[i].add(amtsMin[i]); // repay amt + slippage control

    // 2. Take out collateral
    doTakeCollateral(lp, amtLPTake);

    // 3. Compute amount to actually remove. Remove to repay just enough
    uint amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
    ICurvePool(pool).remove_liquidity_imbalance(amtsDesired, amtLPToRemove);

    // 4. Compute leftover amount to remove. Remove balancedly.
    amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
    uint[3] memory mins;
    ICurvePool(pool).remove_liquidity(amtLPToRemove, mins);

    // 5. Repay
    for (uint i = 0; i < 3; i++) {
      doRepay(tokens[i], actualAmtsRepay[i]);
    }
    doRepay(lp, amtLPRepay);

    // 6. Refund
    for (uint i = 0; i < 3; i++) {
      doRefund(tokens[i]);
    }
    doRefund(lp);
  }
}
