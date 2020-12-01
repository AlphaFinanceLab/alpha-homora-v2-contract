pragma solidity 0.6.12;

import '../../interfaces/IBaseOracle.sol';

contract MockOracle is IBaseOracle {
  mapping(address => uint) public prices;

  function setETHPx(address token, uint price) external {
    prices[token] = price;
  }

  function getETHPx(address token) external override view returns (uint) {
    return prices[token];
  }
}
