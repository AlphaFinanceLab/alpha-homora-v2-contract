// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import './WhitelistSpell.sol';
import '../utils/HomoraMath.sol';
import '../../interfaces/IBalancerPool.sol';
import '../../interfaces/IWStakingRewards.sol';

contract BalancerSpellV1 is WhitelistSpell {
  using SafeMath for uint;
  using HomoraMath for uint;

  mapping(address => address[2]) public pairs; // Mapping from lp token to underlying token (only pairs)

  constructor(
    IBank _bank,
    address _werc20,
    address _weth
  ) public WhitelistSpell(_bank, _werc20, _weth) {}

  /// @dev Return the underlying pairs for the lp token.
  /// @param lp LP token
  function getAndApprovePair(address lp) public returns (address, address) {
    address[2] memory ulTokens = pairs[lp];
    if (ulTokens[0] == address(0) || ulTokens[1] == address(0)) {
      address[] memory tokens = IBalancerPool(lp).getFinalTokens();
      require(tokens.length == 2, 'underlying tokens not 2');
      ulTokens[0] = tokens[0];
      ulTokens[1] = tokens[1];
      pairs[lp] = ulTokens;
      ensureApprove(ulTokens[0], lp);
      ensureApprove(ulTokens[1], lp);
    }
    return (ulTokens[0], ulTokens[1]);
  }

  struct Amounts {
    uint amtAUser; // Supplied tokenA amount
    uint amtBUser; // Supplied tokenB amount
    uint amtLPUser; // Supplied LP token amount
    uint amtABorrow; // Borrow tokenA amount
    uint amtBBorrow; // Borrow tokenB amount
    uint amtLPBorrow; // Borrow LP token amount
    uint amtLPDesired; // Desired LP token amount (slippage control)
  }

  /// @dev Add liquidity to Balancer pool
  /// @param lp LP token for the pool
  /// @param amt Amounts of tokens to supply, borrow, and get.
  /// @return added lp amount
  function addLiquidityInternal(address lp, Amounts calldata amt) internal returns (uint) {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    (address tokenA, address tokenB) = getAndApprovePair(lp);

    // 1. Get user input amounts
    doTransmitETH();
    doTransmit(tokenA, amt.amtAUser);
    doTransmit(tokenB, amt.amtBUser);
    doTransmit(lp, amt.amtLPUser);

    // 2. Borrow specified amounts
    doBorrow(tokenA, amt.amtABorrow);
    doBorrow(tokenB, amt.amtBBorrow);
    doBorrow(lp, amt.amtLPBorrow);

    // 3.1 Add Liquidity using equal value two side to minimize swap fee
    uint[] memory maxAmountsIn = new uint[](2);
    maxAmountsIn[0] = IERC20(tokenA).balanceOf(address(this));
    maxAmountsIn[1] = IERC20(tokenB).balanceOf(address(this));
    uint totalLPSupply = IBalancerPool(lp).totalSupply();
    uint poolAmountFromA =
      maxAmountsIn[0].mul(1e18).div(IBalancerPool(lp).getBalance(tokenA)).mul(totalLPSupply).div(
        1e18
      ); // compute in reverse order of how Balancer's `joinPool` computes tokenAmountIn
    uint poolAmountFromB =
      maxAmountsIn[1].mul(1e18).div(IBalancerPool(lp).getBalance(tokenB)).mul(totalLPSupply).div(
        1e18
      ); // compute in reverse order of how Balancer's `joinPool` computes tokenAmountIn

    uint poolAmountOut = poolAmountFromA > poolAmountFromB ? poolAmountFromB : poolAmountFromA;
    if (poolAmountOut > 0) IBalancerPool(lp).joinPool(poolAmountOut, maxAmountsIn);

    // 3.2 Add Liquidity leftover for each token
    uint ABal = IERC20(tokenA).balanceOf(address(this));
    uint BBal = IERC20(tokenB).balanceOf(address(this));
    if (ABal > 0) IBalancerPool(lp).joinswapExternAmountIn(tokenA, ABal, 0);
    if (BBal > 0) IBalancerPool(lp).joinswapExternAmountIn(tokenB, BBal, 0);

    // 4. Slippage control
    uint lpBalance = IERC20(lp).balanceOf(address(this));
    require(lpBalance >= amt.amtLPDesired, 'lp desired not met');

    return lpBalance;
  }

  /// @dev Add liquidity to Balancer pool (with 2 underlying tokens), without staking rewards (use WERC20 wrapper)
  /// @param lp LP token for the pool
  /// @param amt Amounts of tokens to supply, borrow, and get.
  function addLiquidityWERC20(address lp, Amounts calldata amt) external payable {
    // 1-4. add liquidity
    uint lpBalance = addLiquidityInternal(lp, amt);

    // 5. Put collateral
    doPutCollateral(lp, lpBalance);

    // 6. Refund leftovers to users
    (address tokenA, address tokenB) = getAndApprovePair(lp);
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);
  }

  /// @dev Add liquidity to Balancer pool (with 2 underlying tokens), with staking rewards (use WStakingRewards)
  /// @param lp LP token for the pool
  /// @param amt Amounts of tokens to supply, borrow, and desire.
  /// @param wstaking Wrapped staking rewards contract address
  function addLiquidityWStakingRewards(
    address lp,
    Amounts calldata amt,
    address wstaking
  ) external payable {
    // 1-4. add liquidity
    addLiquidityInternal(lp, amt);

    // 5. Take out collateral
    (, address collToken, uint collId, uint collSize) = bank.getCurrentPositionInfo();
    if (collSize > 0) {
      require(IWStakingRewards(collToken).getUnderlyingToken(collId) == lp, 'incorrect underlying');
      require(collToken == wstaking, 'collateral token & wstaking mismatched');
      bank.takeCollateral(wstaking, collId, collSize);
      IWStakingRewards(wstaking).burn(collId, collSize);
    }

    // 6. Put collateral
    ensureApprove(lp, wstaking);
    uint amount = IERC20(lp).balanceOf(address(this));
    uint id = IWStakingRewards(wstaking).mint(amount);
    if (!IWStakingRewards(wstaking).isApprovedForAll(address(this), address(bank))) {
      IWStakingRewards(wstaking).setApprovalForAll(address(bank), true);
    }
    bank.putCollateral(address(wstaking), id, amount);

    // 7. Refund leftovers to users
    (address tokenA, address tokenB) = getAndApprovePair(lp);
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);

    // 8. Refund reward
    doRefund(IWStakingRewards(wstaking).reward());
  }

  struct RepayAmounts {
    uint amtLPTake; // Take out LP token amount (from Homora)
    uint amtLPWithdraw; // Withdraw LP token amount (back to caller)
    uint amtARepay; // Repay tokenA amount
    uint amtBRepay; // Repay tokenB amount
    uint amtLPRepay; // Repay LP token amount
    uint amtAMin; // Desired tokenA amount (slippage control)
    uint amtBMin; // Desired tokenB amount (slippage control)
  }

  /// @dev Remove liquidity from Balancer pool (with 2 underlying tokens)
  /// @param lp LP token for the pool
  /// @param amt Amounts of tokens to take out, withdraw, repay and get.
  function removeLiquidityInternal(address lp, RepayAmounts calldata amt) internal {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    (address tokenA, address tokenB) = getAndApprovePair(lp);
    uint amtARepay = amt.amtARepay;
    uint amtBRepay = amt.amtBRepay;
    uint amtLPRepay = amt.amtLPRepay;

    // 2. Compute repay amount if MAX_INT is supplied (max debt)
    {
      uint positionId = bank.POSITION_ID();
      if (amtARepay == uint(-1)) {
        amtARepay = bank.borrowBalanceCurrent(positionId, tokenA);
      }
      if (amtBRepay == uint(-1)) {
        amtBRepay = bank.borrowBalanceCurrent(positionId, tokenB);
      }
      if (amtLPRepay == uint(-1)) {
        amtLPRepay = bank.borrowBalanceCurrent(positionId, lp);
      }
    }

    // 3.1 Remove liquidity 2 sides
    uint amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amt.amtLPWithdraw);

    if (amtLPToRemove > 0) {
      uint[] memory minAmountsOut = new uint[](2);
      IBalancerPool(lp).exitPool(amtLPToRemove, minAmountsOut);
    }

    // 3.2 Minimize trading
    uint amtADesired = amtARepay.add(amt.amtAMin);
    uint amtBDesired = amtBRepay.add(amt.amtBMin);

    uint amtA = IERC20(tokenA).balanceOf(address(this));
    uint amtB = IERC20(tokenB).balanceOf(address(this));

    if (amtA < amtADesired && amtB > amtBDesired) {
      IBalancerPool(lp).swapExactAmountOut(
        tokenB,
        amtB.sub(amtBDesired),
        tokenA,
        amtADesired.sub(amtA),
        uint(-1)
      );
    } else if (amtA > amtADesired && amtB < amtBDesired) {
      IBalancerPool(lp).swapExactAmountOut(
        tokenA,
        amtA.sub(amtADesired),
        tokenB,
        amtBDesired.sub(amtB),
        uint(-1)
      );
    }

    // 4. Repay
    doRepay(tokenA, amtARepay);
    doRepay(tokenB, amtBRepay);
    doRepay(lp, amtLPRepay);

    // 5. Slippage control
    require(IERC20(tokenA).balanceOf(address(this)) >= amt.amtAMin);
    require(IERC20(tokenB).balanceOf(address(this)) >= amt.amtBMin);
    require(IERC20(lp).balanceOf(address(this)) >= amt.amtLPWithdraw);

    // 6. Refund leftover
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);
    doRefund(lp);
  }

  /// @dev Remove liquidity from Balancer pool (with 2 underlying tokens), without staking rewards (use WERC20 wrapper)
  /// @param lp LP token for the pool
  /// @param amt Amounts of tokens to take out, withdraw, repay, and get.
  function removeLiquidityWERC20(address lp, RepayAmounts calldata amt) external {
    // 1. Take out collateral
    doTakeCollateral(lp, amt.amtLPTake);

    // 2-6. remove liquidity
    removeLiquidityInternal(lp, amt);
  }

  /// @dev Remove liquidity from Balancer pool (with 2 underlying tokens), with staking rewards
  /// @param lp LP token for the pool
  /// @param amt Amounts of tokens to take out, withdraw, repay, and get.v
  function removeLiquidityWStakingRewards(
    address lp,
    RepayAmounts calldata amt,
    address wstaking
  ) external {
    (, address collToken, uint collId, ) = bank.getCurrentPositionInfo();

    // 1. Take out collateral
    require(IWStakingRewards(collToken).getUnderlyingToken(collId) == lp, 'incorrect underlying');
    require(collToken == wstaking, 'collateral token & wstaking mismatched');
    bank.takeCollateral(wstaking, collId, amt.amtLPTake);
    IWStakingRewards(wstaking).burn(collId, amt.amtLPTake);

    // 2-6. remove liquidity
    removeLiquidityInternal(lp, amt);

    // 7. Refund reward
    doRefund(IWStakingRewards(wstaking).reward());
  }

  /// @dev Harvest staking reward tokens to in-exec position's owner
  /// @param wstaking Wrapped staking rewards
  function harvestWStakingRewards(address wstaking) external {
    (, address collToken, uint collId, ) = bank.getCurrentPositionInfo();
    address lp = IWStakingRewards(wstaking).getUnderlyingToken(collId);
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    require(collToken == wstaking, 'collateral token & wstaking mismatched');

    // 1. Take out collateral
    bank.takeCollateral(wstaking, collId, uint(-1));
    IWStakingRewards(wstaking).burn(collId, uint(-1));

    // 2. put collateral
    uint amount = IERC20(lp).balanceOf(address(this));
    ensureApprove(lp, wstaking);
    uint id = IWStakingRewards(wstaking).mint(amount);
    bank.putCollateral(wstaking, id, amount);

    // 3. Refund reward
    doRefund(IWStakingRewards(wstaking).reward());
  }
}
