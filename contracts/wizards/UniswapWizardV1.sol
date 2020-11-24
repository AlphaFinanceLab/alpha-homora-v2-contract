pragma solidity 0.6.12;

import '../../interfaces/IBank.sol';
import '../../interfaces/IWETH.sol';
import '../../interfaces/IUniswapV2Factory.sol';
import '../../interfaces/IUniswapV2Router02.sol';

contract UniswapV2WizardV1 {
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

  function addLiquidity(
    address tokenA,
    address tokenB,
    uint amountAUser,
    uint amountBUser,
    uint amountABorrow,
    uint amountBBorrow,
    uint amountAMin,
    uint amountBMin,
    uint deadline
  ) public payable {
    address lpToken = factory.getPair(tokenA, tokenB);
    require(lpToken != address(0), 'lp token does not exist');

    // function addLiquidity(
    //   address tokenA,
    //   address tokenB,
    //   uint amountADesired,
    //   uint amountBDesired,
    //   uint amountAMin,
    //   uint amountBMin,
    //   address to,
    //   uint deadline
    // )
    //   external
    //   returns (
    //     uint amountA,
    //     uint amountB,
    //     uint liquidity
    //   );

    // router.addLiquidity()
    // TODO
  }

  function removeLiquidity() public {
    // TODO
  }
}
