pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IBaseOracle.sol';

interface IAggregatorV3Interface {
  function decimals() external view returns (uint8);

  function description() external view returns (string memory);

  function version() external view returns (uint);

  // getRoundData and latestRoundData should both raise "No data present"
  // if they do not have data to report, instead of returning unset values
  // which could be misinterpreted as actual reported values.
  function getRoundData(uint80 _roundId)
    external
    view
    returns (
      uint80 roundId,
      int answer,
      uint startedAt,
      uint updatedAt,
      uint80 answeredInRound
    );

  function latestRoundData()
    external
    view
    returns (
      uint80 roundId,
      int answer,
      uint startedAt,
      uint updatedAt,
      uint80 answeredInRound
    );
}

interface ChainlinkDetailedERC20 {
  function decimals() external view returns (uint8);
}

contract ChainlinkAdapterOracle is IBaseOracle, Governable {
  using SafeMath for uint;

  event SetRefETH(address token, address ref);
  event SetRefUSD(address token, address ref);
  event SetMaxDelayTime(address token, uint maxDelayTime);
  event SetRefETHUSD(address ref);

  address public constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
  address public refETHUSD = 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419; // ETH-USD price reference
  mapping(address => address) public refsETH; // Mapping from token address to ETH price reference
  mapping(address => address) public refsUSD; // Mapping from token address to USD price reference
  mapping(address => uint) public maxDelayTimes; // Mapping from token address to max delay time

  constructor() public {
    __Governable__init();
  }

  /// @dev Set price reference for ETH pair
  /// @param tokens list of tokens to set reference
  /// @param refs list of reference contract addresses
  function setRefsETH(address[] calldata tokens, address[] calldata refs) external onlyGov {
    require(tokens.length == refs.length, 'tokens & refs length mismatched');
    for (uint idx = 0; idx < tokens.length; idx++) {
      refsETH[tokens[idx]] = refs[idx];
      emit SetRefETH(tokens[idx], refs[idx]);
    }
  }

  /// @dev Set price reference for USD pair
  /// @param tokens list of tokens to set reference
  /// @param refs list of reference contract addresses
  function setRefsUSD(address[] calldata tokens, address[] calldata refs) external onlyGov {
    require(tokens.length == refs.length, 'tokens & refs length mismatched');
    for (uint idx = 0; idx < tokens.length; idx++) {
      refsUSD[tokens[idx]] = refs[idx];
      emit SetRefUSD(tokens[idx], refs[idx]);
    }
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

  /// @dev Set ETH-USD to the new reference
  /// @param _refETHUSD The new ETH-USD reference address to set to
  function setRefETHUSD(address _refETHUSD) external onlyGov {
    refETHUSD = _refETHUSD;
    emit SetRefETHUSD(_refETHUSD);
  }

  /// @dev Return token price in ETH, multiplied by 2**112
  /// @param token Token address to get price
  function getETHPx(address token) external view override returns (uint) {
    if (token == WETH || token == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) return uint(2**112);
    uint decimals = uint(ChainlinkDetailedERC20(token).decimals());
    uint maxDelayTime = maxDelayTimes[token];
    require(maxDelayTime != 0, 'max delay time not set');

    // 1. Check token-ETH price ref
    address refETH = refsETH[token];
    if (refETH != address(0)) {
      (, int answer, , uint updatedAt, ) = IAggregatorV3Interface(refETH).latestRoundData();
      require(updatedAt >= block.timestamp.sub(maxDelayTime), 'delayed update time');
      return uint(answer).mul(2**112).div(10**decimals);
    }

    // 2. Check token-USD price ref
    address refUSD = refsUSD[token];
    if (refUSD != address(0)) {
      (, int answer, , uint updatedAt, ) = IAggregatorV3Interface(refUSD).latestRoundData();
      require(updatedAt >= block.timestamp.sub(maxDelayTime), 'delayed update time');
      (, int ethAnswer, , uint ethUpdatedAt, ) =
        IAggregatorV3Interface(refETHUSD).latestRoundData();
      require(ethUpdatedAt >= block.timestamp.sub(maxDelayTime), 'delayed eth-usd update time');
      return uint(answer).mul(2**112).div(uint(ethAnswer)).div(10**decimals);
    }

    revert('no valid price reference for token');
  }
}
