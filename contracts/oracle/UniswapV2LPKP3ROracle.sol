pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import './BaseKP3ROracle.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IKeep3rV1Oracle.sol';
import '../../interfaces/IUniswapV2Pair.sol';

library LpMath {
  using SafeMath for uint;

  function fmul(uint lhs, uint rhs) internal pure returns (uint) {
    return lhs.mul(rhs) / (2**112);
  }

  function fdiv(uint lhs, uint rhs) internal pure returns (uint) {
    return lhs.mul(2**112) / rhs;
  }

  function sqrt(uint x) internal pure returns (uint y) {
    uint z = (x + 1) / 2;
    y = x;
    while (z < y) {
      y = z;
      z = (x / z + z) / 2;
    }
  }
}

contract UniswapV2LPKP3ROracle is IBaseOracle, BaseKP3ROracle {
  using SafeMath for uint;
  using LpMath for uint;

  constructor(IKeep3rV1Oracle _kp3r) public BaseKP3ROracle(_kp3r) {}

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param pair The Uniswap pair to check the value.
  function getETHPx(address pair) external view override returns (uint) {
    address token0 = IUniswapV2Pair(pair).token0();
    uint totalSupply = IUniswapV2Pair(pair).totalSupply();
    (uint r0, uint r1, ) = IUniswapV2Pair(pair).getReserves();
    uint sqrtK = LpMath.sqrt(r0.mul(r1)).fdiv(totalSupply); // in 2**112
    uint twap = token0 < weth ? price0TWAP(pair) : price1TWAP(pair);
    uint value = 2 * sqrtK.fmul(LpMath.sqrt(twap)).fdiv(LpMath.sqrt(2**112));
    return value;
  }
}
