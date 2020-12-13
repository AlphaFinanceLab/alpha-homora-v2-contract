pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/ICurvePool.sol';
import '../../interfaces/ICurveRegistry.sol';

interface IERC20Decimal {
  function decimals() external view returns (uint8);
}

contract CurveOracle is IBaseOracle {
  using SafeMath for uint;

  IBaseOracle public tokenOracle;
  ICurveRegistry public registry;

  mapping(address => address[]) public ulTokens; // lpToken -> underlying token array
  mapping(address => address) public poolOf; // lpToken -> pool

  constructor(IBaseOracle _tokenOracle, ICurveRegistry _registry) public {
    tokenOracle = _tokenOracle;
    registry = _registry;
  }

  /// @dev Return pool address given LP token and update pool info if not exist.
  /// @param lp LP token to find the corresponding pool.
  function getPool(address lp) public returns (address) {
    address pool = poolOf[lp];
    if (pool == address(0)) {
      require(lp != address(0), 'no lp token');
      pool = registry.get_pool_from_lp_token(lp);
      poolOf[lp] = pool;
      uint n = registry.get_n_coins(pool);
      address[8] memory tokens = registry.get_coins(pool);
      ulTokens[lp] = new address[](n);
      for (uint i = 0; i < n; i++) {
        ulTokens[lp][i] = tokens[i];
      }
    }
    return pool;
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param lp The ERC-20 LP token to check the value.
  function getETHPx(address lp) external view override returns (uint) {
    ICurvePool pool = ICurvePool(poolOf[lp]);
    uint minPx = uint(-1);
    address[] memory tokens = ulTokens[lp];
    uint n = tokens.length;
    for (uint idx = 0; idx < n; idx++) {
      address token = tokens[idx];
      uint decimals = IERC20Decimal(token).decimals();
      uint tokenPx = tokenOracle.getETHPx(token);
      if (decimals < 18) tokenPx = tokenPx.div(10**(18 - decimals));
      if (decimals > 18) tokenPx = tokenPx.mul(10**(decimals - 18));
      if (tokenPx < minPx) minPx = tokenPx;
    }
    require(minPx != uint(-1), 'no min px');
    return minPx.mul(pool.get_virtual_price()).div(1e18);
  }
}
