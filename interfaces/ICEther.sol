pragma solidity 0.6.12;

interface ICEther {
  function mint() external payable;

  function balanceOf(address who) external view returns (uint);
}
