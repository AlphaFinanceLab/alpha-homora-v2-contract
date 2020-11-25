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
      IERC20(tokenA).approveInfinite(address(router));
      IERC20(tokenB).approveInfinite(address(router));
      IERC20(lp).approveInfinite(address(router));
      pairs[tokenA][tokenB] = lp;
      pairs[tokenB][tokenA] = lp;
    }
    return lp;
  }

  function addLiquidityETH(
    address token,
    uint amtTokenUser,
    uint amtETHBorrow,
    uint amtTokenBorrow,
    uint amtETHMin,
    uint amtTokenMin
  ) public payable {
    address lp = getPair(weth, token);
    doTransmitETH();
    doTransmit(token, amtTokenUser);
    doBorrow(weth, amtETHBorrow);
    doBorrow(token, amtTokenBorrow);
    (, , uint liquidity) =
      router.addLiquidity(
        weth,
        token,
        IERC20(weth).balanceOf(address(this)),
        IERC20(token).balanceOf(address(this)),
        amtETHMin,
        amtTokenMin,
        address(this),
        now
      );
    bank.putCollateral(lp, liquidity);
    doRefundETH();
    doRefund(token);
  }

  function addLiquidity(
    address tokenA,
    address tokenB,
    uint amtAUser,
    uint amtBUser,
    uint amtABorrow,
    uint amtBBorrow,
    uint amtAMin,
    uint amtBMin
  ) public {
    address lp = getPair(tokenA, tokenB);
    doTransmit(tokenA, amtAUser);
    doTransmit(tokenB, amtBUser);
    doBorrow(tokenA, amtABorrow);
    doBorrow(tokenB, amtBBorrow);
    (, , uint liquidity) =
      router.addLiquidity(
        tokenA,
        tokenB,
        IERC20(tokenA).balanceOf(address(this)),
        IERC20(tokenB).balanceOf(address(this)),
        amtAMin,
        amtBMin,
        address(this),
        now
      );
    doPutCollateral(lp, liquidity);
    doRefund(tokenA);
    doRefund(tokenB);
  }

  function removeLiquidityETH(
    address token,
    uint liquidity,
    uint amtETHMin,
    uint amtTokenMin,
    uint amtETHRepay,
    uint amtTokenRepay
  ) public {
    address lp = getPair(weth, token);
    bank.takeCollateral(lp, liquidity);
    router.removeLiquidity(weth, token, liquidity, amtETHMin, amtTokenMin, address(this), now);
    doRepay(weth, amtETHRepay);
    doRepay(token, amtTokenRepay);
    doRefundETH();
    doRefund(token);
  }

  function removeLiquidity(
    address tokenA,
    address tokenB,
    uint liquidity,
    uint amtAMin,
    uint amtBMin,
    uint amtARepay,
    uint amtBRepay
  ) public {
    address lp = getPair(tokenA, tokenB);
    bank.takeCollateral(lp, liquidity);
    router.removeLiquidity(tokenA, tokenB, liquidity, amtAMin, amtBMin, address(this), now);
    doRepay(tokenA, amtARepay);
    doRepay(tokenB, amtBRepay);
    doRefund(tokenA);
    doRefund(tokenB);
  }
}
