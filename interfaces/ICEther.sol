pragma solidity 0.6.12;

interface ICEther {
  function borrowBalanceCurrent(address account) external returns (uint);

  function borrowBalanceStored(address account) external view returns (uint);

  function borrow(uint borrowAmount) external returns (uint);

  function repayBorrow() external payable;
}
