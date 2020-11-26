pragma solidity 0.6.12;

import '../../interfaces/IKeep3rV1Oracle.sol';
import '../../interfaces/IUniswapV2Pair.sol';

library UniswapV2Library {
  // returns sorted token addresses, used to handle return values from pairs sorted in this order
  function sortTokens(address tokenA, address tokenB)
    internal
    pure
    returns (address token0, address token1)
  {
    require(tokenA != tokenB, 'UniswapV2Library: IDENTICAL_ADDRESSES');
    (token0, token1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
    require(token0 != address(0), 'UniswapV2Library: ZERO_ADDRESS');
  }

  // calculates the CREATE2 address for a pair without making any external calls
  function pairInfo(
    address factory,
    address tokenA,
    address tokenB
  )
    internal
    pure
    returns (
      address pair,
      address token0,
      address token1
    )
  {
    (token0, token1) = sortTokens(tokenA, tokenB);
    pair = address(
      uint(
        keccak256(
          abi.encodePacked(
            hex'ff',
            factory,
            keccak256(abi.encodePacked(token0, token1)),
            hex'96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f' // init code hash
          )
        )
      )
    );
  }
}

contract BaseK3PROracle {
  IKeep3rV1Oracle public k3pr;
  address public factory;
  address public weth;

  constructor(IKeep3rV1Oracle _k3pr) public {
    k3pr = _k3pr;
  }

  function getETHTWAP(address token) public view returns (uint) {
    return getTWAP(token, weth);
  }

  function getTWAP(address quote, address base) public view returns (uint) {
    (address pair, address token0, ) = UniswapV2Library.pairInfo(factory, quote, base);
    uint length = k3pr.observationLength(pair);
    require(length > 0, 'no length-1 observation');
    (uint lastTime, uint lastPx0Cumm, uint lastPx1Cumm) = k3pr.observations(pair, length - 1);
    if (lastTime > now - 15 minutes) {
      require(length > 1, 'no length-2 observation');
      (lastTime, lastPx0Cumm, lastPx1Cumm) = k3pr.observations(pair, length - 2);
    }
    require(lastTime >= now - 60 minutes && lastTime <= now - 15 minutes, 'bad last time');
    if (token0 == quote) {
      uint currPx0Cumm = currentPx0Cumm(pair);
      return (currPx0Cumm - lastPx0Cumm) / (now - lastTime);
    } else {
      uint currPx1Cumm = currentPx1Cumm(pair);
      return (currPx1Cumm - lastPx1Cumm) / (now - lastTime);
    }
  }

  function currentPx0Cumm(address pair) internal view returns (uint px0Cumm) {
    uint32 currTime = uint32(now);
    px0Cumm = IUniswapV2Pair(pair).price0CumulativeLast();
    (uint reserve0, uint reserve1, uint32 lastTime) = IUniswapV2Pair(pair).getReserves();
    if (lastTime != now) {
      uint32 timeElapsed = currTime - lastTime;
      px0Cumm += uint((reserve1 << 112) / reserve0) * timeElapsed;
    }
  }

  function currentPx1Cumm(address pair) internal view returns (uint px1Cumm) {
    uint32 currTime = uint32(now);
    px1Cumm = IUniswapV2Pair(pair).price1CumulativeLast();
    (uint reserve0, uint reserve1, uint32 lastTime) = IUniswapV2Pair(pair).getReserves();
    if (lastTime != now) {
      uint32 timeElapsed = currTime - lastTime;
      px1Cumm += uint((reserve0 << 112) / reserve1) * timeElapsed;
    }
  }
}
