from brownie import (
    accounts, ERC20KP3ROracle, UniswapV2Oracle, BalancerPairOracle, ProxyOracle, CoreOracle,
    HomoraBank, CurveOracle, UniswapV2SpellV1, WERC20, WLiquidityGauge, WMasterChef,
    WStakingRewards, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1, SafeBoxETH, SafeBox
)
from brownie import interface, accounts, chain
from .utils import *


KP3R_NETWORK = '0x73353801921417F465377c8d898c6f4C0270282C'
CRV_REGISTRY = '0x7D86446dDb609eD0F5f8684AcF30380a356b2B4c'
CRV_TOKEN = '0xD533a949740bb3306d119CC777fa900bA034cd52'
MASTERCHEF = '0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd'
BANK = '0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb'


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def test_safebox(token, safebox):
    alice = accounts[1]

    mint_tokens(token, alice)

    token.approve(safebox, 2**256-1, {'from': alice})

    deposit_amt = 10 * 10**token.decimals()

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

    amt = 100 * 10**(token.decimals() - 4)

    borrow_amt = 1 * 10**(token.decimals() - 4)

    prevTokenAlice = token.balanceOf(alice)

    bank.execute(0, uniswap_spell, uniswap_spell.addLiquidityWERC20.encode_input(
        token, weth, [amt, 0, 0, borrow_amt, 10**10, 0, 0, 0]), {'from': alice})

    curTokenAlice = token.balanceOf(alice)

    assert almostEqual(curTokenAlice - prevTokenAlice, -amt), 'incorrect input amt'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)

    # deployer = accounts.load('gh')
    snx = interface.IERC20Ex('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F')
    susd = interface.IERC20Ex('0x57Ab1ec28D129707052df4dF418D58a2D46d5f51')

    cysnx = interface.IERC20Ex('0x12A9cC33A980DAa74E00cc2d1A0E74C57A93d12C')
    cysusd = interface.IERC20Ex('0x4e3a36A633f63aee0aB57b5054EC78867CB3C0b8')

    # add safeboxes
    safebox_snx = SafeBox.deploy(
        cysnx, 'Interest Bearing Synthetix Network Token v2', 'ibSNXv2', {'from': deployer})
    safebox_susd = SafeBox.deploy(
        cysusd, 'Interest Bearing Synth sUSD v2', 'ibsUSDv2', {'from': deployer})

    # add banks
    bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    bank.addBank(snx, cysnx, {'from': deployer})
    bank.addBank(susd, cysusd, {'from': deployer})

    ###########################################################
    # test cyToken

    # for token in [cysnx, cysusd]:
    #     assert interface.IERC20Ex(token).symbol().lower() == 'cy' + \
    #         interface.IERC20Ex(interface.IERC20Ex(token).underlying()).symbol().lower()

    ###########################################################
    # test safeboxes
    # print('============= testing safeboxes ===============')

    # test_safebox(snx, safebox_snx)
    # test_safebox(susd, safebox_susd)

    ###########################################################
    # test banks with uniswap spell
    # print('============ testing banks =============')

    # alice = accounts[1]
    # # test snx
    # mint_tokens(snx, alice)
    # snx.approve(cysnx, 2**256-1, {'from': alice})

    # interface.IERC20Ex(cysnx).mint(10 * 10**snx.decimals(), {'from': alice})

    # print(interface.IERC20Ex(cysnx).borrow(10, {'from': alice}).return_value)
    # test_bank(snx, bank)

    # # test susd
    # mint_tokens(susd, alice)
    # susd.approve(cysusd, 2**256-1, {'from': alice})

    # interface.IERC20Ex(cysusd).mint(10 * 10**susd.decimals(), {'from': alice})

    # print(interface.IERC20Ex(cysusd).borrow(10, {'from': alice}).return_value)
    # test_bank(susd, bank)
