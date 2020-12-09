pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../utils/HomoraMath.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IUniswapV2Pair.sol';

contract UniswapLPOracle is IBaseOracle {
  using SafeMath for uint;
  using HomoraMath for uint;

  IBaseOracle public tokenOracle;

  constructor(IBaseOracle _tokenOracle) public {
    tokenOracle = _tokenOracle;
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param pair The Uniswap pair to check the value.
  function getETHPx(address pair) external view override returns (uint) {
    address token0 = IUniswapV2Pair(pair).token0();
    address token1 = IUniswapV2Pair(pair).token1();
    uint totalSupply = IUniswapV2Pair(pair).totalSupply();
    (uint r0, uint r1, ) = IUniswapV2Pair(pair).getReserves();
    uint sqrtK = HomoraMath.sqrt(r0.mul(r1)).fdiv(totalSupply); // in 2**112
    uint px0 = tokenOracle.getETHPx(token0);
    uint px1 = tokenOracle.getETHPx(token1);
    return sqrtK.mul(2).mul(HomoraMath.sqrt(px0)).div(2**56).mul(HomoraMath.sqrt(px1)).div(2**56);
  }
}
