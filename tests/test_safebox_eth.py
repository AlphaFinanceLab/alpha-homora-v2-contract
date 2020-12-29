import pytest
import brownie
from brownie import interface
from utils import *


def test_governor(admin, safebox_eth):
    assert safebox_eth.governor() == admin


def test_pending_governor(safebox_eth):
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_set_governor(admin, alice, safebox_eth):
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # set pending governor to alice
    safebox_eth.setPendingGovernor(alice, {'from': admin})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == alice
    # accept governor
    safebox_eth.acceptGovernor({'from': alice})
    assert safebox_eth.governor() == alice
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_not_governor(admin, alice, bob, eve, safebox_eth):
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # not governor tries to set governor
    with brownie.reverts('not the governor'):
        safebox_eth.setPendingGovernor(bob, {'from': alice})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # admin sets self
    safebox_eth.setPendingGovernor(admin, {'from': admin})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == admin
    # accept self
    safebox_eth.acceptGovernor({'from': admin})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # governor sets another
    safebox_eth.setPendingGovernor(alice, {'from': admin})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == alice
    # alice tries to set without accepting
    with brownie.reverts('not the governor'):
        safebox_eth.setPendingGovernor(admin, {'from': alice})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == alice
    # eve tries to accept
    with brownie.reverts('not the pending governor'):
        safebox_eth.acceptGovernor({'from': eve})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == alice
    # alice accepts governor
    safebox_eth.acceptGovernor({'from': alice})
    assert safebox_eth.governor() == alice
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_governor_set_twice(admin, alice, eve, safebox_eth):
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # mistakenly set eve to governor
    safebox_eth.setPendingGovernor(eve, {'from': admin})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == eve
    # set another governor before eve can accept
    safebox_eth.setPendingGovernor(alice, {'from': admin})
    assert safebox_eth.governor() == admin
    assert safebox_eth.pendingGovernor() == alice
    # eve can no longer accept governor
    with brownie.reverts('not the pending governor'):
        safebox_eth.acceptGovernor({'from': eve})
    # alice accepts governor
    safebox_eth.acceptGovernor({'from': alice})
    assert safebox_eth.governor() == alice
    assert safebox_eth.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_relayer(admin, safebox_eth):
    assert safebox_eth.relayer() == admin


def test_set_relayer(admin, alice, safebox_eth):
    # set relayer to alice
    safebox_eth.setRelayer(alice, {'from': admin})
    assert safebox_eth.relayer() == alice


def test_relayer_2(admin, alice, bob, eve, safebox_eth):
    # not governor tries to set governor
    with brownie.reverts('not the governor'):
        safebox_eth.setRelayer(bob, {'from': eve})
    assert safebox_eth.relayer() == admin
    # governor sets relayer
    safebox_eth.setRelayer(alice, {'from': admin})
    assert safebox_eth.relayer() == alice
    # governor sets relayer
    safebox_eth.setRelayer(bob, {'from': admin})
    assert safebox_eth.relayer() == bob


def test_update_root(admin, alice, eve, safebox_eth):
    safebox_eth.setRelayer(alice, {'from': admin})
    assert safebox_eth.root() == '0x0000000000000000000000000000000000000000'
    # update from governor
    safebox_eth.updateRoot('0x0000000000000000000000000000000000000001', {'from': admin})
    assert safebox_eth.root() == '0x0000000000000000000000000000000000000001'
    # update from relayer
    safebox_eth.updateRoot('0x0000000000000000000000000000000000000002', {'from': alice})
    assert safebox_eth.root() == '0x0000000000000000000000000000000000000002'
    # update from non-authorized party
    with brownie.reverts('!relayer'):
        safebox_eth.updateRoot('0x0000000000000000000000000000000000000003', {'from': eve})


