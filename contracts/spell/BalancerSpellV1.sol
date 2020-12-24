pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import './BasicSpell.sol';
import '../utils/HomoraMath.sol';
import '../../interfaces/IBalancerPool.sol';

contract BalancerSpellV1 is BasicSpell {
  using SafeMath for uint;
  using HomoraMath for uint;

  mapping(address => address[2]) pairs; // mapping from lp token to underlying token (only pairs)

  constructor(
    IBank _bank,
    address _werc20,
    address _weth
  ) public BasicSpell(_bank, _werc20, _weth) {}

  function getPair(address lp) public returns (address tokenA, address tokenB) {
    address[2] memory ulTokens = pairs[lp];
    tokenA = ulTokens[0];
    tokenB = ulTokens[1];
    if (tokenA == address(0) || tokenB == address(0)) {
      address[] memory tokens = IBalancerPool(lp).getFinalTokens();
      require(tokens.length == 2, 'underlying tokens not 2');
      tokenA = tokens[0];
      tokenB = tokens[1];
      ensureApprove(tokenA, lp);
      ensureApprove(tokenB, lp);
    }
  }

  struct Amounts {
    uint amtAUser;
    uint amtBUser;
    uint amtLPUser;
    uint amtABorrow;
    uint amtBBorrow;
    uint amtLPBorrow;
    uint amtLPDesired;
  }

  /// @dev Add liquidity to Balancer pool (with 2 underlying tokens)
  function addLiquidity(address lp, Amounts calldata amt) external payable {
    (address tokenA, address tokenB) = getPair(lp);

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
    maxAmountsIn[0] = amt.amtAUser.add(amt.amtABorrow);
    maxAmountsIn[1] = amt.amtBUser.add(amt.amtBBorrow);
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

    // 5. Put collateral
    doPutCollateral(lp, lpBalance);

    // 6. Refund leftovers to users
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);
  }

  struct RepayAmounts {
    uint amtLPTake;
    uint amtLPWithdraw;
    uint amtARepay;
    uint amtBRepay;
    uint amtLPRepay;
    uint amtAMin;
    uint amtBMin;
  }

  function removeLiquidity(address lp, RepayAmounts calldata amt) external {
    (address tokenA, address tokenB) = getPair(lp);
    uint amtARepay = amt.amtARepay;
    uint amtBRepay = amt.amtBRepay;
    uint amtLPRepay = amt.amtLPRepay;

    // 1. Compute repay amount if MAX_INT is supplied (max debt)
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

    // 2. Take out collateral
    doTakeCollateral(lp, amt.amtLPTake);

    // 3.1 Remove liquidity 2 sides
    uint amtADesired = amtARepay.add(amt.amtAMin);
    uint amtBDesired = amtBRepay.add(amt.amtBMin);
    uint totalLPSupply = IBalancerPool(lp).totalSupply();

    uint poolAmountOut;

    {
      uint ARes = IBalancerPool(lp).getBalance(tokenA);
      uint BRes = IBalancerPool(lp).getBalance(tokenB);
      uint poolAmountFromA = amtADesired.mul(1e18).div(ARes).mul(totalLPSupply).div(1e18); // compute in reverse order of how Balancer's `joinPool` computes tokenAmountIn
      uint poolAmountFromB = amtBDesired.mul(1e18).div(BRes).mul(totalLPSupply).div(1e18); // compute in reverse order of how Balancer's `joinPool` computes tokenAmountIn
      poolAmountOut = poolAmountFromA > poolAmountFromB ? poolAmountFromB : poolAmountFromA;
    }

    uint[] memory minAmountsOut = new uint[](2);
    if (poolAmountOut > 0) {
      IBalancerPool(lp).exitPool(poolAmountOut, minAmountsOut);
    }

    // 3.2 Remove liquidity for each asset to cover the desired amount
    {
      uint ABal = IERC20(tokenA).balanceOf(address(this));

      if (amtADesired > ABal)
        IBalancerPool(lp).exitswapExternAmountOut(tokenA, amtADesired - ABal, uint(-1));
    }
    {
      uint BBal = IERC20(tokenB).balanceOf(address(this));

      if (amtBDesired > BBal)
        IBalancerPool(lp).exitswapExternAmountOut(tokenB, amtBDesired - BBal, uint(-1));
    }

    // 3.3 Remove remaining liquidity
    IBalancerPool(lp).exitPool(
      IERC20(lp).balanceOf(address(this)).sub(amt.amtLPWithdraw.add(amt.amtLPRepay)),
      minAmountsOut
    );

    // 4. Repay
    doRepay(tokenA, amtARepay);
    doRepay(tokenB, amtBRepay);
    doRepay(lp, amtLPRepay);

    // 5. Slippage control
    require(IERC20(tokenA).balanceOf(address(this)) >= amt.amtAMin);
    require(IERC20(tokenB).balanceOf(address(this)) >= amt.amtBMin);
    require(IERC20(lp).balanceOf(address(this)) == amt.amtLPWithdraw);

    // 6. Refund leftover
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);
    doRefund(lp);
  }
}
