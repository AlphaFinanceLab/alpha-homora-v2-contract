pragma solidity 0.6.12;

import '../../interfaces/IKeep3rV1Oracle.sol';

contract BaseK3PROracle {
  IKeep3rV1Oracle public k3pr;

  constructor(IKeep3rV1Oracle _k3pr) public {
    k3pr = _k3pr;
  }
}
