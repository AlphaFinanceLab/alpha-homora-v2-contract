pragma solidity 0.6.12;

interface IAny {
  function approve(address, uint) external;

  function _setCreditLimit(address, uint) external;

  function setOracle(address) external;

  function poolInfo(uint)
    external
    view
    returns (
      address,
      uint,
      uint,
      uint
    );

  function poolLength() external view returns (uint);

  function setWhitelistSpells(address[] memory, bool[] memory) external;

  function setWhitelistTokens(address[] memory, bool[] memory) external;

  function getPrice(address, address) external view returns (uint, uint);

  function owner() external view returns (address);

  function work(
    uint,
    address,
    uint,
    uint,
    bytes memory
  ) external;

  function setPrices(
    address[] memory,
    address[] memory,
    uint[] memory
  ) external;

  function getETHPx(address) external view returns (uint);

  function balanceOf(address) external view returns (uint);
}
