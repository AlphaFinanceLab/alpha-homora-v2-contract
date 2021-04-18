pragma solidity 0.6.12;


import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

contract Test {

  // using SafeMath for uint;

  // // uint public weightA, weightB;
  // uint public BASE = 1e18;

  // constructor() public {
  //   weightA = 2;
  //   weightB = 1;
  // }

  // function getBBalance(uint balA, uint priceA, uint priceB) public returns (uint) {
  //   return balA.mul(priceA).mul(weightB).mul(BASE).div(priceB).div(weightA);
  // }

  // function bpow(uint base, uint ind) internal pure returns (uint, uint) {
  //   uint prod = BASE;
  //   uint mag = 0;
  //   for(uint i=0;i<ind;i++) {
  //     prod = prod.mul(base);

  //     if(prod > BASE.mul(BASE)) {
  //       prod = prod.div(BASE);
  //       mag++;
  //     }
  //   }
  //   return (prod, mag);
  // }

  // function computeTarget(uint balA, uint balB) internal pure returns (uint, uint) {
  //   (uint prod1, uint mag1) = pow(balA, weightA);
  //   (uint prod2, uint mag2) = pow(balB, weightB);
  //   uint prod = prod1.mul(prod2);
  //   uint mag = mag1.add(mag2);
  //   if (prod > BASE.mul(BASE)) {
  //     prod = prod.div(BASE);
  //     mag ++;
  //   }
  //   return (prod, mag);
  // }

  // function isGreater(uint prod1, uint mag1, uint prod2, uint mag2) internal pure returns (bool) {
  //   if (mag1 > mag2) return true;
  //   if (mag1 < mag2) return false;
  //   return prod1 > prod2;
  // }

  // function evaluate(uint balA, uint balB, uint targetProd, uint targetMag) returns (uint) {

  //   (uint prod, uint mag) = 
  // }
}
