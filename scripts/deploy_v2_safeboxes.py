from brownie import (
    accounts, ERC20KP3ROracle, UniswapV2Oracle, BalancerPairOracle, ProxyOracle, CoreOracle,
    HomoraBank, CurveOracle, UniswapV2SpellV1, WERC20, WLiquidityGauge, WMasterChef,
    WStakingRewards, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1, SafeBoxETH, SafeBox
)
from brownie import interface, accounts
from .utils import *


KP3R_NETWORK = '0x73353801921417F465377c8d898c6f4C0270282C'
CRV_REGISTRY = '0x7D86446dDb609eD0F5f8684AcF30380a356b2B4c'
CRV_TOKEN = '0xD533a949740bb3306d119CC777fa900bA034cd52'
MASTERCHEF = '0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd'
BANK = '0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb'


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def test_safebox_eth(safebox):
    alice = accounts[1]

    deposit_amt = 100000 * 10**18

    prevETHBal = alice.balance()
    safebox.deposit({'from': alice, 'value': deposit_amt})
    curETHBal = alice.balance()

    assert almostEqual(curETHBal - prevETHBal, -deposit_amt), 'incorrect deposit amount'

    withdraw_amt = safebox.balanceOf(alice) // 3

    prevETHBal = alice.balance()
    safebox.withdraw(withdraw_amt, {'from': alice})
    curETHBal = alice.balance()

    assert almostEqual(curETHBal - prevETHBal, deposit_amt // 3), 'incorrect first withdraw amount'

    withdraw_amt = safebox.balanceOf(alice)

    prevETHBal = alice.balance()
    safebox.withdraw(withdraw_amt, {'from': alice})
    curETHBal = alice.balance()

    assert almostEqual(curETHBal - prevETHBal, deposit_amt - deposit_amt //
                       3), 'incorrect second withdraw amount'


def test_safebox(token, safebox):
    alice = accounts[1]

    mint_tokens(token, alice)

    token.approve(safebox, 2**256-1, {'from': alice})

    deposit_amt = 100 * 10**token.decimals()

    prevBal = token.balanceOf(alice)
    safebox.deposit(deposit_amt, {'from': alice})
    curBal = token.balanceOf(alice)

    assert almostEqual(curBal - prevBal, -deposit_amt), 'incorrect deposit amount'

    withdraw_amt = safebox.balanceOf(alice) // 3

    prevBal = token.balanceOf(alice)
    safebox.withdraw(withdraw_amt, {'from': alice})
    curBal = token.balanceOf(alice)

    assert almostEqual(curBal - prevBal, deposit_amt // 3), 'incorrect first withdraw amount'

    withdraw_amt = safebox.balanceOf(alice)

    prevBal = token.balanceOf(alice)
    safebox.withdraw(withdraw_amt, {'from': alice})
    curBal = token.balanceOf(alice)

    assert almostEqual(curBal - prevBal, deposit_amt - deposit_amt //
                       3), 'incorrect second withdraw amount'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    # deploy safeboxes
    safebox_eth = SafeBoxETH.deploy(
        '0x41c84c0e2ee0b740cf0d31f63f3b6f627dc6b393', 'Yearn Wrapped Ether', 'cyWETH', {'from': deployer})
    safebox_dai = SafeBox.deploy(
        '0x8e595470Ed749b85C6F7669de83EAe304C2ec68F', 'Yearn Dai Stablecoin', 'cyDAI', {'from': deployer})
    safebox_usdt = SafeBox.deploy(
        '0x48759F220ED983dB51fA7A8C0D2AAb8f3ce4166a', 'Yearn Tether USD', 'cyUSDT', {'from': deployer})
    safebox_usdc = SafeBox.deploy(
        '0x76Eb2FE28b36B3ee97F3Adae0C69606eeDB2A37c', 'Yearn USD Coin', 'cyUSDC', {'from': deployer})
    safebox_yfi = SafeBox.deploy(
        '0xfa3472f7319477c9bfecdd66e4b948569e7621b9', 'Yearn YFI', 'cyYFI', {'from': deployer})

    ###########################################################
    # test

    # dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    # usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    # usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
    # yfi = interface.IERC20Ex('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e')

    # test_safebox_eth(safebox_eth)
    # test_safebox(dai, safebox_dai)
    # test_safebox(usdt, safebox_usdt)
    # test_safebox(usdc, safebox_usdc)
    # test_safebox(yfi, safebox_yfi)
