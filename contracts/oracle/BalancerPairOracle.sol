// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import './UsingBaseOracle.sol';
import '../utils/BNum.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IBalancerPool.sol';

contract BalancerPairOracle is UsingBaseOracle, IBaseOracle, BNum {
  using SafeMath for uint;

  constructor(IBaseOracle _base) public UsingBaseOracle(_base) {}

  /// @dev Return fair reserve amounts given spot reserves, weights, and fair prices.
  /// @param resA Reserve of the first asset
  /// @param resB Reserve of the second asset
  /// @param wA Weight of the first asset
  /// @param wB Weight of the second asset
  /// @param pxA Fair price of the first asset
  /// @param pxB Fair price of the second asset
  function computeFairReserves(
    uint resA,
    uint resB,
    uint wA,
    uint wB,
    uint pxA,
    uint pxB
  ) internal pure returns (uint fairResA, uint fairResB) {
    // NOTE: wA + wB = 1 (normalize weights)
    // constant product = resA^wA * resB^wB
    // constraints:
    // - fairResA^wA * fairResB^wB = constant product
    // - fairResA * pxA / wA = fairResB * pxB / wB
    // Solving equations:
    // --> fairResA^wA * (fairResA * (pxA * wB) / (wA * pxB))^wB = constant product
    // --> fairResA / r1^wB = constant product
    // --> fairResA = resA^wA * resB^wB * r1^wB
    // --> fairResA = resA * (resB/resA)^wB * r1^wB = resA * (r1/r0)^wB
    uint r0 = bdiv(resA, resB);
    uint r1 = bdiv(bmul(wA, pxB), bmul(wB, pxA));
    // fairResA = resA * (r1 / r0) ^ wB
    // fairResB = resB * (r0 / r1) ^ wA
    if (r0 > r1) {
      uint ratio = bdiv(r1, r0);
      fairResA = bmul(resA, bpow(ratio, wB));
      fairResB = bdiv(resB, bpow(ratio, wA));
    } else {
      uint ratio = bdiv(r0, r1);
      fairResA = bdiv(resA, bpow(ratio, wB));
      fairResB = bmul(resB, bpow(ratio, wA));
    }
  }

  /// @dev Return the value of the given input as ETH per unit, multiplied by 2**112.
  /// @param token The ERC-20 token to check the value.
  function getETHPx(address token) external view override returns (uint) {
    IBalancerPool pool = IBalancerPool(token);
    require(pool.getNumTokens() == 2, 'num tokens must be 2');
    address[] memory tokens = pool.getFinalTokens();
    address tokenA = tokens[0];
    address tokenB = tokens[1];
    uint pxA = base.getETHPx(tokenA);
    uint pxB = base.getETHPx(tokenB);
    (uint fairResA, uint fairResB) =
      computeFairReserves(
        pool.getBalance(tokenA),
        pool.getBalance(tokenB),
        pool.getNormalizedWeight(tokenA),
        pool.getNormalizedWeight(tokenB),
        pxA,
        pxB
      );
    // use fairReserveA and fairReserveB to compute LP token price
    // LP price = (fairResA * pxA + fairResB * pxB) / totalLPSupply
    return fairResA.mul(pxA).add(fairResB.mul(pxB)).div(pool.totalSupply());
  }
}
