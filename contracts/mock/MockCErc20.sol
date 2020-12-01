pragma solidity 0.6.12;

import '../../interfaces/ICErc20.sol';
import './MockERC20.sol';

contract MockCErc20 is ICErc20 {
  MockERC20 public underlying;
  mapping(address => uint) public balance;

  constructor(MockERC20 _underlying) public {
    underlying = _underlying;
  }

  function borrowBalanceCurrent(address account) external override returns (uint) {
    return balance[account];
  }

  function borrowBalanceStored(address account) external override view returns (uint) {
    return balance[account];
  }

  function borrow(uint borrowAmount) external override returns (uint) {
    balance[msg.sender] += borrowAmount;
    underlying.mint(msg.sender, borrowAmount);
    return borrowAmount;
  }

  function repayBorrow(uint repayAmount) external override {
    balance[msg.sender] -= repayAmount;
    underlying.burn(msg.sender, repayAmount);
  }
}