def test_deposit_withdraw(admin, alice, weth, cweth, safebox_eth):
    alice_deposit_amt = 10 * 10**18
    prevAliceBalance = alice.balance()
    safebox_eth.deposit({'from': alice, 'value': alice_deposit_amt})
    assert almostEqual(alice.balance() - prevAliceBalance, -alice_deposit_amt)
    assert cweth.balanceOf(safebox_eth) == alice_deposit_amt

    print(safebox_eth.balanceOf(alice))

    alice_withdraw_amt = 2 * 10**18
    prevAliceBalance = alice.balance()
    safebox_eth.withdraw(alice_withdraw_amt, {'from': alice})
    assert almostEqual(alice.balance() - prevAliceBalance, alice_withdraw_amt)
    assert cweth.balanceOf(safebox_eth) == alice_deposit_amt - alice_withdraw_amt

    cweth.setMintRate(11 * 10**17)
    assert cweth.mintRate() == 11 * 10**17

    alice_rewithdraw_amt = 3 * 10**18
    prevAliceBalance = alice.balance()
    safebox_eth.withdraw(alice_rewithdraw_amt, {'from': alice})
    assert almostEqual(alice.balance() - prevAliceBalance, alice_rewithdraw_amt * 10 // 11)
    assert cweth.balanceOf(safebox_eth) == alice_deposit_amt - \
        alice_withdraw_amt - alice_rewithdraw_amt


def test_admin_claim(admin, alice, eve, weth, safebox_eth):
    mint_amt = 20 * 10**18
    weth.deposit({'from': alice, 'value': mint_amt})
    weth.transfer(safebox_eth, mint_amt, {'from': alice})
    admin_claim_amt = 7 * 10**18
    prevAdminBalance = admin.balance()
    safebox_eth.adminClaim(admin_claim_amt, {'from': admin})
    assert weth.balanceOf(safebox_eth) == mint_amt - admin_claim_amt
    assert admin.balance() - prevAdminBalance == admin_claim_amt

    with brownie.reverts('not the governor'):
        safebox_eth.adminClaim(admin_claim_amt, {'from': eve})


def test_claim(a, admin, weth, safebox_eth):
    weth.deposit({'from': admin, 'value': 1000 * 10**18})
    weth.transfer(safebox_eth, 1000 * 10**18, {'from': admin})

    user = '0x875B3a3374c63527271281a9254ad8926F021f1A'
    user2 = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

    prevUserBalance = a.at(user, force=True).balance()
    safebox_eth.updateRoot('0xaee410ac1087d10cadac9200aea45b43b7f48a5c75ba30988eeddf29db4303ad')
    safebox_eth.claim(9231, ['0x69f3f45eba22069136bcf167cf8d409b0fc92841af8112ad94696c72c4fd281d',
                             '0xd841f03d02a38c6b5c9f2042bc8877162e45b1d9de0fdd5711fa735827760f9b',
                             '0xd279da13820e67ddd2615d2412ffef5470abeb32ba6a387005036fdd0b5ff889'], {'from': user})

    assert a.at(user, force=True).balance() - prevUserBalance == 9231

    prevUserBalance = a.at(user, force=True).balance()
    safebox_eth.updateRoot('0xd427ac6fd81417c7e5cefed0b0157d30f4622586a2af6a6a9fb12b3a47a7d6cb')
    safebox_eth.claim(9331, ['0x691395a552526657ee71eda339d1bafc72ead15d560ef4f11149c25846708c0e',
                             '0xf024a94a201d1b2733b930f6cecc765f38a628fc7add2649b0da1ce64d4bf037',
                             '0xe40972281644958cba0c8a0b1e06f4d3531a35ae03fbbf2c355d1fc9a3ab9f00'], {'from': user})

    assert a.at(user, force=True).balance() - prevUserBalance == 100

    prevUser2Balance = a.at(user2, force=True).balance()
    safebox_eth.claim(
        223, ['0x8e1314f881555f59ae04ddfe30e82dfcfa9d3e2422974564f365308083135cec'], {'from': user2})
    assert a.at(user2, force=True).balance() - prevUser2Balance == 223


def test_claim_and_withdraw(a, admin, weth, cweth, safebox_eth):
    weth.deposit({'from': admin, 'value': 100 * 10**18})
    weth.transfer(safebox_eth, 100 * 10**18, {'from': admin})

    user = '0x875B3a3374c63527271281a9254ad8926F021f1A'

    user_deposit_amt = 10 * 10**18
    admin.transfer(user, user_deposit_amt)
    safebox_eth.deposit({'from': user, 'value': user_deposit_amt})
    assert cweth.balanceOf(safebox_eth) == user_deposit_amt

    prevUserBalance = a.at(user, force=True).balance()
    safebox_eth.updateRoot('0xaee410ac1087d10cadac9200aea45b43b7f48a5c75ba30988eeddf29db4303ad')
    safebox_eth.claimAndWithdraw(9231, ['0x69f3f45eba22069136bcf167cf8d409b0fc92841af8112ad94696c72c4fd281d',
                                        '0xd841f03d02a38c6b5c9f2042bc8877162e45b1d9de0fdd5711fa735827760f9b',
                                        '0xd279da13820e67ddd2615d2412ffef5470abeb32ba6a387005036fdd0b5ff889'], user_deposit_amt, {'from': user})

    assert a.at(user, force=True).balance() - prevUserBalance == user_deposit_amt + 9231


def test_receive_eth(admin, eve, weth, safebox_eth):
    with brownie.reverts('!weth'):
        eve.transfer(safebox_eth, 10)
