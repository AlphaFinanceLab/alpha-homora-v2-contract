pragma solidity 0.6.12;

interface ICToken {
  function borrowBalanceCurrent(address account) external returns (uint);

  function borrowBalanceStored(address account) external view returns (uint);

  function borrow(uint borrowAmount) external returns (uint);
}

interface ICErc20 is ICToken {
  function repayBorrow(uint repayAmount) external;
}

interface ICEther is ICToken {
  function repayBorrow() external payable;
}
