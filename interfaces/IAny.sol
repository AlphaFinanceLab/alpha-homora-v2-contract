pragma solidity 0.6.12;

interface IAny {
  function approve(address, uint) external;

  function target() external view returns (address);

  function owner() external view returns (address);

  function masterMinter() external view returns (address);

  function issue(uint) external;

  function configureMinter(address, uint) external;

  function mint(address, uint) external;

  function increaseSupply(uint) external;

  function transfer(address, uint) external;

  function deposit(uint) external;

  function getModules() external view returns (address[] memory);

  function addMinter(address) external;

  function governance() external view returns (address);

  function createTokens(uint) external;

  function joinPool(uint, uint) external;

  function _setCreditLimit(address, uint) external;

  function setOracle(address) external;

  function decimals() external view returns (uint8);

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

  function addBank(address, address) external;

  function getFinalTokens() external view returns (address[] memory);

  function admin() external view returns (address);

  function token0() external view returns (address);

  function token1() external view returns (address);

  function symbol() external view returns (string memory);

  function execute(
    uint,
    address,
    bytes memory
  ) external returns (uint);
}
