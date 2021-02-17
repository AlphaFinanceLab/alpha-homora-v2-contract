pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IBaseOracle.sol';

contract AggregatorOracle is IBaseOracle, Governable {
  using SafeMath for uint;

  uint public constant MAX_PRICE_DEVIATION = 1.05e18;
  mapping(address => uint) public primarySourceCount;
  mapping(address => mapping(uint => IBaseOracle)) public primarySources;

  constructor() public {
    __Governable__init();
  }

  function setPrimarySources(address token, IBaseOracle[] memory sources) external onlyGov {
    _setPrimarySources(token, sources);
  }

  function setMultiPrimarySources(address[] memory tokens, IBaseOracle[][] memory allSources)
    external
    onlyGov
  {
    require(tokens.length == allSources.length, 'inconsistent length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      _setPrimarySources(tokens[idx], allSources[idx]);
    }
  }

  function _setPrimarySources(address token, IBaseOracle[] memory sources) internal {
    primarySourceCount[token] = sources.length;
    for (uint idx = 0; idx < sources.length; idx++) {
      primarySources[token][idx] = sources[idx];
    }
  }

  function getETHPx(address token) external view override returns (uint) {
    uint candidateSourceCount = primarySourceCount[token];
    require(candidateSourceCount > 0, 'no primary source');
    uint[] memory prices = new uint[](candidateSourceCount);
    uint validSourceCount = 0;
    for (uint idx = 0; idx < candidateSourceCount; idx++) {
      try primarySources[token][idx].getETHPx(token) returns (uint px) {
        prices[validSourceCount++] = px;
      } catch {}
    }
    require(validSourceCount > 0, 'no valid source');
    for (uint i = 0; i < validSourceCount - 1; i++) {
      for (uint j = 0; j < validSourceCount - i - 1; j++) {
        if (prices[j] > prices[j + 1]) {
          (prices[j], prices[j + 1]) = (prices[j + 1], prices[j]);
        }
      }
    }
    if (validSourceCount == 1) {
      return prices[0];
    } else if (validSourceCount == 2) {
      require(
        prices[1].mul(1e18) / prices[0] <= MAX_PRICE_DEVIATION,
        'too much deviation (2 valid sources)'
      );
      return prices[0].add(prices[1]) / 2;
    } else if (validSourceCount == 3) {
      bool midMinOk = prices[1].mul(1e18) / prices[0] <= MAX_PRICE_DEVIATION;
      bool maxMidOk = prices[2].mul(1e18) / prices[1] <= MAX_PRICE_DEVIATION;
      if (midMinOk && maxMidOk) {
        return prices[1];
      } else if (midMinOk) {
        return prices[0].add(prices[1]) / 2;
      } else if (maxMidOk) {
        return prices[1].add(prices[2]) / 2;
      } else {
        revert('too much deviation (3 valid sources)');
      }
    } else {
      revert('more than 3 valid sources not supported');
    }
  }
}
