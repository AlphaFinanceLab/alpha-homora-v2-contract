pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/ICurvePool.sol';

interface IERC20Decimal {
  function decimals() external view returns (uint8);
}

contract CurveOracle is IBaseOracle {
  using SafeMath for uint;

  IBaseOracle public tokenOracle;

  constructor(IBaseOracle _tokenOracle) public {
    tokenOracle = _tokenOracle;
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param token The ERC-20 token to check the value.
  function getETHPx(address token) external view override returns (uint) {
    ICurvePool pool = ICurvePool(token);
    uint minPx = uint(-1);
    for (uint idx = 0; ; idx++) {
      try pool.coins(idx) returns (address coin) {
        uint decimals = IERC20Decimal(coin).decimals();
        uint tokenPx = tokenOracle.getETHPx(coin);
        if (decimals < 18) tokenPx = tokenPx.div(10**(18 - decimals));
        if (decimals > 18) tokenPx = tokenPx.mul(10**(decimals - 18));
        if (tokenPx < minPx) minPx = tokenPx;
      } catch (bytes memory) {
        break;
      }
    }
    require(minPx != uint(-1), 'no min px');
    return minPx.mul(pool.get_virtual_price()).div(1e18);
  }
}
