from brownie import (SafeBoxETH, HomoraBank)
from brownie import accounts, interface, chain
from .utils import *


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def main():
    admin = accounts[0]
    alice = accounts[1]
    bob = accounts[2]

    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    cyweth = interface.IERC20Ex('0x41c84c0e2ee0b740cf0d31f63f3b6f627dc6b393')

    homora = HomoraBank.deploy({'from': admin})

    safebox = SafeBoxETH.deploy(cyweth, 'ibETHv2', 'ibETHv2', {'from': admin})

    # set up funds to alice
    mint_tokens(weth, alice)
    mint_tokens(weth, bob)

    weth.approve(cyweth, 2**256-1, {'from': bob})

    #################################################################
    # check decimals

    assert safebox.decimals() == cyweth.decimals(), 'incorrect decimals'

    #################################################################
    # deposit
    print('====================================')
    print('Case 1. deposit')

    prevETHAlice = alice.balance()
    prevWETHBob = weth.balanceOf(bob)
    prevIBETHAlice = safebox.balanceOf(alice)
    prevcyWETHBob = cyweth.balanceOf(bob)

    alice_amt = 10**18
    bob_amt = 10**18
    safebox.deposit({'from': alice, 'value': alice_amt})
    chain.mine(20)
    cyweth.mint(bob_amt, {'from': bob})

    curETHAlice = alice.balance()
    curWETHBob = weth.balanceOf(bob)
    curIBETHAlice = safebox.balanceOf(alice)
    curcyWETHBob = cyweth.balanceOf(bob)

    print('∆ eth alice', curETHAlice - prevETHAlice)
    print('∆ weth bob', curWETHBob - prevWETHBob)
    print('∆ ibETH bal alice', curIBETHAlice - prevIBETHAlice)
    print('∆ cyWETH bal bob', curcyWETHBob - prevcyWETHBob)
    print('calculated ibETH alice', alice_amt * 10**18 // cyweth.exchangeRateStored())
    print('calculated ibETH bob', bob_amt * 10**18 // cyweth.exchangeRateStored())

    assert curETHAlice - prevETHAlice == -alice_amt, 'incorrect alice amount'
    assert curWETHBob - prevWETHBob == -bob_amt, 'incorrect bob amount'
    assert almostEqual(curIBETHAlice - prevIBETHAlice, curcyWETHBob - prevcyWETHBob)

    chain.mine(200)

    #################################################################
    # alice withdraws 1/3 & 2/3. bob withdraws all.
    print('====================================')
    print('Case 2. withdraw')

    alice_withdraw_1 = safebox.balanceOf(alice) // 3
    alice_withdraw_2 = safebox.balanceOf(alice) - alice_withdraw_1
    bob_withdraw = cyweth.balanceOf(bob) // 3

    prevETHAlice = alice.balance()
    prevWETHBob = weth.balanceOf(bob)
    prevIBETHAlice = safebox.balanceOf(alice)
    prevcyWETHBob = cyweth.balanceOf(bob)

    safebox.withdraw(alice_withdraw_1, {'from': alice})
    chain.mine(20)
    cyweth.redeem(bob_withdraw, {'from': bob})

    curETHAlice = alice.balance()
    curWETHBob = weth.balanceOf(bob)
    curIBETHAlice = safebox.balanceOf(alice)
    curcyWETHBob = cyweth.balanceOf(bob)

    print('∆ eth alice', curETHAlice - prevETHAlice)
    print('∆ weth bob', curWETHBob - prevWETHBob)
    print('∆ ibETH bal alice', curIBETHAlice - prevIBETHAlice)
    print('∆ cyWETH bal bob', curcyWETHBob - prevcyWETHBob)

    assert almostEqual(curETHAlice - prevETHAlice, alice_amt //
                       3), 'incorrect alice withdraw eth amount'
    assert almostEqual(curWETHBob - prevWETHBob, bob_amt // 3), 'incorrect bob withdraw eth amount'
    assert almostEqual(curIBETHAlice - prevIBETHAlice, curcyWETHBob -
                       prevcyWETHBob), 'incorrect withdraw amount'

    chain.mine(20)

    prevETHAlice = alice.balance()
    prevIBETHAlice = safebox.balanceOf(alice)

    safebox.withdraw(alice_withdraw_2, {'from': alice})

    curETHAlice = alice.balance()
    curIBETHAlice = safebox.balanceOf(alice)

    print('∆ eth alice', curETHAlice - prevETHAlice)
    print('∆ ibETH bal alice', curIBETHAlice - prevIBETHAlice)

    assert almostEqual(curETHAlice - prevETHAlice, alice_amt * 2 //
                       3), 'incorrect second withdraw'
