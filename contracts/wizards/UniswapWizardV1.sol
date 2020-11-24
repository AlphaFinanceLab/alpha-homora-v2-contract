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

  function addLiquidity(address tokenA, address tokenB) public payable {
    address lpToken = factory.getPair(tokenA, tokenB);
    require(lpToken != address(0), 'lp token does not exist');
    // TODO
  }

  function removeLiquidity() public {
    // TODO
  }
}
