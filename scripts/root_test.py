from brownie import accounts, interface, Contract
from brownie import (
    FMath, Root 
)

def almostEqual(a, b):
    return a <= b + abs(b) // 10 and a >= b - abs(b) // 10

def test(balA, balB, pA, pB, n):
    m, o = root.computeTarget(balA, balB, n)
    print('product mantissa, order:', m, o)
    assert almostEqual((balA**n)* balB, m * 10**o * 10**(18*n))

    m1, o1 = root.findOptimal(m, o, pA, pB, n)
    print('optimal:', m1, o1)

    mA, oA, mB, oB = root.compute(balA, balB, pA, pB, n)
    print('optimal bal A:', mA, oA)
    print('optimal bal B:', mB, oB)

    tx = root.computeWithGas(balA, balB, pA, pB, n)
    print('optimal bal A:', tx.return_value)
    print('gas used:', tx.gas_used)

def wbtc_weth():
    #  1 : 1
    balA = 3200000000000000000000
    balB = 104300000000000000000000
    pA = 19155740000000000000000
    pB = 605000000000000000000
    n = 1 # 1 : 1
    test(balA, balB, pA, pB, n) 

    balA = 3200000000000000000000000000
    balB = 104300000000000000000000000000
    pA = 19155740000000000000000
    pB = 605000000000000000000
    n = 1 # 1 : 1
    test(balA, balB, pA, pB, n) 

def bal_weth():
    # 2 : 1
    balA = 455900000000000000000000
    balB = 5200000000000000000000
    pA = 13640000000000000000
    pB = 588000000000000000000
    n = 2
    test(balA, balB, pA, pB, n)

def bal_usdc():
    # NOTE: assume USDC is 18 decimals
    # 2 : 1 
    balA = 2100000000000000000000
    balB = 14300000000000000000000
    pA = 13640000000000000000
    pB = 1000000000000000000
    n = 2
    test(balA, balB, pA, pB, n) 

def mkr_weth():
    # 3 : 1
    balA = 1800000000000000000000
    balB = 527504000000000000000
    pA = 527000000000000000000
    pB = 588000000000000000000
    n = 3
    test(balA, balB, pA, pB, n) 

    # 4 : 1
    balA = 15848960000000000000000
    balB = 3469620000000000000000
    pA = 516370000000000000000
    pB = 595150000000000000000
    n = 4
    test(balA, balB, pA, pB, n) 

def stake_weth():
    # 9 : 1
    balA = 283000000000000000000000
    balB = 758753000000000000000
    pA = 13950000000000000000
    pB = 595150000000000000000
    n = 9
    test(balA, balB, pA, pB, n)  

def mana_dg():
    # 49 : 1
    balA = 13800000000000000000000000
    balB = 1700000000000000000000
    pA = 88433000000000000
    pB = 15650000000000000000
    n = 49
    test(balA, balB, pA, pB, n)  

def htre_usdc():
    # 49 : 1
    balA = 4200000000000000000000000
    balB = 4600000000000000000000
    pA = 53383000000000000
    pB = 1000000000000000000
    n = 49
    test(balA, balB, pA, pB, n)  

def main():
    admin = accounts[0]
    alice = accounts[1]

    global fmath
    global root

    fmath = FMath.deploy({'from' : admin})
    root = Root.deploy({'from' : admin})

    wbtc_weth()
    # bal_weth()
    # bal_usdc()
    # mkr_weth()
    # stake_weth()
    # mana_dg()
    # htre_usdc()
    