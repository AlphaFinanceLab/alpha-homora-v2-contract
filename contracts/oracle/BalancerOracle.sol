pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IBalancerPool.sol';
import '../utils/BNum.sol';

interface IERC20Decimal {
  function decimals() external view returns (uint8);
}

contract BalancerOracle is IBaseOracle, BNum {
  using SafeMath for uint;

  IBaseOracle public tokenOracle;

  constructor(IBaseOracle _tokenOracle) public {
    tokenOracle = _tokenOracle;
  }

  /// @dev Return fair reserve amounts given spot reserves, weights, and fair prices.
  /// @param resA Reserve of the first asset
  /// @param resB Reserev of the second asset
  /// @param wA Weight of the first asset
  /// @param wB Weight of the second asset
  /// @param pA Fair price of the first asset
  /// @param pB Fair price of the second asset
  function computeFairReserves(
    uint resA,
    uint resB,
    uint wA,
    uint wB,
    uint pA,
    uint pB
  ) internal pure returns (uint, uint) {
    uint r = bdiv(resA, resB);
    uint r1;
    {
      uint num = bmul(wA, pB);
      uint den = bmul(wB, pA);
      r1 = bdiv(num, den);
    }

    uint fairResA;
    uint fairResB;

    // fairResA = resA * (r1 / r) ^ wB
    // fairResB = resB * (r / r1) ^ wA
    if (r > r1) {
      uint ratio = bdiv(r1, r);
      uint powA = bpow(ratio, wB);
      uint powB = bpow(ratio, wA);
      fairResA = bmul(resA, powA);
      fairResB = bdiv(resB, powB);
    } else {
      uint ratio = bdiv(r, r1);
      uint powA = bpow(ratio, wB);
      uint powB = bpow(ratio, wA);
      fairResA = bdiv(resA, powA);
      fairResB = bmul(resB, powB);
    }
    return (fairResA, fairResB);
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param token The ERC-20 token to check the value.
  function getETHPx(address token) external view override returns (uint) {
    IBalancerPool pool = IBalancerPool(token);
    uint n = pool.getNumTokens();
    require(n == 2, 'num tokens not 2');
    address[] memory tokens = pool.getFinalTokens();
    address tokenA = tokens[0];
    address tokenB = tokens[1];
    uint wA = pool.getNormalizedWeight(tokenA);
    uint wB = pool.getNormalizedWeight(tokenB);

    uint pA = tokenOracle.getETHPx(tokenA);
    uint pB = tokenOracle.getETHPx(tokenB);

    uint resA = pool.getBalance(tokenA);
    uint resB = pool.getBalance(tokenB);

    (uint fairResA, uint fairResB) = computeFairReserves(resA, resB, wA, wB, pA, pB);

    uint totalSupply = pool.totalSupply();

    return fairResA.mul(pA).add(fairResB.mul(pB)).div(totalSupply);
  }
}
