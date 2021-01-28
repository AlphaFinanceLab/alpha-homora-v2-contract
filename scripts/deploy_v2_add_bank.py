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
        token, weth, [amt, 0, 0, borrow_amt, 10**15, 0, 0, 0]), {'from': alice})

    curTokenAlice = token.balanceOf(alice)

    assert almostEqual(curTokenAlice - prevTokenAlice, -amt), 'incorrect input amt'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    yfi = interface.IERC20Ex('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e')
    cyyfi = '0xFa3472f7319477c9bFEcdD66E4B948569E7621b9'

    bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    bank.addBank(yfi, cyyfi, {'from': deployer})

    ###########################################################
    # test cyToken

    # for token in [cyyfi]:
    #     assert interface.IERC20Ex(token).symbol() == 'cy' + \
    #         interface.IERC20Ex(interface.IERC20Ex(token).underlying()).symbol()

    ###########################################################
    # test banks with uniswap spell
    # print('============ testing banks =============')

    # alice = accounts[1]
    # mint_tokens(yfi, alice)
    # yfi.approve(cyyfi, 2**256-1, {'from': alice})

    # interface.IERC20Ex(cyyfi).mint(10 * 10**yfi.decimals(), {'from': alice})

    # print(interface.IERC20Ex(cyyfi).borrow(10, {'from': alice}).return_value)
    # test_bank(yfi, bank)
