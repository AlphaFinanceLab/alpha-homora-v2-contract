pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../../interfaces/IBank.sol';
import '../../interfaces/IWETH.sol';
import '../../interfaces/IUniswapV2Factory.sol';
import '../../interfaces/IUniswapV2Router02.sol';

// function

contract UniswapV2WizardV1 {
  using SafeMath for uint;

  IBank public bank;
  IUniswapV2Factory public factory;
  IUniswapV2Router02 public router;
  IWETH public weth;

  constructor(IBank _bank, IUniswapV2Router02 _router) public {
    bank = _bank;
    router = _router;
    factory = IUniswapV2Factory(_router.factory());
    weth = IWETH(_router.WETH());
  }

  // function approvePair(address tokenA, address tokenB) public {
  //   address lpToken = factory.getPair(tokenA, tokenB);
  //   require(lpToken != address(0), 'lp token does not exist');
  //   IERC20(tokenA).approve(router, uint(0));
  //   IERC20(tokenA).approve(router, uint(-1));
  //   IERC20(tokenB).approve(router, uint(0));
  //   IERC20(tokenB).approve(router, uint(-1));
  //   IERC20(lpToken).approve(router, uint(0));
  //   IERC20(lpToken).approve(router, uint(-1));
  // }

  function addLiquidity(
    address tokenA,
    address tokenB,
    uint amountAUser,
    uint amountBUser,
    uint amountABorrow,
    uint amountBBorrow,
    uint amountAMin,
    uint amountBMin
  ) public payable {
    address lpToken = factory.getPair(tokenA, tokenB);
    require(lpToken != address(0), 'lp token does not exist');
    if (msg.value > 0) weth.deposit{value: msg.value}();
    if (amountAUser > 0) bank.transmit(tokenA, amountAUser);
    if (amountBUser > 0) bank.transmit(tokenB, amountBUser);
    if (amountABorrow > 0) bank.borrow(tokenA, amountABorrow);
    if (amountBBorrow > 0) bank.borrow(tokenB, amountBBorrow);
    uint amountADesired = IERC20(tokenA).balanceOf(address(this));
    uint amountBDesired = IERC20(tokenB).balanceOf(address(this));
    (uint amountA, uint amountB, uint liquidity) =
      router.addLiquidity(
        tokenA,
        tokenB,
        amountADesired,
        amountBDesired,
        amountAMin,
        amountBMin,
        address(this),
        now + 10
      );
    address executor = bank.EXECUTOR();
    if (amountADesired > amountA) IERC20(tokenA).transfer(executor, amountADesired - amountA);
    if (amountBDesired > amountB) IERC20(tokenA).transfer(executor, amountADesired - amountB);
    bank.putCollateral(lpToken, liquidity);
  }

  function removeLiquidity() public {
    // TODO
  }
}
