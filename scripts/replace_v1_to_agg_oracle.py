from brownie import interface, accounts, Contract
from brownie import AggregatorOracle, BandAdapterOracle, ChainlinkAdapterOracle, HomoraBank, CoreOracle, UniswapV2SpellV1
from .utils import *
from .tokens import *
import eth_abi

from brownie.network.gas.strategies import GasNowScalingStrategy
from brownie import network

gas_strategy = GasNowScalingStrategy(
    initial_speed="fast", max_speed="fast", increment=1.085, block_duration=20)

# set gas strategy
network.gas_price(gas_strategy)

token_names = ['weth', 'aave', 'band', 'comp', 'crv', 'dai',
               'dpi', 'link', 'mkr', 'perp', 'ren', 'renbtc',
               'snx', 'susd', 'sushi', 'uma', 'uni', 'usdc', 'usdt', 'wbtc', 'yfi'
               ]
tokens = [
    Tokens.WETH,
    Tokens.AAVE,
    Tokens.BAND,
    Tokens.COMP,
    Tokens.CRV,
    Tokens.DAI,
    Tokens.DPI,
    Tokens.LINK,
    Tokens.MKR,
    Tokens.PERP,
    Tokens.REN,
    Tokens.RENBTC,
    Tokens.SNX,
    Tokens.SUSD,
    Tokens.SUSHI,
    Tokens.UMA,
    Tokens.UNI,
    Tokens.USDC,
    Tokens.USDT,
    Tokens.WBTC,
    Tokens.YFI
]


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def sort_tokens(token):
    if token.lower() < WETH.lower():
        return token, WETH
    else:
        return WETH, token


def check_token_prices(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer):
    for idx, token in enumerate(tokens):
        print('band', token_names[idx], ':', band_oracle.getETHPx(token))
        print('link', token_names[idx], ':', link_oracle.getETHPx(token))
        print('agg', token_names[idx], ':', agg_oracle.getETHPx(token))
        token0, token1 = sort_tokens(token)
        print(token0, token1)
        agg_price = agg_oracle.getPrice(token0, token1)
        print('agg v1', token_names[idx], ':', agg_price)
        try:
            simple_price = simple_oracle.getPrice(token0, token1)
            print('simple', token_names[idx], ':', simple_price)
            assert 1/1.05 < agg_price / simple_price < 1.05, 'deviation exceeds 5%'
        except:
            pass
        print('===========================================')


def check_replace_v1_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer):
    bank_v1 = interface.IAny('0x67B66C99D3Eb37Fa76Aa3Ed1ff33E8e39F0b9c7A')
    goblin_config = interface.IAny('0x61858a3d3d8fDbC622a64a9fFB5b77Cc57beCB98')
    goblin_config.setOracle(agg_oracle, {'from': deployer})

    # # test if `work` can still be called (should not revert)
    # simple_oracle_owner = simple_oracle.owner()

    # # remove prices from simple oracle
    # token0s = []
    # token1s = []
    # for idx, token in enumerate(tokens):
    #     token0, token1 = sort_tokens(token)
    #     token0s.append(token0)
    #     token1s.append(token1)

    # simple_oracle.setPrices(token0s, token1s, [0] * len(token0s), {'from': simple_oracle_owner})

    # print('working....')
    # alice = accounts[1]
    # goblin = interface.IAny('0x14804802592c0f6e2fd03e78ec3efc9b56f1963d')  # UNI DAI-ETH
    # two_side = '0xa1dc7CE03cB285aca8BDE9C27D1e5d4731871814'
    # bank_v1.work(0, goblin, 2 * 10**18, 0, eth_abi.encode_abi(['address', 'bytes'], [two_side, eth_abi.encode_abi(
    #     ['address', 'uint256', 'uint256'], [DAI, 0, 0])]), {'from': alice, 'value': '1.8 ether'})


