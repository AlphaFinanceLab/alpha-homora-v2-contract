pragma solidity 0.6.12;

import './IStakingRewards.sol';

interface IStakingRewardsEx is IStakingRewards {
  function rewardsToken() external view returns (address);

  function stakingToken() external view returns (address);
}
