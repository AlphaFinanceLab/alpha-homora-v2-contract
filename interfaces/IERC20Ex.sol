pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';

// Export IERC20 interface for mainnet-fork testing.
interface IERC20Ex is IERC20 {
  function name() external view returns (string memory);

  function owner() external view returns (address);

  function issue(uint) external;

  function issue(address, uint) external;

  function mint(address, uint) external;

  function mint(
    address,
    uint,
    uint
  ) external returns (bool);

  function configureMinter(address, uint) external returns (bool);

  function masterMinter() external view returns (address);

  function deposit() external payable;

  function deposit(uint) external;

  function decimals() external view returns (uint);

  function target() external view returns (address);

  function erc20Impl() external view returns (address);

  function custodian() external view returns (address);

  function requestPrint(address, uint) external returns (bytes32);

  function confirmPrint(bytes32) external;

  function invest(uint) external;

  function increaseSupply(uint) external;

  function supplyController() external view returns (address);

  function getModules() external view returns (address[] memory);

  function addMinter(address) external;
}
