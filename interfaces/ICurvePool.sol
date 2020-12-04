pragma solidity 0.6.12;

interface ICurvePool {
  function N_COINS() external view returns (uint128);

  function PRECISION_MUL(uint index) external view returns (uint);

  function coins(uint index) external view returns (address);

  function get_virtual_price() external view returns (uint);
}
