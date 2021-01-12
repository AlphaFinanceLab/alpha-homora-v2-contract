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

    safebox = SafeBoxETH.deploy(cyweth, 'Yearn Wrapped Ether', 'cyWETH', {'from': admin})

    # set up funds to alice
    mint_tokens(weth, alice)
    mint_tokens(weth, bob)

    #################################################################
    # deposit
    print('====================================')
    print('Case 1. deposit')

    prevETHAlice = alice.balance()
    prevETHBob = bob.balance()
    prevIBETHAlice = safebox.balanceOf(alice)
    prevIBETHBob = safebox.balanceOf(bob)

    alice_amt = 10**18
    bob_amt = 10**18
    safebox.deposit({'from': alice, 'value': alice_amt})
    chain.mine(20)
    safebox.deposit({'from': bob, 'value': bob_amt})

    curETHAlice = alice.balance()
    curETHBob = bob.balance()
    curIBETHAlice = safebox.balanceOf(alice)
    curIBETHBob = safebox.balanceOf(bob)

    print('∆ eth alice', curETHAlice - prevETHAlice)
    print('∆ eth bob', curETHBob - prevETHBob)
    print('∆ ibETH bal alice', curIBETHAlice - prevIBETHAlice)
    print('∆ ibETH bal bob', curIBETHBob - prevIBETHBob)
    print('calculated ibETH alice', alice_amt * 10**18 // cyweth.exchangeRateStored())
    print('calculated ibETH bob', bob_amt * 10**18 // cyweth.exchangeRateStored())

    assert curETHAlice - prevETHAlice == -alice_amt, 'incorrect alice amount'
    assert curETHBob - prevETHBob == -bob_amt, 'incorrect bob amount'
    assert almostEqual(curIBETHAlice - prevIBETHAlice,
                       alice_amt * 10**18 // cyweth.exchangeRateStored())
    assert almostEqual(curIBETHBob - prevIBETHBob,
                       bob_amt * 10**18 // cyweth.exchangeRateStored())

    chain.mine(200)

    #################################################################
    # alice withdraws 1/3 & 2/3. bob withdraws all.
    print('====================================')
    print('Case 2. withdraw')

    alice_withdraw_1 = safebox.balanceOf(alice) // 3
    alice_withdraw_2 = safebox.balanceOf(alice) - alice_withdraw_1
    bob_withdraw = safebox.balanceOf(bob)

    prevETHAlice = alice.balance()
    prevETHBob = bob.balance()
    prevIBETHAlice = safebox.balanceOf(alice)
    prevIBETHBob = safebox.balanceOf(bob)

    safebox.withdraw(alice_withdraw_1, {'from': alice})
    chain.mine(20)
    safebox.withdraw(bob_withdraw, {'from': bob})

    curETHAlice = alice.balance()
    curETHBob = bob.balance()
    curIBETHAlice = safebox.balanceOf(alice)
    curIBETHBob = safebox.balanceOf(bob)

    print('∆ eth alice', curETHAlice - prevETHAlice)
    print('∆ eth bob', curETHBob - prevETHBob)
    print('∆ ibETH bal alice', curIBETHAlice - prevIBETHAlice)
    print('∆ ibETH bal bob', curIBETHBob - prevIBETHBob)

    assert almostEqual(curETHAlice - prevETHAlice, alice_amt //
                       3), 'incorrect alice withdraw eth amount'
    assert almostEqual(curETHBob - prevETHBob, bob_amt), 'incorrect bob withdraw eth amount'
    assert curIBETHAlice - prevIBETHAlice == -alice_withdraw_1, 'incorrect alice ∆ibETH'
    assert curIBETHBob - prevIBETHBob == -bob_withdraw, 'incorrect bob ∆ibETH'

    chain.mine(20)

    prevETHAlice = alice.balance()
    prevIBETHAlice = safebox.balanceOf(alice)

    safebox.withdraw(alice_withdraw_2, {'from': alice})

    curETHAlice = alice.balance()
    curIBETHAlice = safebox.balanceOf(alice)

    print('∆ eth alice', curETHAlice - prevETHAlice)
    print('∆ eth bob', curETHBob - prevETHBob)
    print('∆ ibETH bal alice', curIBETHAlice - prevIBETHAlice)
    print('∆ ibETH bal bob', curIBETHBob - prevIBETHBob)

    assert almostEqual(curETHAlice - prevETHAlice, alice_amt * 2 //
                       3), 'incorrect alice second withdraw eth amount'
    assert curIBETHAlice - prevIBETHAlice == -alice_withdraw_2, 'incorrect alice second ∆ibETH '
