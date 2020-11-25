pragma solidity 0.6.12;

abstract contract IKeep3rV1Oracle {
  struct Observation {
    uint timestamp;
    uint price0Cumulative;
    uint price1Cumulative;
  }

  mapping(address => Observation[]) public observations;

  function observationLength(address pair) external view virtual returns (uint);

  function pairFor(address tokenA, address tokenB) external pure virtual returns (address);

  function pairForWETH(address tokenA) external pure virtual returns (address);
}
