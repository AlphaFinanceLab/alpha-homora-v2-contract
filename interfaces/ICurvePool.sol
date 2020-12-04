pragma solidity 0.6.12;

interface ICurvePool {
  function coins(uint index) external view returns (address);

  function get_virtual_price() external view returns (uint);
}
