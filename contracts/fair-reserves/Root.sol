pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

library FMath {
    using SafeMath for uint;
    
    uint public constant BASE = 1e18;
    
    function fmul(uint lhs, uint rhs) external pure returns (uint) {
        return lhs.mul(rhs).div(BASE);
    }
    
    function fdiv(uint lhs, uint rhs) external pure returns (uint) {
        return lhs.mul(BASE).div(rhs);
    }
     
}

contract Root {
    using FMath for uint;
    using SafeMath for uint;
    
    uint public constant BASE = 1e18;
    
    function badd(uint mantissa1, int order1, uint mantissa2, int order2) public pure returns (uint mantissa, int order) {
        // add 
        if (order1 == order2) {
            order = order1;
            mantissa = mantissa1.add(mantissa2);
        } else if (order1 < order2) {
            uint orderDiff = uint(order2 - order1);
            if (orderDiff <= 18) {
                mantissa = mantissa2 + mantissa1 / (10**orderDiff);
                order = order2;
            } else {
                mantissa = mantissa2;
                order = order2;
            }
        } else if (order1 > order2) {
            uint orderDiff = uint(order1 - order2);
            if (orderDiff <= 18) {
                mantissa = mantissa1 + mantissa2 / (10**orderDiff);
                order = order1;
            } else {
                mantissa = mantissa1;
                order = order1;
            }
        }
        
        // check overflow
        (mantissa, order) = rewrite(mantissa, order);
    }
    
    function bmulConst(uint mantissa, int order, uint n) public pure returns (uint mantissaOut, int orderOut) {
        mantissaOut = mantissa.mul(n);
        orderOut = order;
        
        (mantissaOut, orderOut) = rewrite(mantissaOut, orderOut);
    }
    
    // n < 100
    function bdivConst(uint mantissa, int order, uint n) public pure returns (uint mantissaOut, int orderOut) {
        mantissaOut = mantissa.mul(100) / n;
        orderOut = order - 2;
        (mantissaOut, orderOut) = rewrite(mantissaOut, orderOut);
    }
    
    
    // 1e19 > mantissa >= 1e18
    function bmul(uint mantissa1, int order1, uint mantissa2, int order2) public pure returns (uint mantissa, int order) {
        mantissa = mantissa1.fmul(mantissa2);
        order = order1 + order2;
        (mantissa, order) = rewrite(mantissa, order);
    }
    
    function bdiv(uint mantissa1, int order1, uint mantissa2, int order2) public pure returns (uint mantissa, int order) {
        mantissa = mantissa1.fdiv(mantissa2);
        order = order1 - order2;
        (mantissa, order) = rewrite(mantissa, order);
    }
    
    function bpow(uint mantissa, int order, uint ind) public pure returns (uint mantissaOut, int orderOut) {
        if (ind == 0) return (1e18, 0);
        if (ind == 1) return (mantissa, order);
        
        (mantissaOut, orderOut) = (1e18, 0);
        
        for (uint i=ind ;i > 0;i >>= 1) {
            if (i & 1 == 1) {
                (mantissaOut, orderOut) = bmul(mantissaOut, orderOut, mantissa, order);
            }
            
            (mantissa, order) = bmul(mantissa, order, mantissa, order);
        }
     }
     
     
     function nthRootOverApprox(uint x, uint n) public pure returns (uint) {
         uint root = 1;
         uint exp = 255/n;
         for(uint st = (1 << exp); st >= 1 ;st >>= 1) {
             uint tmp = st ** n;
             if(x >= tmp) {
                 x /= tmp;
                 root *= (1 << exp);
             }
             exp --;
         }
         return root * 2;
     }
     
     // convert (x * 10^exp) to (mantissa * 10^order)
     function rewrite(uint x, int exp) internal pure returns (uint mantissa, int order) {
         mantissa = x;
         order = exp;
         while (mantissa < 1e18) {
            mantissa *= 10;
            order --;
        }
        while (mantissa >= 1e19) {
            mantissa /= 10;
            order ++;
        }
     }
    
  
    // n-th root of mantissa * 10^(order + BASE*(n - 1)) since 10^BASE is built-in
    function initGuess(uint mantissa, int order, uint n) public pure returns (uint mantissaOut, int orderOut) {
        // return (mantissa, (order+int(n)-1)/int(n));
        // (uint mantissaTmp, int orderTmp) = bmulConst(1e18, order, n-1);
        // (mantissaTmp, orderTmp) = badd(mantissaTmp, orderTmp, mantissa, order);
        // return bdivConst(mantissaTmp, orderTmp, n);
        
        
        int newOrder = order - 18;
        int quoOrder = newOrder / int(n);
        int rOrder = newOrder - quoOrder * int(n); // value less than n 

        if (rOrder < 0) {
            rOrder += int(n);
            quoOrder --;
        }
        
    
        require (rOrder <= 50);
        
        uint newMantissa = mantissa;
        if (rOrder > 0) {
            newMantissa = newMantissa * 10**uint(rOrder);
        } else if (rOrder < 0) {
            newMantissa = newMantissa / (10**uint(-rOrder));
        }
        
        mantissaOut = nthRootOverApprox(newMantissa, n);
        orderOut = quoOrder;
        
        (mantissaOut, orderOut) = rewrite(mantissaOut, orderOut);
        
        orderOut += 18; // times base 1e18
        
    }
    
    
    
    function lt(uint mantissa1, int order1, uint mantissa2, int order2) internal pure returns (bool) {
        if (order1 < order2) return true;
        if (order1 > order2) return false;
        if (mantissa1 < mantissa2) return true;
        return false;
    }
    
    // x = (mantissa, order)  
    // y = (mantissaOut, orderOut)
    // z = (mantissaTmp, orderTmp)
    function root(uint mantissa, int order, uint n) public pure returns (uint mantissaOut, int orderOut) {
        (uint mantissaTmp, int orderTmp) = initGuess(mantissa, order, n);
        (mantissaOut, orderOut) = (mantissa, order);
        while (lt(mantissaTmp, orderTmp, mantissaOut, orderOut)) {
            (mantissaOut, orderOut) = (mantissaTmp, orderTmp);
            (uint mPow, int oPow) = bpow(mantissaTmp, orderTmp, n-1);
            // return (mPow, oPow);
            (uint m1, int o1) = bdiv(mantissa, order, mPow, oPow);
            // return (m1, o1);
            (uint m2, int o2) = bmulConst(mantissaTmp, orderTmp, n-1);
            // return (m2, o2);
            (mantissaTmp, orderTmp) = badd(m1, o1, m2, o2);
            (mantissaTmp, orderTmp) = bdivConst(mantissaTmp, orderTmp, n);
            
        }
    }
    
    function computeTarget(uint balA, uint balB, uint n) public pure returns (uint mantissaOut, int orderOut) {
        (uint mTmp1, int oTmp1) = rewrite(balA, 0);
        (uint m1, int o1) = bpow(mTmp1, oTmp1, n);
        (uint m2, int o2) = rewrite(balB, 0);
        
        (mantissaOut, orderOut) = bmul(m1, o1, m2, o2);
    }
    
    // optA = nthRoot(K * pB * n / pA)
    function findOptimal(uint mK, int oK, uint pA, uint pB, uint n) public pure returns (uint mantissaOut, int orderOut) {
        (uint mTmp, int oTmp) = rewrite(pB, 0);
        (mTmp, oTmp) = bmul(mK, oK, mTmp, oTmp);

        (mTmp, oTmp) = bmulConst(mTmp, oTmp, n);

        (uint mTmp1, int oTmp1) = rewrite(pA, 0);
        (mTmp, oTmp) = bdiv(mTmp, oTmp, mTmp1, oTmp1);
        
        (mantissaOut, orderOut) = root(mTmp, oTmp, n+1);
        
    }
    
    function compute(uint balA, uint balB, uint pA, uint pB, uint n) public pure returns (uint, int, uint, int) {
        (uint mantissa, int order) = computeTarget(balA, balB, n);
        (uint mA, int oA) = findOptimal(mantissa, order, pA, pB, n);
        (uint mTmp, int oTmp) = bpow(mA, oA, n);
        (uint mB, int oB) = bdiv(mantissa, order, mTmp, oTmp);
        return (mA, oA, mB, oB);
    }

    function computeWithGas(uint balA, uint balB, uint pA, uint pB, uint n) public returns (uint, int, uint, int) {
        return compute(balA, balB, pA, pB, n);
    }
}
