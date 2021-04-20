// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IBaseOracle.sol';

contract AggregatorOracle is IBaseOracle, Governable {
  using SafeMath for uint;

  event SetPrimarySources(address indexed token, uint maxPriceDeviation, IBaseOracle[] oracles);

  address public constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2; // WETH address
  mapping(address => uint) public primarySourceCount; // Mapping from token to number of sources
  mapping(address => mapping(uint => IBaseOracle)) public primarySources; // Mapping from token to (mapping from index to oracle source)
  mapping(address => uint) public maxPriceDeviations; // Mapping from token to max price deviation (multiplied by 1e18)

  uint public constant MIN_PRICE_DEVIATION = 1e18; // min price deviation
  uint public constant MAX_PRICE_DEVIATION = 1.5e18; // max price deviation

  constructor() public {
    __Governable__init();
  }

  /// @dev Set oracle primary sources for the token
  /// @param token Token address to set oracle sources
  /// @param maxPriceDeviation Max price deviation (in 1e18) for token
  /// @param sources Oracle sources for the token
  function setPrimarySources(
    address token,
    uint maxPriceDeviation,
    IBaseOracle[] memory sources
  ) external onlyGov {
    _setPrimarySources(token, maxPriceDeviation, sources);
  }

  /// @dev Set oracle primary sources for multiple tokens
  /// @param tokens List of token addresses to set oracle sources
  /// @param maxPriceDeviationList List of max price deviations (in 1e18) for tokens
  /// @param allSources List of oracle sources for tokens
  function setMultiPrimarySources(
    address[] memory tokens,
    uint[] memory maxPriceDeviationList,
    IBaseOracle[][] memory allSources
  ) external onlyGov {
    require(tokens.length == allSources.length, 'inconsistent length');
    require(tokens.length == maxPriceDeviationList.length, 'inconsistent length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      _setPrimarySources(tokens[idx], maxPriceDeviationList[idx], allSources[idx]);
    }
  }

  /// @dev Set oracle primary sources for tokens
  /// @param token Token to set oracle sources
  /// @param maxPriceDeviation Max price deviation (in 1e18) for token
  /// @param sources Oracle sources for the token
  function _setPrimarySources(
    address token,
    uint maxPriceDeviation,
    IBaseOracle[] memory sources
  ) internal {
    primarySourceCount[token] = sources.length;
    require(
      maxPriceDeviation >= MIN_PRICE_DEVIATION && maxPriceDeviation <= MAX_PRICE_DEVIATION,
      'bad max deviation value'
    );
    require(sources.length <= 3, 'sources length exceed 3');
    maxPriceDeviations[token] = maxPriceDeviation;
    for (uint idx = 0; idx < sources.length; idx++) {
      primarySources[token][idx] = sources[idx];
    }
    emit SetPrimarySources(token, maxPriceDeviation, sources);
  }

  /// @dev Return token price relative to ETH, multiplied by 2**112
  /// @param token Token to get price of
  /// NOTE: Support at most 3 oracle sources per token
  function getETHPx(address token) public view override returns (uint) {
    uint candidateSourceCount = primarySourceCount[token];
    require(candidateSourceCount > 0, 'no primary source');
    uint[] memory prices = new uint[](candidateSourceCount);

    // Get valid oracle sources
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
    uint maxPriceDeviation = maxPriceDeviations[token];

    // Algo:
    // - 1 valid source --> return price
    // - 2 valid sources
    //     --> if the prices within deviation threshold, return average
    //     --> else revert
    // - 3 valid sources --> check deviation threshold of each pair
    //     --> if all within threshold, return median
    //     --> if one pair within threshold, return average of the pair
    //     --> if none, revert
    // - revert otherwise
    if (validSourceCount == 1) {
      return prices[0]; // if 1 valid source, return
    } else if (validSourceCount == 2) {
      require(
        prices[1].mul(1e18) / prices[0] <= maxPriceDeviation,
        'too much deviation (2 valid sources)'
      );
      return prices[0].add(prices[1]) / 2; // if 2 valid sources, return average
    } else if (validSourceCount == 3) {
      bool midMinOk = prices[1].mul(1e18) / prices[0] <= maxPriceDeviation;
      bool maxMidOk = prices[2].mul(1e18) / prices[1] <= maxPriceDeviation;
      if (midMinOk && maxMidOk) {
        return prices[1]; // if 3 valid sources, and each pair is within thresh, return median
      } else if (midMinOk) {
        return prices[0].add(prices[1]) / 2; // return average of pair within thresh
      } else if (maxMidOk) {
        return prices[1].add(prices[2]) / 2; // return average of pair within thresh
      } else {
        revert('too much deviation (3 valid sources)');
      }
    } else {
      revert('more than 3 valid sources not supported');
    }
  }

  /// @dev Return the price of token0/token1, multiplied by 1e18
  /// @notice One of the input tokens must be WETH
  function getPrice(address token0, address token1) external view returns (uint, uint) {
    require(token0 == WETH || token1 == WETH, 'one of the requested tokens must be ETH or WETH');
    if (token0 == WETH) {
      return (uint(2**112).mul(1e18).div(getETHPx(token1)), block.timestamp);
    } else {
      return (getETHPx(token0).mul(1e18).div(2**112), block.timestamp);
    }
  }
}
