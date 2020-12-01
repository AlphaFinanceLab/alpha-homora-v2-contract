pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import './BasicSpell.sol';
import '../../interfaces/IUniswapV2Factory.sol';
import '../../interfaces/IUniswapV2Router02.sol';
import '../../interfaces/IUniswapV2Pair.sol';

library Math {
  using SafeMath for uint;

  function sqrt(uint x) internal pure returns (uint y) {
    uint z = (x + 1) / 2;
    y = x;
    while (z < y) {
      y = z;
      z = (x / z + z) / 2;
    }
  }
}

contract UniswapV2SpellV1 is BasicSpell {
  using SafeMath for uint;
  using Math for uint;

  IUniswapV2Factory public factory;
  IUniswapV2Router02 public router;

  mapping(address => mapping(address => address)) public pairs;

  constructor(IBank _bank, IUniswapV2Router02 _router) public BasicSpell(_bank, _router.WETH()) {
    router = _router;
    factory = IUniswapV2Factory(_router.factory());
  }

  function getPair(address tokenA, address tokenB) public returns (address) {
    address lp = pairs[tokenA][tokenB];
    if (lp == address(0)) {
      lp = factory.getPair(tokenA, tokenB);
      require(lp != address(0), 'no lp token');
      ensureApprove(tokenA, address(router));
      ensureApprove(tokenB, address(router));
      ensureApprove(lp, address(router));
      pairs[tokenA][tokenB] = lp;
      pairs[tokenB][tokenA] = lp;
    }
    return lp;
  }

  /// @dev Compute optimal deposit amount
  /// @param amtA amount of token A desired to deposit
  /// @param amtB amonut of token B desired to deposit
  /// @param resA amount of token A in reserve
  /// @param resB amount of token B in reserve
  function optimalDeposit(
    uint amtA,
    uint amtB,
    uint resA,
    uint resB
  ) internal pure returns (uint swapAmt, bool isReversed) {
    if (amtA.mul(resB) >= amtB.mul(resA)) {
      swapAmt = _optimalDepositA(amtA, amtB, resA, resB);
      isReversed = false;
    } else {
      swapAmt = _optimalDepositA(amtB, amtA, resB, resA);
      isReversed = true;
    }
  }

  /// @dev Compute optimal deposit amount helper
  /// @param amtA amount of token A desired to deposit
  /// @param amtB amonut of token B desired to deposit
  /// @param resA amount of token A in reserve
  /// @param resB amount of token B in reserve
  function _optimalDepositA(
    uint amtA,
    uint amtB,
    uint resA,
    uint resB
  ) internal pure returns (uint) {
    require(amtA.mul(resB) >= amtB.mul(resA), 'Reversed');

    uint a = 997;
    uint b = uint(1997).mul(resA);
    uint _c = (amtA.mul(resB)).sub(amtB.mul(resA));
    uint c = _c.mul(1000).div(amtB.add(resB)).mul(resA);

    uint d = a.mul(c).mul(4);
    uint e = Math.sqrt(b.mul(b).add(d));

    uint numerator = e.sub(b);
    uint denominator = a.mul(2);

    return numerator.div(denominator);
  }

  struct Amounts {
    uint amtAUser;
    uint amtBUser;
    uint amtLPUser;
    uint amtABorrow;
    uint amtBBorrow;
    uint amtLPBorrow;
    uint amtAMin;
    uint amtBMin;
  }

  function addLiquidity(
    address tokenA,
    address tokenB,
    Amounts calldata amt
  ) external {
    address lp = getPair(tokenA, tokenB);

    // 1. Get user input amounts
    doTransmit(tokenA, amt.amtAUser);
    doTransmit(tokenB, amt.amtBUser);
    doTransmit(lp, amt.amtLPUser);

    // 2. Borrow specified amounts
    doBorrow(tokenA, amt.amtABorrow);
    doBorrow(tokenB, amt.amtBBorrow);
    doBorrow(lp, amt.amtLPBorrow);

    // 3. Calculate optimal swap amount
    uint swapAmt;
    bool isReversed;
    {
      uint amtA = IERC20(tokenA).balanceOf(address(this));
      uint amtB = IERC20(tokenB).balanceOf(address(this));
      uint resA;
      uint resB;
      if (IUniswapV2Pair(lp).token0() == tokenA) {
        (resA, resB, ) = IUniswapV2Pair(lp).getReserves();
      } else {
        (resB, resA, ) = IUniswapV2Pair(lp).getReserves();
      }
      (swapAmt, isReversed) = optimalDeposit(amtA, amtB, resA, resB);
    }

    // 4. Swap optimal amount
    {
      address[] memory path = new address[](2);
      (path[0], path[1]) = isReversed ? (tokenB, tokenA) : (tokenA, tokenB);
      router.swapExactTokensForTokens(swapAmt, 0, path, address(this), now);
    }

    // 5. Add liquidity
    (, , uint liquidity) = router.addLiquidity(
      tokenA,
      tokenB,
      IERC20(tokenA).balanceOf(address(this)),
      IERC20(tokenB).balanceOf(address(this)),
      amt.amtAMin,
      amt.amtBMin,
      address(this),
      now
    );

    // 6. Put collateral
    doPutCollateral(lp, IERC20(lp).balanceOf(address(this)));

    // // 7. Refund leftovers to users
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

  function removeLiquidity(
    address tokenA,
    address tokenB,
    RepayAmounts calldata amt
  ) external {
    address lp = getPair(tokenA, tokenB);

    // 1. Take out collateral
    doTakeCollateral(amt.amtLPTake);

    // 2. Compute amount to actually remove
    uint amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amt.amtLPWithdraw);

    // 3. Remove liquidity
    (uint amtA, uint amtB) = router.removeLiquidity(
      tokenA,
      tokenB,
      amtLPToRemove,
      amt.amtAMin,
      amt.amtBMin,
      address(this),
      now
    );

    // // 4. Repay TODO: if repay amount = -1, repay max debt
    // if (amt.amtARepay == uint(-1)) {
    //   // uint amtARepay = bank.
    // }

    // 5. MinimizeTrading to repay debt
    if (amtA < amt.amtARepay && amtB >= amt.amtBRepay) {
      address[] memory path = new address[](2);
      (path[0], path[1]) = (tokenB, tokenA);
      router.swapTokensForExactTokens(amt.amtARepay.sub(amtA), uint(-1), path, address(this), now);
    } else if (amtA >= amt.amtARepay && amtB < amt.amtBRepay) {
      address[] memory path = new address[](2);
      (path[0], path[1]) = (tokenA, tokenB);
      router.swapTokensForExactTokens(amt.amtBRepay.sub(amtB), uint(-1), path, address(this), now);
    }

    // 6. Repay
    doRepay(tokenA, amt.amtARepay);
    // doRepay(tokenB, amt.amtBRepay);
    // doRepay(lp, amt.amtLPRepay);

    // // 7. Slippage control
    // require(IERC20(tokenA).balanceOf(address(this)) >= amt.amtAMin);
    // require(IERC20(tokenB).balanceOf(address(this)) >= amt.amtBMin);

    // // 8. Refund leftover
    // doRefund(tokenA);
    // doRefund(tokenB);
  }

  // function addLiquidity(
  //   address tokenA,
  //   address tokenB,
  //   uint amtAUser,
  //   uint amtBUser,
  //   uint amtLPUser,
  //   uint amtABorrow,
  //   uint amtBBorrow,
  //   uint amtLPBorrow,
  //   uint amtAMin,
  //   uint amtBMin
  // ) public {
  //   address lp = getPair(tokenA, tokenB);

  //   // 1. Get user input amounts
  //   if (amtAUser > 0) {
  //     doTransmit(tokenA, amtAUser);
  //   }
  //   if (amtBUser > 0) {
  //     doTransmit(tokenB, amtBUser);
  //   }
  //   if (amtLPUser > 0) {
  //     doTransmit(lp, amtLPUser);
  //   }

  //   // 2. Borrow specified amounts
  //   if (amtABorrow > 0) {
  //     doBorrow(tokenA, amtABorrow);
  //   }
  //   if (amtBBorrow > 0) {
  //     doBorrow(tokenB, amtBBorrow);
  //   }
  //   if (amtLPBorrow > 0) {
  //     doBorrow(lp, amtLPBorrow);
  //   }

  //   // 3. Calculate optimal swap amount
  //   uint swapAmt;
  //   bool isReversed;
  //   {
  //     uint amtA = IERC20(tokenA).balanceOf(address(this));
  //     uint amtB = IERC20(tokenB).balanceOf(address(this));
  //     uint resA;
  //     uint resB;
  //     if (IUniswapV2Pair(lp).token0() == tokenA) {
  //       (resA, resB, ) = IUniswapV2Pair(lp).getReserves();
  //     } else {
  //       (resB, resA, ) = IUniswapV2Pair(lp).getReserves();
  //     }
  //     (swapAmt, isReversed) = optimalDeposit(amtA, amtB, resA, resB);
  //   }

  //   // 4. Swap optimal amount
  //   {
  //     address[] memory path = new address[](2);
  //     (path[0], path[1]) = isReversed ? (tokenB, tokenA) : (tokenA, tokenB);
  //     router.swapExactTokensForTokens(swapAmt, 0, path, address(this), now);
  //   }

  //   // 5. Add liquidity
  //   (, , uint liquidity) = router.addLiquidity(
  //     tokenA,
  //     tokenB,
  //     IERC20(tokenA).balanceOf(address(this)),
  //     IERC20(tokenB).balanceOf(address(this)),
  //     amtAMin,
  //     amtBMin,
  //     address(this),
  //     now
  //   );

  //   // 6. Put collateral
  //   bank.putCollateral(liquidity);

  //   // 7. Refund leftovers to users
  //   doRefund(tokenA);
  //   doRefund(tokenB);
  // }

  // function addLiquidityETH(
  //   address token,
  //   uint amtTokenUser,
  //   uint amtETHBorrow,
  //   uint amtTokenBorrow,
  //   uint amtETHMin,
  //   uint amtTokenMin
  // ) public payable {
  //   address lp = getPair(weth, token);
  //   doTransmitETH();
  //   doTransmit(token, amtTokenUser);
  //   doBorrow(weth, amtETHBorrow);
  //   doBorrow(token, amtTokenBorrow);
  //   (, , uint liquidity) = router.addLiquidity(
  //     weth,
  //     token,
  //     IERC20(weth).balanceOf(address(this)),
  //     IERC20(token).balanceOf(address(this)),
  //     amtETHMin,
  //     amtTokenMin,
  //     address(this),
  //     now
  //   );
  //   bank.putCollateral(liquidity);
  //   doRefundETH();
  //   doRefund(token);
  // }

  // function addLiquidity(
  //   address tokenA,
  //   address tokenB,
  //   uint amtAUser,
  //   uint amtBUser,
  //   uint amtABorrow,
  //   uint amtBBorrow,
  //   uint amtAMin,
  //   uint amtBMin
  // ) public {
  //   address lp = getPair(tokenA, tokenB);
  //   doTransmit(tokenA, amtAUser);
  //   doTransmit(tokenB, amtBUser);
  //   doBorrow(tokenA, amtABorrow);
  //   doBorrow(tokenB, amtBBorrow);
  //   (, , uint liquidity) = router.addLiquidity(
  //     tokenA,
  //     tokenB,
  //     IERC20(tokenA).balanceOf(address(this)),
  //     IERC20(tokenB).balanceOf(address(this)),
  //     amtAMin,
  //     amtBMin,
  //     address(this),
  //     now
  //   );
  //   doPutCollateral(lp, liquidity);
  //   doRefund(tokenA);
  //   doRefund(tokenB);
  // }

  // function removeLiquidityETH(
  //   address token,
  //   uint liquidity,
  //   uint amtETHMin,
  //   uint amtTokenMin,
  //   uint amtETHRepay,
  //   uint amtTokenRepay
  // ) public {
  //   address lp = getPair(weth, token);
  //   bank.takeCollateral(liquidity);
  //   router.removeLiquidity(weth, token, liquidity, amtETHMin, amtTokenMin, address(this), now);
  //   doRepay(weth, amtETHRepay);
  //   doRepay(token, amtTokenRepay);
  //   doRefundETH();
  //   doRefund(token);
  // }

  // function removeLiquidity(
  //   address tokenA,
  //   address tokenB,
  //   uint liquidity,
  //   uint amtAMin,
  //   uint amtBMin,
  //   uint amtARepay,
  //   uint amtBRepay
  // ) public {
  //   address lp = getPair(tokenA, tokenB);
  //   bank.takeCollateral(liquidity);
  //   router.removeLiquidity(tokenA, tokenB, liquidity, amtAMin, amtBMin, address(this), now);
  //   doRepay(tokenA, amtARepay);
  //   doRepay(tokenB, amtBRepay);
  //   doRefund(tokenA);
  //   doRefund(tokenB);
  // }
}
