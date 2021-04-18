// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;

import '../../interfaces/IBaseOracle.sol';
import '../Governable.sol';

contract CoreOracle is IBaseOracle, Governable {
  event SetRoute(address indexed token, address route);
  mapping(address => address) public routes; // Mapping from token to oracle source

  constructor() public {
    __Governable__init();
  }

  /// @dev Set oracle source routes for tokens
  /// @param tokens List of tokens
  /// @param targets List of oracle source routes
  function setRoute(address[] calldata tokens, address[] calldata targets) external onlyGov {
    require(tokens.length == targets.length, 'inconsistent length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      routes[tokens[idx]] = targets[idx];
      emit SetRoute(tokens[idx], targets[idx]);
    }
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param token The ERC-20 token to check the value.
  function getETHPx(address token) external view override returns (uint) {
    uint px = IBaseOracle(routes[token]).getETHPx(token);
    require(px != 0, 'price oracle failure');
    return px;
  }
}
