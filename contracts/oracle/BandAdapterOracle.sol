// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IBaseOracle.sol';

interface IStdReference {
  /// A structure returned whenever someone requests for standard reference data.
  struct ReferenceData {
    uint rate; // base/quote exchange rate, multiplied by 1e18.
    uint lastUpdatedBase; // UNIX epoch of the last time when base price gets updated.
    uint lastUpdatedQuote; // UNIX epoch of the last time when quote price gets updated.
  }

  /// @dev Returns the price data for the given base/quote pair. Revert if not available.
  function getReferenceData(string memory _base, string memory _quote)
    external
    view
    returns (ReferenceData memory);

  /// @dev Similar to getReferenceData, but with multiple base/quote pairs at once.
  function getReferenceDataBulk(string[] memory _bases, string[] memory _quotes)
    external
    view
    returns (ReferenceData[] memory);
}

interface BandDetailedERC20 {
  function decimals() external view returns (uint8);
}

contract BandAdapterOracle is IBaseOracle, Governable {
  using SafeMath for uint;

  event SetSymbol(address token, string symbol);
  event SetRef(address ref);
  event SetMaxDelayTime(address token, uint maxDelayTime);

  string public constant ETH = 'ETH';
  address public constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;

  IStdReference public ref; // Standard reference

  mapping(address => string) public symbols; // Mapping from token to symbol string
  mapping(address => uint) public maxDelayTimes; // Mapping from token address to max delay time

  constructor(IStdReference _ref) public {
    __Governable__init();
    ref = _ref;
  }

  /// @dev Set token symbols
  /// @param tokens List of tokens
  /// @param syms List of string symbols
  function setSymbols(address[] memory tokens, string[] memory syms) external onlyGov {
    require(syms.length == tokens.length, 'inconsistent length');
    for (uint idx = 0; idx < syms.length; idx++) {
      symbols[tokens[idx]] = syms[idx];
      emit SetSymbol(tokens[idx], syms[idx]);
    }
  }

  /// @dev Set standard reference source
  /// @param _ref Standard reference source
  function setRef(IStdReference _ref) external onlyGov {
    ref = _ref;
    emit SetRef(address(_ref));
  }

  /// @dev Set max delay time for each token
  /// @param tokens list of tokens to set max delay
  /// @param maxDelays list of max delay times to set to
  function setMaxDelayTimes(address[] calldata tokens, uint[] calldata maxDelays) external onlyGov {
    require(tokens.length == maxDelays.length, 'tokens & maxDelays length mismatched');
    for (uint idx = 0; idx < tokens.length; idx++) {
      maxDelayTimes[tokens[idx]] = maxDelays[idx];
      emit SetMaxDelayTime(tokens[idx], maxDelays[idx]);
    }
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param token The ERC-20 token to check the value.
  function getETHPx(address token) external view override returns (uint) {
    if (token == WETH || token == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) return uint(2**112);

    string memory sym = symbols[token];
    uint maxDelayTime = maxDelayTimes[token];
    require(bytes(sym).length != 0, 'no mapping');
    require(maxDelayTime != 0, 'max delay time not set');
    uint decimals = uint(BandDetailedERC20(token).decimals());
    IStdReference.ReferenceData memory data = ref.getReferenceData(sym, ETH);
    require(data.lastUpdatedBase >= block.timestamp.sub(maxDelayTime), 'delayed base data');
    require(data.lastUpdatedQuote >= block.timestamp.sub(maxDelayTime), 'delayed quote data');
    return data.rate.mul(2**112).div(10**decimals);
  }
}
