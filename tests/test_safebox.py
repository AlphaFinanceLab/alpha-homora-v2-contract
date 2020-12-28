import pytest
import brownie
from brownie import interface


def test_governor(admin, safebox):
    assert safebox.governor() == admin


def test_pending_governor(safebox):
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_set_governor(admin, alice, safebox):
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # set pending governor to alice
    safebox.setPendingGovernor(alice, {'from': admin})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == alice
    # accept governor
    safebox.acceptGovernor({'from': alice})
    assert safebox.governor() == alice
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_not_governor(admin, alice, bob, eve, safebox):
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # not governor tries to set governor
    with brownie.reverts('not the governor'):
        safebox.setPendingGovernor(bob, {'from': alice})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # admin sets self
    safebox.setPendingGovernor(admin, {'from': admin})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == admin
    # accept self
    safebox.acceptGovernor({'from': admin})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # governor sets another
    safebox.setPendingGovernor(alice, {'from': admin})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == alice
    # alice tries to set without accepting
    with brownie.reverts('not the governor'):
        safebox.setPendingGovernor(admin, {'from': alice})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == alice
    # eve tries to accept
    with brownie.reverts('not the pending governor'):
        safebox.acceptGovernor({'from': eve})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == alice
    # alice accepts governor
    safebox.acceptGovernor({'from': alice})
    assert safebox.governor() == alice
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_governor_set_twice(admin, alice, eve, safebox):
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'
    # mistakenly set eve to governor
    safebox.setPendingGovernor(eve, {'from': admin})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == eve
    # set another governor before eve can accept
    safebox.setPendingGovernor(alice, {'from': admin})
    assert safebox.governor() == admin
    assert safebox.pendingGovernor() == alice
    # eve can no longer accept governor
    with brownie.reverts('not the pending governor'):
        safebox.acceptGovernor({'from': eve})
    # alice accepts governor
    safebox.acceptGovernor({'from': alice})
    assert safebox.governor() == alice
    assert safebox.pendingGovernor() == '0x0000000000000000000000000000000000000000'


def test_relayer(admin, safebox):
    assert safebox.relayer() == admin


def test_set_relayer(admin, alice, safebox):
    # set relayer to alice
    safebox.setRelayer(alice, {'from': admin})
    assert safebox.relayer() == alice


def test_relayer_2(admin, alice, bob, eve, safebox):
    # not governor tries to set governor
    with brownie.reverts('not the governor'):
        safebox.setRelayer(bob, {'from': eve})
    assert safebox.relayer() == admin
    # governor sets relayer
    safebox.setRelayer(alice, {'from': admin})
    assert safebox.relayer() == alice
    # governor sets relayer
    safebox.setRelayer(bob, {'from': admin})
    assert safebox.relayer() == bob


def test_update_root(admin, alice, eve, safebox):
    safebox.setRelayer(alice, {'from': admin})
    assert safebox.root() == '0x0000000000000000000000000000000000000000'
    # update from governor
    safebox.updateRoot('0x0000000000000000000000000000000000000001', {'from': admin})
    assert safebox.root() == '0x0000000000000000000000000000000000000001'
    # update from relayer
    safebox.updateRoot('0x0000000000000000000000000000000000000002', {'from': alice})
    assert safebox.root() == '0x0000000000000000000000000000000000000002'
    # update from non-authorized party
    with brownie.reverts('!relayer'):
        safebox.updateRoot('0x0000000000000000000000000000000000000003', {'from': eve})