def check_replace_v2_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer):
    bank_v2 = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    core_oracle = CoreOracle.at('0x1E5BDdd0cDF8839d6b27b34927869eF0AD7bf692')

    simple_oracle_v2 = interface.IAny('0x487e0ae63Bfd8364a11e840900BaAD92D5aF7C42')

    v2_tokens = [
        Tokens.WETH,
        Tokens.DAI,
        Tokens.USDC,
        Tokens.USDT,
        Tokens.UNI,
        Tokens.PERP,
        Tokens.SUSHI
    ]

    # set route
    core_oracle.setRoute(v2_tokens, [agg_oracle] * len(v2_tokens), {'from': deployer})

    # for token in v2_tokens:
    #     simple_price = simple_oracle_v2.getETHPx(token)
    #     agg_price = agg_oracle.getETHPx(token)
    #     print(token, 'diff:', max(simple_price / agg_price, agg_price / simple_price))

    # print(simple_oracle_v2.getETHPx(DAI))
    # print(agg_oracle.getETHPx(DAI))

    # print(simple_oracle_v2.getETHPx(USDT))
    # print(agg_oracle.getETHPx(USDT))

    # #####################################################################################
    # print('=========================================================================')
    # print('Case 1.')

    # alice = accounts[1]

    # usdt = interface.IAny(USDT)
    # weth = interface.IAny(WETH)
    # lp = interface.IAny('0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852')  # Uni USDT-WETH
    # werc20 = interface.IAny('0xe28d9df7718b0b5ba69e01073fe82254a9ed2f98')

    # uniswap_spell = UniswapV2SpellV1.at('0xc671B7251a789de0835a2fa33c83c8D4afB39092')

    # prevABal = usdt.balanceOf(alice)
    # prevBBal = weth.balanceOf(alice)
    # prevLPBal = lp.balanceOf(alice)
    # prevLPBal_bank = lp.balanceOf(bank_v2)
    # prevLPBal_werc20 = lp.balanceOf(werc20)

    # if interface.IUniswapV2Pair(lp).token0() == usdt:
    #     prevARes, prevBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    # else:
    #     prevBRes, prevARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    # usdt_amt = 0
    # weth_amt = 0
    # lp_amt = 0
    # borrow_usdt_amt = 0
    # borrow_weth_amt = 0

    # tx = bank_v2.execute(
    #     0,
    #     uniswap_spell,
    #     uniswap_spell.addLiquidityWERC20.encode_input(
    #         usdt,  # token 0
    #         weth,  # token 1
    #         [usdt_amt,  # supply USDT
    #          weth_amt,   # supply WETH
    #          lp_amt,  # supply LP
    #          borrow_usdt_amt,  # borrow USDT
    #          borrow_weth_amt,  # borrow WETH
    #          0,  # borrow LP tokens
    #          0,  # min USDT
    #          0],  # min WETH
    #     ),
    #     {'from': alice, 'value': '1 ether'}
    # )

    # curABal = usdt.balanceOf(alice)
    # curBBal = weth.balanceOf(alice)
    # curLPBal = lp.balanceOf(alice)
    # curLPBal_bank = lp.balanceOf(bank_v2)
    # curLPBal_werc20 = lp.balanceOf(werc20)

    # if interface.IUniswapV2Pair(lp).token0() == usdt:
    #     curARes, curBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    # else:
    #     curBRes, curARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    # print('spell lp balance', lp.balanceOf(uniswap_spell))
    # print('Alice delta A balance', curABal - prevABal)
    # print('Alice delta B balance', curBBal - prevBBal)
    # print('add liquidity gas', tx.gas_used)
    # print('bank lp balance', curLPBal_bank)

    # print('bank prev LP balance', prevLPBal_bank)
    # print('bank cur LP balance', curLPBal_bank)

    # print('werc20 prev LP balance', prevLPBal_werc20)
    # print('werc20 cur LP balance', curLPBal_werc20)

    # print('prev usdt res', prevARes)
    # print('cur usdt res', curARes)

    # print('prev weth res', prevBRes)
    # print('cur weth res', curBRes)

    # # alice
    # assert almostEqual(curABal - prevABal, -usdt_amt), 'incorrect USDT amt'
    # assert almostEqual(curBBal - prevBBal, -weth_amt), 'incorrect WETH amt'
    # assert curLPBal - prevLPBal == -lp_amt, 'incorrect LP amt'

    # # spell
    # assert usdt.balanceOf(uniswap_spell) == 0, 'non-zero spell USDT balance'
    # assert weth.balanceOf(uniswap_spell) == 0, 'non-zero spell WETH balance'
    # assert lp.balanceOf(uniswap_spell) == 0, 'non-zero spell LP balance'

    # # check balance and pool reserves
    # assert curABal - prevABal - borrow_usdt_amt == - \
    #     (curARes - prevARes), 'not all USDT tokens go to LP pool'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    simple_oracle = interface.IAny('0x05e7b38931948e10171e643e5f3004dcd0bef22b')
    band_oracle = BandAdapterOracle.at('0xb35E6a063CC00c66408284d60765c52e70394772')
    link_oracle = ChainlinkAdapterOracle.at('0x9A42660eebFf100B9D88cab82b3049Ae2a33712f')
    agg_oracle = AggregatorOracle.at('0x636478DcecA0308ec6b39e3ab1e6b9EBF00Cd01c')

    ########################################################################
    # check token prices

    # check_token_prices(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer)

    ########################################################################
    # try replacing in v1 bank

    check_replace_v1_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer)

    ########################################################################
    # try replacing in old v2 bank

    check_replace_v2_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer)
