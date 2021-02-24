pragma solidity 0.6.12;

interface IAny {
  function approve(address, uint) external;

  function _setCreditLimit(address, uint) external;
}
