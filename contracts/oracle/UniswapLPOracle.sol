pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../utils/HomoraMath.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IUniswapV2Pair.sol';

contract UniswapLPOracle is IBaseOracle {
  using SafeMath for uint;
  using HomoraMath for uint;

  IBaseOracle public tokenOracle;
  address public weth;

  constructor(IBaseOracle _tokenOracle, address _weth) public {
    tokenOracle = _tokenOracle;
    weth = _weth;
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param pair The Uniswap pair to check the value.
  function getETHPx(address pair) external view override returns (uint) {
    address _weth = weth;
    address token0 = IUniswapV2Pair(pair).token0();
    address token1 = IUniswapV2Pair(pair).token1();
    // TODO: Test and make it work with non weth
    require(token0 == _weth || token1 == _weth, 'one token must be weth');
    uint totalSupply = IUniswapV2Pair(pair).totalSupply();
    (uint r0, uint r1, ) = IUniswapV2Pair(pair).getReserves();
    uint sqrtK = HomoraMath.sqrt(r0.mul(r1)).fdiv(totalSupply); // in 2**112
    uint px = token0 != _weth ? tokenOracle.getETHPx(token0) : tokenOracle.getETHPx(token1);
    uint value = 2 * sqrtK.fmul(HomoraMath.sqrt(px)).fdiv(HomoraMath.sqrt(2**112));
    return value;
  }
}
