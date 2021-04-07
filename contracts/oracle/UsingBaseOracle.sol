// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;

import '../../interfaces/IBaseOracle.sol';

contract UsingBaseOracle {
  IBaseOracle public immutable base; // Base oracle source

  constructor(IBaseOracle _base) public {
    base = _base;
  }
}
