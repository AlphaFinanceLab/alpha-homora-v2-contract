// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import './WhitelistSpell.sol';
import '../utils/HomoraMath.sol';
import '../../interfaces/ICurvePool.sol';
import '../../interfaces/ICurveRegistry.sol';
import '../../interfaces/IWLiquidityGauge.sol';

contract CurveSpellV1 is WhitelistSpell {
  using SafeMath for uint;
  using HomoraMath for uint;

  ICurveRegistry public immutable registry; // Curve registry
  IWLiquidityGauge public immutable wgauge; // Wrapped liquidity gauge
  address public immutable crv; // CRV token address
  mapping(address => address[]) public ulTokens; // Mapping from LP token address -> underlying token addresses
  mapping(address => address) public poolOf; // Mapping from LP token address to -> pool address

  constructor(
    IBank _bank,
    address _werc20,
    address _weth,
    address _wgauge
  ) public WhitelistSpell(_bank, _werc20, _weth) {
    wgauge = IWLiquidityGauge(_wgauge);
    IWLiquidityGauge(_wgauge).setApprovalForAll(address(_bank), true);
    registry = IWLiquidityGauge(_wgauge).registry();
    crv = address(IWLiquidityGauge(_wgauge).crv());
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
      (uint n, ) = registry.get_n_coins(pool);
      address[8] memory tokens = registry.get_coins(pool);
      ulTokens[lp] = new address[](n);
      for (uint i = 0; i < n; i++) {
        ulTokens[lp][i] = tokens[i];
      }
    }
    return pool;
  }

  /// @dev Ensure approval of underlying tokens to the corresponding Curve pool
  /// @param lp LP token for the pool
  /// @param n Number of pool's underlying tokens
  function ensureApproveN(address lp, uint n) public {
    require(ulTokens[lp].length == n, 'incorrect pool length');
    address pool = poolOf[lp];
    address[] memory tokens = ulTokens[lp];
    for (uint idx = 0; idx < n; idx++) {
      ensureApprove(tokens[idx], pool);
    }
  }

  /// @dev Add liquidity to Curve pool with 2 underlying tokens, with staking to Curve gauge
  /// @param lp LP token for the pool
  /// @param amtsUser Supplied underlying token amounts
  /// @param amtLPUser Supplied LP token amount
  /// @param amtsBorrow Borrow underlying token amounts
  /// @param amtLPBorrow Borrow LP token amount
  /// @param minLPMint Desired LP token amount (slippage control)
  /// @param pid Curve pool id for the pool
  /// @param gid Curve gauge id for the pool
  function addLiquidity2(
    address lp,
    uint[2] calldata amtsUser,
    uint amtLPUser,
    uint[2] calldata amtsBorrow,
    uint amtLPBorrow,
    uint minLPMint,
    uint pid,
    uint gid
  ) external {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    address pool = getPool(lp);
    require(ulTokens[lp].length == 2, 'incorrect pool length');
    require(wgauge.getUnderlyingTokenFromIds(pid, gid) == lp, 'incorrect underlying');
    address[] memory tokens = ulTokens[lp];

    // 0. Take out collateral
    (, address collToken, uint collId, uint collSize) = bank.getCurrentPositionInfo();
    if (collSize > 0) {
      (uint decodedPid, uint decodedGid, ) = wgauge.decodeId(collId);
      require(decodedPid == pid && decodedGid == gid, 'bad pid or gid');
      require(collToken == address(wgauge), 'collateral token & wgauge mismatched');
      bank.takeCollateral(address(wgauge), collId, collSize);
      wgauge.burn(collId, collSize);
    }

    // 1. Ensure approve 2 underlying tokens
    ensureApproveN(lp, 2);

    // 2. Get user input amounts
    for (uint i = 0; i < 2; i++) doTransmit(tokens[i], amtsUser[i]);
    doTransmit(lp, amtLPUser);

    // 3. Borrow specified amounts
    for (uint i = 0; i < 2; i++) doBorrow(tokens[i], amtsBorrow[i]);
    doBorrow(lp, amtLPBorrow);

    // 4. add liquidity
    uint[2] memory suppliedAmts;
    for (uint i = 0; i < 2; i++) {
      suppliedAmts[i] = IERC20(tokens[i]).balanceOf(address(this));
    }
    if (suppliedAmts[0] > 0 || suppliedAmts[1] > 0) {
      ICurvePool(pool).add_liquidity(suppliedAmts, minLPMint);
    }

    // 5. Put collateral
    ensureApprove(lp, address(wgauge));
    {
      uint amount = IERC20(lp).balanceOf(address(this));
      uint id = wgauge.mint(pid, gid, amount);
      bank.putCollateral(address(wgauge), id, amount);
    }

    // 6. Refund
    for (uint i = 0; i < 2; i++) doRefund(tokens[i]);

    // 7. Refund crv
    doRefund(crv);
  }

  /// @dev Add liquidity to Curve pool with 3 underlying tokens, with staking to Curve gauge
  /// @param lp LP token for the pool
  /// @param amtsUser Supplied underlying token amounts
  /// @param amtLPUser Supplied LP token amount
  /// @param amtsBorrow Borrow underlying token amounts
  /// @param amtLPBorrow Borrow LP token amount
  /// @param minLPMint Desired LP token amount (slippage control)
  /// @param pid CUrve pool id for the pool
  /// @param gid Curve gauge id for the pool
  function addLiquidity3(
    address lp,
    uint[3] calldata amtsUser,
    uint amtLPUser,
    uint[3] calldata amtsBorrow,
    uint amtLPBorrow,
    uint minLPMint,
    uint pid,
    uint gid
  ) external {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    address pool = getPool(lp);
    require(ulTokens[lp].length == 3, 'incorrect pool length');
    require(wgauge.getUnderlyingTokenFromIds(pid, gid) == lp, 'incorrect underlying');
    address[] memory tokens = ulTokens[lp];

    // 0. take out collateral
    (, address collToken, uint collId, uint collSize) = bank.getCurrentPositionInfo();
    if (collSize > 0) {
      (uint decodedPid, uint decodedGid, ) = wgauge.decodeId(collId);
      require(decodedPid == pid && decodedGid == gid, 'incorrect coll id');
      require(collToken == address(wgauge), 'collateral token & wgauge mismatched');
      bank.takeCollateral(address(wgauge), collId, collSize);
      wgauge.burn(collId, collSize);
    }

    // 1. Ensure approve 3 underlying tokens
    ensureApproveN(lp, 3);

    // 2. Get user input amounts
    for (uint i = 0; i < 3; i++) doTransmit(tokens[i], amtsUser[i]);
    doTransmit(lp, amtLPUser);

    // 3. Borrow specified amounts
    for (uint i = 0; i < 3; i++) doBorrow(tokens[i], amtsBorrow[i]);
    doBorrow(lp, amtLPBorrow);

    // 4. add liquidity
    uint[3] memory suppliedAmts;
    for (uint i = 0; i < 3; i++) {
      suppliedAmts[i] = IERC20(tokens[i]).balanceOf(address(this));
    }
    if (suppliedAmts[0] > 0 || suppliedAmts[1] > 0 || suppliedAmts[2] > 0) {
      ICurvePool(pool).add_liquidity(suppliedAmts, minLPMint);
    }

    // 5. put collateral
    ensureApprove(lp, address(wgauge));
    {
      uint amount = IERC20(lp).balanceOf(address(this));
      uint id = wgauge.mint(pid, gid, amount);
      bank.putCollateral(address(wgauge), id, amount);
    }

    // 6. Refund
    for (uint i = 0; i < 3; i++) doRefund(tokens[i]);

    // 7. Refund crv
    doRefund(crv);
  }

  /// @dev Add liquidity to Curve pool with 4 underlying tokens, with staking to Curve gauge
  /// @param lp LP token for the pool
  /// @param amtsUser Supplied underlying token amounts
  /// @param amtLPUser Supplied LP token amount
  /// @param amtsBorrow Borrow underlying token amounts
  /// @param amtLPBorrow Borrow LP token amount
  /// @param minLPMint Desired LP token amount (slippage control)
  /// @param pid CUrve pool id for the pool
  /// @param gid Curve gauge id for the pool
  function addLiquidity4(
    address lp,
    uint[4] calldata amtsUser,
    uint amtLPUser,
    uint[4] calldata amtsBorrow,
    uint amtLPBorrow,
    uint minLPMint,
    uint pid,
    uint gid
  ) external {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    address pool = getPool(lp);
    require(ulTokens[lp].length == 4, 'incorrect pool length');
    require(wgauge.getUnderlyingTokenFromIds(pid, gid) == lp, 'incorrect underlying');
    address[] memory tokens = ulTokens[lp];

    // 0. Take out collateral
    (, address collToken, uint collId, uint collSize) = bank.getCurrentPositionInfo();
    if (collSize > 0) {
      (uint decodedPid, uint decodedGid, ) = wgauge.decodeId(collId);
      require(decodedPid == pid && decodedGid == gid, 'incorrect coll id');
      require(collToken == address(wgauge), 'collateral token & wgauge mismatched');
      bank.takeCollateral(address(wgauge), collId, collSize);
      wgauge.burn(collId, collSize);
    }

    // 1. Ensure approve 4 underlying tokens
    ensureApproveN(lp, 4);

    // 2. Get user input amounts
    for (uint i = 0; i < 4; i++) doTransmit(tokens[i], amtsUser[i]);
    doTransmit(lp, amtLPUser);

    // 3. Borrow specified amounts
    for (uint i = 0; i < 4; i++) doBorrow(tokens[i], amtsBorrow[i]);
    doBorrow(lp, amtLPBorrow);

    // 4. add liquidity
    uint[4] memory suppliedAmts;
    for (uint i = 0; i < 4; i++) {
      suppliedAmts[i] = IERC20(tokens[i]).balanceOf(address(this));
    }
    if (suppliedAmts[0] > 0 || suppliedAmts[1] > 0 || suppliedAmts[2] > 0 || suppliedAmts[3] > 0) {
      ICurvePool(pool).add_liquidity(suppliedAmts, minLPMint);
    }

    // 5. Put collateral
    ensureApprove(lp, address(wgauge));
    {
      uint amount = IERC20(lp).balanceOf(address(this));
      uint id = wgauge.mint(pid, gid, amount);
      bank.putCollateral(address(wgauge), id, amount);
    }

    // 6. Refund
    for (uint i = 0; i < 4; i++) doRefund(tokens[i]);

    // 7. Refund crv
    doRefund(crv);
  }

  /// @dev Remove liquidity from Curve pool with 2 underlying tokens
  /// @param lp LP token for the pool
  /// @param amtLPTake Take out LP token amount (from Homora)
  /// @param amtLPWithdraw Withdraw LP token amount (back to caller)
  /// @param amtsRepay Repay underlying token amounts
  /// @param amtLPRepay Repay LP token amount
  /// @param amtsMin Desired underlying token amounts (slippage control)
  function removeLiquidity2(
    address lp,
    uint amtLPTake,
    uint amtLPWithdraw,
    uint[2] calldata amtsRepay,
    uint amtLPRepay,
    uint[2] calldata amtsMin
  ) external {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    address pool = getPool(lp);
    uint positionId = bank.POSITION_ID();
    (, address collToken, uint collId, ) = bank.getPositionInfo(positionId);
    require(IWLiquidityGauge(collToken).getUnderlyingToken(collId) == lp, 'incorrect underlying');
    require(collToken == address(wgauge), 'collateral token & wgauge mismatched');
    address[] memory tokens = ulTokens[lp];

    // 0. Ensure approve
    ensureApproveN(lp, 2);

    // 1. Compute repay amount if MAX_INT is supplied (max debt)
    uint[2] memory actualAmtsRepay;
    for (uint i = 0; i < 2; i++) {
      actualAmtsRepay[i] = amtsRepay[i] == uint(-1)
        ? bank.borrowBalanceCurrent(positionId, tokens[i])
        : amtsRepay[i];
    }
    uint[2] memory amtsDesired;
    for (uint i = 0; i < 2; i++) {
      amtsDesired[i] = actualAmtsRepay[i].add(amtsMin[i]); // repay amt + slippage control
    }

    // 2. Take out collateral
    bank.takeCollateral(address(wgauge), collId, amtLPTake);
    wgauge.burn(collId, amtLPTake);

    // 3. Compute amount to actually remove. Remove to repay just enough
    uint amtLPToRemove;
    if (amtsDesired[0] > 0 || amtsDesired[1] > 0) {
      amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
      ICurvePool(pool).remove_liquidity_imbalance(amtsDesired, amtLPToRemove);
    }

    // 4. Compute leftover amount to remove. Remove balancedly.
    amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
    if (amtLPToRemove > 0) {
      uint[2] memory mins;
      ICurvePool(pool).remove_liquidity(amtLPToRemove, mins);
    }
    // 5. Repay
    for (uint i = 0; i < 2; i++) {
      doRepay(tokens[i], actualAmtsRepay[i]);
    }
    doRepay(lp, amtLPRepay);

    // 6. Refund
    for (uint i = 0; i < 2; i++) {
      doRefund(tokens[i]);
    }
    doRefund(lp);

    // 7. Refund crv
    doRefund(crv);
  }

  /// @dev Remove liquidity from Curve pool with 3 underlying tokens
  /// @param lp LP token for the pool
  /// @param amtLPTake Take out LP token amount (from Homora)
  /// @param amtLPWithdraw Withdraw LP token amount (back to caller)
  /// @param amtsRepay Repay underlying token amounts
  /// @param amtLPRepay Repay LP token amount
  /// @param amtsMin Desired underlying token amounts (slippage control)
  function removeLiquidity3(
    address lp,
    uint amtLPTake,
    uint amtLPWithdraw,
    uint[3] calldata amtsRepay,
    uint amtLPRepay,
    uint[3] calldata amtsMin
  ) external {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    address pool = getPool(lp);
    uint positionId = bank.POSITION_ID();
    (, address collToken, uint collId, ) = bank.getPositionInfo(positionId);
    require(IWLiquidityGauge(collToken).getUnderlyingToken(collId) == lp, 'incorrect underlying');
    require(collToken == address(wgauge), 'collateral token & wgauge mismatched');
    address[] memory tokens = ulTokens[lp];

    // 0. Ensure approve
    ensureApproveN(lp, 3);

    // 1. Compute repay amount if MAX_INT is supplied (max debt)
    uint[3] memory actualAmtsRepay;
    for (uint i = 0; i < 3; i++) {
      actualAmtsRepay[i] = amtsRepay[i] == uint(-1)
        ? bank.borrowBalanceCurrent(positionId, tokens[i])
        : amtsRepay[i];
    }
    uint[3] memory amtsDesired;
    for (uint i = 0; i < 3; i++) {
      amtsDesired[i] = actualAmtsRepay[i].add(amtsMin[i]); // repay amt + slippage control
    }

    // 2. Take out collateral
    bank.takeCollateral(address(wgauge), collId, amtLPTake);
    wgauge.burn(collId, amtLPTake);

    // 3. Compute amount to actually remove. Remove to repay just enough
    uint amtLPToRemove;
    if (amtsDesired[0] > 0 || amtsDesired[1] > 0 || amtsDesired[2] > 0) {
      amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
      ICurvePool(pool).remove_liquidity_imbalance(amtsDesired, amtLPToRemove);
    }

    // 4. Compute leftover amount to remove. Remove balancedly.
    amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
    if (amtLPToRemove > 0) {
      uint[3] memory mins;
      ICurvePool(pool).remove_liquidity(amtLPToRemove, mins);
    }

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

    // 7. Refund crv
    doRefund(crv);
  }

  /// @dev Remove liquidity from Curve pool with 4 underlying tokens
  /// @param lp LP token for the pool
  /// @param amtLPTake Take out LP token amount (from Homora)
  /// @param amtLPWithdraw Withdraw LP token amount (back to caller)
  /// @param amtsRepay Repay underlying token amounts
  /// @param amtLPRepay Repay LP token amount
  /// @param amtsMin Desired underlying token amounts (slippage control)
  function removeLiquidity4(
    address lp,
    uint amtLPTake,
    uint amtLPWithdraw,
    uint[4] calldata amtsRepay,
    uint amtLPRepay,
    uint[4] calldata amtsMin
  ) external {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    address pool = getPool(lp);
    uint positionId = bank.POSITION_ID();
    (, address collToken, uint collId, ) = bank.getPositionInfo(positionId);
    require(IWLiquidityGauge(collToken).getUnderlyingToken(collId) == lp, 'incorrect underlying');
    require(collToken == address(wgauge), 'collateral token & wgauge mismatched');
    address[] memory tokens = ulTokens[lp];

    // 0. Ensure approve
    ensureApproveN(lp, 4);

    // 1. Compute repay amount if MAX_INT is supplied (max debt)
    uint[4] memory actualAmtsRepay;
    for (uint i = 0; i < 4; i++) {
      actualAmtsRepay[i] = amtsRepay[i] == uint(-1)
        ? bank.borrowBalanceCurrent(positionId, tokens[i])
        : amtsRepay[i];
    }
    uint[4] memory amtsDesired;
    for (uint i = 0; i < 4; i++) {
      amtsDesired[i] = actualAmtsRepay[i].add(amtsMin[i]); // repay amt + slippage control
    }

    // 2. Take out collateral
    bank.takeCollateral(address(wgauge), collId, amtLPTake);
    wgauge.burn(collId, amtLPTake);

    // 3. Compute amount to actually remove. Remove to repay just enough
    uint amtLPToRemove;
    if (amtsDesired[0] > 0 || amtsDesired[1] > 0 || amtsDesired[2] > 0 || amtsDesired[3] > 0) {
      amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
      ICurvePool(pool).remove_liquidity_imbalance(amtsDesired, amtLPToRemove);
    }

    // 4. Compute leftover amount to remove. Remove balancedly.
    amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amtLPWithdraw);
    if (amtLPToRemove > 0) {
      uint[4] memory mins;
      ICurvePool(pool).remove_liquidity(amtLPToRemove, mins);
    }

    // 5. Repay
    for (uint i = 0; i < 4; i++) {
      doRepay(tokens[i], actualAmtsRepay[i]);
    }
    doRepay(lp, amtLPRepay);

    // 6. Refund
    for (uint i = 0; i < 4; i++) {
      doRefund(tokens[i]);
    }
    doRefund(lp);

    // 7. Refund crv
    doRefund(crv);
  }

  /// @dev Harvest CRV reward tokens to in-exec position's owner
  function harvest() external {
    (, address collToken, uint collId, uint collSize) = bank.getCurrentPositionInfo();
    (uint pid, uint gid, ) = wgauge.decodeId(collId);
    address lp = wgauge.getUnderlyingToken(collId);
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    require(collToken == address(wgauge), 'collateral token & wgauge mismatched');

    // 1. Take out collateral
    bank.takeCollateral(address(wgauge), collId, collSize);
    wgauge.burn(collId, collSize);

    // 2. Put collateral
    uint amount = IERC20(lp).balanceOf(address(this));
    ensureApprove(lp, address(wgauge));
    uint id = wgauge.mint(pid, gid, amount);
    bank.putCollateral(address(wgauge), id, amount);

    // 3. Refund crv
    doRefund(crv);
  }
}
