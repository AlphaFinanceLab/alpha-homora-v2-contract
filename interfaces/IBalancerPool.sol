pragma solidity 0.6.12;

interface IBalancerPool {
  function getFinalTokens() external view returns (address[] memory);

  function getNormalizedWeight(address token) external view returns (uint);

  function getSwapFee() external view returns (uint);

  function getNumTokens() external view returns (uint);

  function getBalance(address token) external view returns (uint);

  function totalSupply() external view returns (uint);
}
