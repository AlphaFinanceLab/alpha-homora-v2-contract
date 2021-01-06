pragma solidity 0.6.12;

import '../../interfaces/IBaseOracle.sol';
import '../Governable.sol';

contract CoreOracle is IBaseOracle, Governable {
  mapping(address => address) public routes;

  constructor() public {
    __Governable__init();
  }

  function setRoute(address[] calldata tokens, address[] calldata targets) external onlyGov {
    require(tokens.length == targets.length, '!length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      routes[tokens[idx]] = targets[idx];
    }
  }

  function getETHPx(address token) external view override returns (uint) {
    return IBaseOracle(routes[token]).getETHPx(token);
  }
}
