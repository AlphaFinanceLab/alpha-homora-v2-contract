pragma solidity 0.6.12;

import './BaseK3PROracle.sol';
import '../Governable.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IKeep3rV1Oracle.sol';

contract BasicK3PROracle is IBaseOracle, BaseK3PROracle, Governable {
  /// @dev Create the contract and initialize the first governor.
  /// @param _k3pr The keeper oracle smart contract.
  constructor(IKeep3rV1Oracle _k3pr) public BaseK3PROracle(_k3pr) {
    Governable.initialize();
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param token The ERC-20 token to check the value.
  function getETHPx(address token) external view override returns (uint) {
    return 0;
    // return prices[token];
  }
}
