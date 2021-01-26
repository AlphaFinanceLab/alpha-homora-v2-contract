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


def test_bank(token, bank):
    alice = accounts[1]

    uniswap_spell = UniswapV2SpellV1.at('0xc671B7251a789de0835a2fa33c83c8D4afB39092')

    mint_tokens(token, alice)

    token.approve(bank, 2**256-1, {'from': alice})

    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    amt = 10000 * 10**token.decimals()

    borrow_amt = 10 * 10**token.decimals()

    prevTokenAlice = token.balanceOf(alice)

    bank.execute(0, uniswap_spell, uniswap_spell.addLiquidityWERC20.encode_input(
        token, weth, [amt, 0, 0, borrow_amt, 10**18, 0, 0, 0]), {'from': alice})

    curTokenAlice = token.balanceOf(alice)

    assert almostEqual(curTokenAlice - prevTokenAlice, -amt), 'incorrect input amt'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    # deploy safeboxes
    safebox_eth = SafeBoxETH.deploy(
        '0x41c84c0e2EE0b740Cf0d31F63f3B6F627DC6b393', 'Interest Bearing Ether v2', 'ibETHv2', {'from': deployer})
    safebox_dai = SafeBox.deploy(
        '0x8e595470Ed749b85C6F7669de83EAe304C2ec68F', 'Interest Bearing Dai Stablecoin v2', 'ibDAIv2', {'from': deployer})
    safebox_usdt = SafeBox.deploy(
        '0x48759F220ED983dB51fA7A8C0D2AAb8f3ce4166a', 'Interest Bearing Tether USD v2', 'ibUSDTv2', {'from': deployer})
    safebox_usdc = SafeBox.deploy(
        '0x76Eb2FE28b36B3ee97F3Adae0C69606eeDB2A37c', 'Interest Bearing USD Coin v2', 'ibUSDCv2', {'from': deployer})
    safebox_yfi = SafeBox.deploy(
        '0xFa3472f7319477c9bFEcdD66E4B948569E7621b9', 'Interest Bearing yearn.finance v2', 'ibYFIv2', {'from': deployer})

    # add banks
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    usdc = interface.IERC20Ex('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
    yfi = interface.IERC20Ex('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e')

    cyusdt = '0x48759F220ED983dB51fA7A8C0D2AAb8f3ce4166a'
    cyusdc = '0x76Eb2FE28b36B3ee97F3Adae0C69606eeDB2A37c'
    cyyfi = '0xFa3472f7319477c9bFEcdD66E4B948569E7621b9'

    bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    bank.addBank(usdt, cyusdt, {'from': deployer})
    bank.addBank(usdc, cyusdc, {'from': deployer})

    ###########################################################
    # test cyToken

    # for token in [cyusdt, cyusdc, cyyfi]:
    #     assert interface.IERC20Ex(token).symbol() == 'cy' + \
    #         interface.IERC20Ex(interface.IERC20Ex(token).underlying()).symbol()

    ###########################################################
    # test safeboxes

    # dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    # usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    # usdc = interface.IERC20Ex('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
    # yfi = interface.IERC20Ex('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e')

    # test_safebox_eth(safebox_eth)
    # test_safebox(dai, safebox_dai)
    # test_safebox(usdt, safebox_usdt)
    # test_safebox(usdc, safebox_usdc)
    # test_safebox(yfi, safebox_yfi)

    ###########################################################
    # test banks with uniswap spell
    # print('============ testing banks =============')

    # test_bank(usdt, bank)
    # test_bank(usdc, bank)
