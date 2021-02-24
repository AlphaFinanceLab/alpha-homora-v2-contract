pragma solidity 0.6.12;

import './BasicSpell.sol';
import '../Governable.sol';

contract WhitelistSpell is BasicSpell, Governable {
  mapping(address => bool) public whitelistedLpTokens; // mapping from lp token to whitelist status

  constructor(
    IBank _bank,
    address _werc20,
    address _weth
  ) public BasicSpell(_bank, _werc20, _weth) {
    __Governable__init();
  }

  function setWhitelistLPTokens(address[] calldata lpTokens, bool[] calldata statuses)
    external
    onlyGov
  {
    require(lpTokens.length == statuses.length, 'lpTokens & statuses length mismatched');
    for (uint idx = 0; idx < lpTokens.length; idx++) {
      whitelistedLpTokens[lpTokens[idx]] = statuses[idx];
    }
  }
}
