pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';

import './BasicSpell.sol';
import '../../interfaces/IUniswapV2Factory.sol';
import '../../interfaces/IUniswapV2Router02.sol';

contract UniswapV2SpellV1 is BasicSpell {
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
      uint256 amtA,
      uint256 amtB,
      uint256 resA,
      uint256 resB
  ) internal pure returns (uint256 swapAmt, bool isReversed) {
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
      uint256 amtA,
      uint256 amtB,
      uint256 resA,
      uint256 resB
  ) internal pure returns (uint256) {
      require(amtA.mul(resB) >= amtB.mul(resA), "Reversed");

      uint256 a = 997;
      uint256 b = uint256(1997).mul(resA);
      uint256 _c = (amtA.mul(resB)).sub(amtB.mul(resA));
      uint256 c = _c.mul(1000).div(amtB.add(resB)).mul(resA);

      uint256 d = a.mul(c).mul(4);
      uint256 e = Math.sqrt(b.mul(b).add(d));

      uint256 numerator = e.sub(b);
      uint256 denominator = a.mul(2);

      return numerator.div(denominator);
  }

  function addLiquidity(
    address tokenA,
    address tokenB,
    uint amtAUser,
    uint amtBUser,
    uint amtLPUser,
    uint amtABorrow,
    uint amtBBorrow,
    uint amtLPBorrow,
    uint amtAMin,
    uint amtBMin,
  ) public {
    address lp = getPair(tokenA, tokenB);

    // 1. Get user input amounts
    if (amtAUser > 0) { doTransmit(tokenA, amtAUser); }
    if (amtBUser > 0) { doTransmit(tokenB, amtBUser); }
    if (amtLPUser > 0) { doTransmit(lp, amtLPUser); }

    // 2. Borrow specified amounts
    if (amtABorrow > 0) { doBorrow(tokenA, amtABorrow); }
    if (amtBBorrow > 0) { doBorrow(tokenB, amtBBorrow); }
    if (amtLPBorrow > 0) { doBorrow(lp, amtLPBorrow); }

    // 3. Calculate optimal swap amount
    uint swapAmt;
    bool isReversed;
    {
      uint amtA = IERC20(tokenA).balanceOf(address(this));
      uint amtB = IERC20(tokenB).balanceOf(address(this));
      uint resA;
      uint resB;
      if (lp.token0() == tokenA) {
        (resA, resB, ) = lp.getReserves();
      } else {
        (resB, resA, ) = lp.getReserves();
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
    (, , uint liquidity) = router.addLiquidity(tokenA, tokenB, IERC20(tokenA).balanceOf(address(this)), IERC20(tokenB).balanceOf(address(this)), amtAMin, amtBMin, address(this), now);

    // 6. Put collateral
    bank.putCollateral(liquidity);

    // 7. Refund leftovers to users
    doRefund(tokenA);
    doRefund(tokenB);
  }

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
