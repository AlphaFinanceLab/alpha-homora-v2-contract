pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

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
  string public constant ETH = 'ETH';

  IStdReference public ref; // Standard reference
  uint public maxDelayTime; // Max price update delay time

  mapping(address => string) public symbols; // Mapping from token to symbol string

  constructor(IStdReference _ref, uint _maxDelayTime) public {
    __Governable__init();
    ref = _ref;
    maxDelayTime = _maxDelayTime;
  }

  /// @dev Set token symbols
  /// @param syms List of string symbols
  /// @param tokens List of tokens
  function setSymbols(string[] memory syms, address[] memory tokens) external onlyGov {
    require(syms.length == tokens.length, 'inconsistent length');
    for (uint idx = 0; idx < syms.length; idx++) {
      symbols[tokens[idx]] = syms[idx];
    }
  }

  /// @dev Set standard reference source
  /// @param _ref Standard reference source
  function setRef(IStdReference _ref) external onlyGov {
    ref = _ref;
  }

  /// @dev Set max price update delay
  /// @param _maxDelayTime Max price update delay
  function setMaxDelayTime(uint _maxDelayTime) external onlyGov {
    maxDelayTime = _maxDelayTime;
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param token The ERC-20 token to check the value.
  function getETHPx(address token) external view override returns (uint) {
    string memory sym = symbols[token];
    require(bytes(sym).length != 0, 'no mapping');
    uint decimals = uint(BandDetailedERC20(token).decimals());
    IStdReference.ReferenceData memory data = ref.getReferenceData(sym, ETH);
    require(data.lastUpdatedBase >= block.timestamp.sub(maxDelayTime), 'delayed base data');
    require(data.lastUpdatedQuote >= block.timestamp.sub(maxDelayTime), 'delayed quote data');
    return data.rate.mul(2**112).div(10**decimals);
  }
}
