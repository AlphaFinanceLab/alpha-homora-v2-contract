from brownie import (SafeBox, HomoraBank)
from brownie import accounts, interface, chain
from .utils import *


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def main():
    admin = accounts[0]
    alice = accounts[1]
    bob = accounts[2]

    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    cydai = interface.IERC20Ex('0x8e595470ed749b85c6f7669de83eae304c2ec68f')

    homora = HomoraBank.deploy({'from': admin})

    safebox = SafeBox.deploy(cydai, 'ibDAIv2', 'ibDAIv2', {'from': admin})

    # set up funds to alice
    mint_tokens(dai, alice)
    mint_tokens(dai, bob)

    # approve dai
    dai.approve(safebox, 2**256-1, {'from': alice})
    dai.approve(cydai, 2**256-1, {'from': bob})

    #################################################################
    # check decimals

    assert safebox.decimals() == cydai.decimals(), 'incorrect decimals'

    #################################################################
    # deposit
    print('====================================')
    print('Case 1. deposit')

    prevDAIAlice = dai.balanceOf(alice)
    prevDAIBob = dai.balanceOf(bob)
    prevIBDAIAlice = safebox.balanceOf(alice)
    prevcyDAIBob = cydai.balanceOf(bob)

    alice_amt = 10**18
    bob_amt = 10**18
    safebox.deposit(alice_amt, {'from': alice})
    chain.mine(20)
    cydai.mint(bob_amt, {'from': bob})

    curDAIAlice = dai.balanceOf(alice)
    curDAIBob = dai.balanceOf(bob)
    curIBDAIAlice = safebox.balanceOf(alice)
    curcyDAIBob = cydai.balanceOf(bob)

    print('∆ dai alice', curDAIAlice - prevDAIAlice)
    print('∆ dai bob', curDAIBob - prevDAIBob)
    print('∆ ibDAI bal alice', curIBDAIAlice - prevIBDAIAlice)
    print('∆ cyDAI bal bob', curcyDAIBob - prevcyDAIBob)
    print('calculated ibDAI alice', alice_amt * 10**18 // cydai.exchangeRateStored())

    assert curDAIAlice - prevDAIAlice == -alice_amt, 'incorrect alice amount'
    assert curDAIBob - prevDAIBob == -bob_amt, 'incorrect bob amount'
    assert almostEqual(curIBDAIAlice - prevIBDAIAlice,
                       curcyDAIBob - prevcyDAIBob)

    chain.mine(200)

    #################################################################
    # alice withdraws 1/3 & 2/3. bob withdraws all.
    print('====================================')
    print('Case 2. withdraw')

    alice_withdraw_1 = safebox.balanceOf(alice) // 3
    alice_withdraw_2 = safebox.balanceOf(alice) - alice_withdraw_1
    bob_withdraw = cydai.balanceOf(bob) // 3

    prevDAIAlice = dai.balanceOf(alice)
    prevDAIBob = dai.balanceOf(bob)
    prevIBDAIAlice = safebox.balanceOf(alice)
    prevcyDAIBob = cydai.balanceOf(bob)

    safebox.withdraw(alice_withdraw_1, {'from': alice})
    chain.mine(20)
    cydai.redeem(bob_withdraw, {'from': bob})

    curDAIAlice = dai.balanceOf(alice)
    curDAIBob = dai.balanceOf(bob)
    curIBDAIAlice = safebox.balanceOf(alice)
    curcyDAIBob = cydai.balanceOf(bob)

    print('∆ dai alice', curDAIAlice - prevDAIAlice)
    print('∆ dai bob', curDAIBob - prevDAIBob)
    print('∆ ibDAI bal alice', curIBDAIAlice - prevIBDAIAlice)
    print('∆ cyDAI bal bob', curcyDAIBob - prevcyDAIBob)

    assert almostEqual(curDAIAlice - prevDAIAlice, alice_amt //
                       3), 'incorrect alice withdraw dai amount'
    assert almostEqual(curDAIBob - prevDAIBob, bob_amt // 3), 'incorrect bob withdraw dai amount'
    assert almostEqual(curIBDAIAlice - prevIBDAIAlice, curcyDAIBob -
                       prevcyDAIBob), 'incorrect withdraw amount'

    chain.mine(20)

    prevDAIAlice = dai.balanceOf(alice)
    prevIBDAIAlice = safebox.balanceOf(alice)

    safebox.withdraw(alice_withdraw_2, {'from': alice})

    curDAIAlice = dai.balanceOf(alice)
    curIBDAIAlice = safebox.balanceOf(alice)

    print('∆ dai alice', curDAIAlice - prevDAIAlice)
    print('∆ dai bob', curDAIBob - prevDAIBob)
    print('∆ ibDAI bal alice', curIBDAIAlice - prevIBDAIAlice)
    print('∆ ibDAI bal bob', curcyDAIBob - prevcyDAIBob)

    assert almostEqual(curDAIAlice - prevDAIAlice, alice_amt * 2 //
                       3), 'incorrect alice second withdraw dai amount'
