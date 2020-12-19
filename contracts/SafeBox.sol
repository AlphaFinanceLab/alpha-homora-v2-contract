pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/ERC20.sol';

import './Governable.sol';

contract SafeBox is Governable {
  constructor() public {
    __Governable__init();
  }

  // function deposit(address cToken, address amount) external {
  //   address cToken = cTokens[token];
  //   require(cToken != address(0));
  //   // TODO
  // }

  // function withdraw(address) external {
  //   address cToken = cTokens[token];
  //   require(cToken != address(0));
  //   // TODO
  // }
}