def test_deposit_withdraw(admin, alice, token, cToken, safebox):
    alice_mint_amt = 1000 * 10**18
    token.mint(alice, alice_mint_amt, {'from': admin})
    token.approve(safebox, 2**256-1, {'from': alice})

    alice_deposit_amt = 10 * 10**18
    safebox.deposit(alice_deposit_amt, {'from': alice})
    assert token.balanceOf(alice) == alice_mint_amt - alice_deposit_amt
    assert cToken.balanceOf(safebox) == alice_deposit_amt

    print(safebox.balanceOf(alice))

    alice_withdraw_amt = 2 * 10**18
    safebox.withdraw(alice_withdraw_amt, {'from': alice})
    assert token.balanceOf(alice) == alice_mint_amt - alice_deposit_amt + alice_withdraw_amt
    assert cToken.balanceOf(safebox) == alice_deposit_amt - alice_withdraw_amt

    cToken.setMintRate(11 * 10**17)
    assert cToken.mintRate() == 11 * 10**17

    alice_rewithdraw_amt = 3 * 10**18
    safebox.withdraw(alice_rewithdraw_amt, {'from': alice})
    assert token.balanceOf(alice) == alice_mint_amt - alice_deposit_amt + \
        alice_withdraw_amt + alice_rewithdraw_amt * 10 // 11
    assert cToken.balanceOf(safebox) == alice_deposit_amt - \
        alice_withdraw_amt - alice_rewithdraw_amt


def test_admin_claim(admin, eve, token, safebox):
    mint_amt = 100 * 10**18
    token.mint(safebox, mint_amt, {'from': admin})
    admin_claim_amt = 5 * 10**18
    safebox.adminClaim(admin_claim_amt, {'from': admin})
    assert token.balanceOf(safebox) == mint_amt - admin_claim_amt
    assert token.balanceOf(admin) == admin_claim_amt

    with brownie.reverts('not the governor'):
        safebox.adminClaim(admin_claim_amt, {'from': eve})


def test_claim(admin, token, safebox):
    token.mint(safebox, 1000 * 10**18, {'from': admin})
    user = '0x875B3a3374c63527271281a9254ad8926F021f1A'
    user2 = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

    safebox.updateRoot('0xaee410ac1087d10cadac9200aea45b43b7f48a5c75ba30988eeddf29db4303ad')
    safebox.claim(9231, ['0x69f3f45eba22069136bcf167cf8d409b0fc92841af8112ad94696c72c4fd281d',
                         '0xd841f03d02a38c6b5c9f2042bc8877162e45b1d9de0fdd5711fa735827760f9b',
                         '0xd279da13820e67ddd2615d2412ffef5470abeb32ba6a387005036fdd0b5ff889'], {'from': user})

    assert token.balanceOf(user) == 9231

    safebox.updateRoot('0xd427ac6fd81417c7e5cefed0b0157d30f4622586a2af6a6a9fb12b3a47a7d6cb')
    safebox.claim(9331, ['0x691395a552526657ee71eda339d1bafc72ead15d560ef4f11149c25846708c0e',
                         '0xf024a94a201d1b2733b930f6cecc765f38a628fc7add2649b0da1ce64d4bf037',
                         '0xe40972281644958cba0c8a0b1e06f4d3531a35ae03fbbf2c355d1fc9a3ab9f00'], {'from': user})

    assert token.balanceOf(user) == 9331

    safebox.claim(
        223, ['0x8e1314f881555f59ae04ddfe30e82dfcfa9d3e2422974564f365308083135cec'], {'from': user2})
    assert token.balanceOf(user2) == 223


def test_claim_and_withdraw(admin, token, cToken, safebox):
    token.mint(safebox, 1000 * 10**18, {'from': admin})
    user = '0x875B3a3374c63527271281a9254ad8926F021f1A'

    user_mint_amt = 1000 * 10**18
    token.mint(user, user_mint_amt, {'from': admin})
    token.approve(safebox, 2**256-1, {'from': user})

    user_deposit_amt = 10 * 10**18
    safebox.deposit(user_deposit_amt, {'from': user})
    assert token.balanceOf(user) == user_mint_amt - user_deposit_amt
    assert cToken.balanceOf(safebox) == user_deposit_amt

    safebox.updateRoot('0xaee410ac1087d10cadac9200aea45b43b7f48a5c75ba30988eeddf29db4303ad')
    safebox.claimAndWithdraw(9231, ['0x69f3f45eba22069136bcf167cf8d409b0fc92841af8112ad94696c72c4fd281d',
                                    '0xd841f03d02a38c6b5c9f2042bc8877162e45b1d9de0fdd5711fa735827760f9b',
                                    '0xd279da13820e67ddd2615d2412ffef5470abeb32ba6a387005036fdd0b5ff889'], user_deposit_amt, {'from': user})

    assert token.balanceOf(user) == user_mint_amt + 9231
