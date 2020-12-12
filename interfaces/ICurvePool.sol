pragma solidity 0.6.12;

interface ICurvePool {
  function coins(uint index) external view returns (address);

  function add_liquidity(uint[3] calldata, uint) external;

  function remove_liquidity(uint, uint[3] calldata) external;

  function remove_liquidity_imbalance(uint[3] calldata, uint) external;

  function remove_liquidity_one_coin(
    uint,
    int128,
    uint
  ) external;

  function get_virtual_price() external view returns (uint);
}
