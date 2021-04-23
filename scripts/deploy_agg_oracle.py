from brownie import interface, accounts, Contract
from brownie import AggregatorOracle, BandAdapterOracle, ChainlinkAdapterOracle, HomoraBank, CoreOracle, UniswapV2SpellV1
from .utils import *

from brownie.convert import to_decimal, to_string
import eth_abi
from brownie.network.gas.strategies import GasNowScalingStrategy

gas_strategy = GasNowScalingStrategy(
    initial_speed="fast", max_speed="fast", increment=1.085, block_duration=20)


token_infos = [
    (WETH, 'WETH'),
    (AAVE, 'AAVE'),
    (BAND, 'BAND'),
    (COMP, 'COMP'),
    (CRV, 'CRV'),
    (DAI, 'DAI'),
    (DPI, 'DPI'),
    (INDEX, 'INDEX'),
    (LINK, 'LINK'),
    (MKR, 'MKR'),
    (PERP, 'PERP'),
    (REN, 'REN'),
    (renBTC, 'RENBTC'),
    (SNX, 'SNX'),
    (sUSD, 'SUSD'),
    (SUSHI, 'SUSHI'),
    (UMA, 'UMA'),
    (UNI, 'UNI'),
    (USDC, 'USDC'),
    (USDT, 'USDT'),
    (WBTC, 'WBTC'),
    (wNXM, 'WNXM'),
    (YFI, 'YFI'),
]
tokens, token_names = zip(*token_infos)


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def sort_tokens(token):
    if token.lower() < WETH.lower():
        return token, WETH
    else:
        return WETH, token


def to_float(x):
    return float(to_string(x))


def check_token_prices(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer):
    for idx, token in enumerate(tokens):
        try:
            band_price = to_float(band_oracle.getETHPx(token))
            print('band', token_names[idx], ':', band_price)
        except:
            pass
        try:
            link_price = to_float(link_oracle.getETHPx(token))
            print('link', token_names[idx], ':', link_price)
        except:
            pass
        try:
            print('diff', max(band_price / link_price, link_price/band_price))
        except:
            pass
        print('agg', token_names[idx], ':', agg_oracle.getETHPx(token))
        token0, token1 = sort_tokens(token)
        print(token0, token1)
        agg_price = to_float(agg_oracle.getPrice(token0, token1)[0])
        print('agg v1', token_names[idx], ':', agg_price)
        try:
            simple_price = to_float(simple_oracle.getPrice(token0, token1)[0])
            print('simple', token_names[idx], ':', simple_price)
            print('diff', max(agg_price / simple_price, simple_price / agg_price))
        except Exception as e:
            print(e)
        print('===========================================')


def replace_v1_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer):
    bank_v1 = interface.IAny('0x67B66C99D3Eb37Fa76Aa3Ed1ff33E8e39F0b9c7A')
    goblin_config = interface.IAny('0x61858a3d3d8fDbC622a64a9fFB5b77Cc57beCB98')
    goblin_config.setOracle(agg_oracle, {'from': deployer, 'gas_price': gas_strategy})

    # ########################################################
    # # test
    # simple_oracle_owner = simple_oracle.owner()

    # # remove prices from simple oracle
    # token0s = []
    # token1s = []
    # for idx, token in enumerate(tokens):
    #     token0, token1 = sort_tokens(token)
    #     token0s.append(token0)
    #     token1s.append(token1)

    # simple_oracle.setPrices(token0s, token1s, [0] * len(token0s), {'from': simple_oracle_owner})

    # print('working ETH-DAI....')
    # alice = accounts[1]
    # goblin = interface.IAny('0x14804802592c0f6e2fd03e78ec3efc9b56f1963d')  # UNI DAI-ETH
    # two_side = '0xa1dc7CE03cB285aca8BDE9C27D1e5d4731871814'
    # bank_v1.work(0, goblin, 2 * 10**18, 0, eth_abi.encode_abi(['address', 'bytes'], [two_side, eth_abi.encode_abi(
    #     ['address', 'uint256', 'uint256'], [DAI, 0, 0])]), {'from': alice, 'value': '1.8 ether'})

    # print('working ETH-USDT...')
    # alice = accounts[1]
    # goblin = interface.IAny('0x4668ff4d478c5459d6023c4a7efda853412fb999')
    # two_side = '0x1debf8e2ddfc4764376e8e4ed5bc8f1b403d2629'
    # bank_v1.work(0, goblin, 2 * 10**18, 0, eth_abi.encode_abi(['address', 'bytes'], [two_side, eth_abi.encode_abi(
    #     ['address', 'uint256', 'uint256'], [USDT, 0, 0])]), {'from': alice, 'value': '1.8 ether'})


def check_replace_v2_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer):
    bank_v2 = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    core_oracle = CoreOracle.at('0x1E5BDdd0cDF8839d6b27b34927869eF0AD7bf692')

    simple_oracle_v2 = interface.IAny('0x487e0ae63Bfd8364a11e840900BaAD92D5aF7C42')

    # set route
    core_oracle.setRoute(tokens, [agg_oracle] * len(tokens), {'from': deployer, 'gas_price': gas_strategy})

    print(simple_oracle_v2.getETHPx(DAI))
    print(agg_oracle.getETHPx(DAI))

    print(simple_oracle_v2.getETHPx(USDT))
    print(agg_oracle.getETHPx(USDT))

    #####################################################################################
    print('=========================================================================')
    print('Case 1.')

    alice = accounts[1]

    usdt = interface.IAny(USDT)
    weth = interface.IAny(WETH)
    lp = interface.IAny('0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852')  # Uni USDT-WETH
    werc20 = interface.IAny('0xe28d9df7718b0b5ba69e01073fe82254a9ed2f98')

    uniswap_spell = UniswapV2SpellV1.at('0xc671B7251a789de0835a2fa33c83c8D4afB39092')

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(bank_v2)
    prevLPBal_werc20 = lp.balanceOf(werc20)

    if interface.IUniswapV2Pair(lp).token0() == usdt:
        prevARes, prevBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    else:
        prevBRes, prevARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    usdt_amt = 0
    weth_amt = 0
    lp_amt = 0
    borrow_usdt_amt = 0
    borrow_weth_amt = 0

    tx = bank_v2.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidityWERC20.encode_input(
            usdt,  # token 0
            weth,  # token 1
            [usdt_amt,  # supply USDT
             weth_amt,   # supply WETH
             lp_amt,  # supply LP
             borrow_usdt_amt,  # borrow USDT
             borrow_weth_amt,  # borrow WETH
             0,  # borrow LP tokens
             0,  # min USDT
             0],  # min WETH
        ),
        {'from': alice, 'value': '1 ether'}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(bank_v2)
    curLPBal_werc20 = lp.balanceOf(werc20)

    if interface.IUniswapV2Pair(lp).token0() == usdt:
        curARes, curBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    else:
        curBRes, curARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    print('spell lp balance', lp.balanceOf(uniswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('werc20 prev LP balance', prevLPBal_werc20)
    print('werc20 cur LP balance', curLPBal_werc20)

    print('prev usdt res', prevARes)
    print('cur usdt res', curARes)

    print('prev weth res', prevBRes)
    print('cur weth res', curBRes)

    # alice
    assert almostEqual(curABal - prevABal, -usdt_amt), 'incorrect USDT amt'
    assert almostEqual(curBBal - prevBBal, -weth_amt), 'incorrect WETH amt'
    assert curLPBal - prevLPBal == -lp_amt, 'incorrect LP amt'

    # spell
    assert usdt.balanceOf(uniswap_spell) == 0, 'non-zero spell USDT balance'
    assert weth.balanceOf(uniswap_spell) == 0, 'non-zero spell WETH balance'
    assert lp.balanceOf(uniswap_spell) == 0, 'non-zero spell LP balance'

    # check balance and pool reserves
    assert curABal - prevABal - borrow_usdt_amt == - \
        (curARes - prevARes), 'not all USDT tokens go to LP pool'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    simple_oracle = interface.IAny('0x05e7b38931948e10171e643e5f3004dcd0bef22b')
    band_oracle = BandAdapterOracle.deploy(
        '0xDA7a001b254CD22e46d3eAB04d937489c93174C3', {'from': deployer, 'gas_price': gas_strategy})
    link_oracle = ChainlinkAdapterOracle.deploy({'from': deployer, 'gas_price': gas_strategy})
    agg_oracle = AggregatorOracle.deploy({'from': deployer, 'gas_price': gas_strategy})

    # token list

    # list of (token address, band symbols, chainlink eth ref, agg deviation % (band + link))
    token_info_eth_refs = [
        (AAVE, 'AAVE', '0x6Df09E975c830ECae5bd4eD9d90f3A95a4f88012', 8 + 2),
        (BAND, 'BAND', '0x0BDb051e10c9718d1C29efbad442E88D38958274', 8 + 2),
        (COMP, 'COMP', '0x1B39Ee86Ec5979ba5C322b826B3ECb8C79991699', 8 + 2),
        (CRV, 'CRV', '0x8a12Be339B0cD1829b91Adc01977caa5E9ac121e', 8 + 2),
        (DAI, 'DAI', '0x773616E4d11A78F511299002da57A0a94577F1f4', 4 + 1),
        (DPI, 'DPI', '0x029849bbc0b1d93b85a8b6190e979fd38F5760E2', 8 + 2),
        (LINK, 'LINK', '0xDC530D9457755926550b59e8ECcdaE7624181557', 8 + 1),
        (MKR, 'MKR', '0x24551a8Fb2A7211A25a17B1481f043A8a8adC7f2', 8 + 1),
        (PERP, 'PERP', '0x3b41D5571468904D4e53b6a8d93A6BaC43f02dC9', 8 + 2),
        (REN, 'REN', '0x3147D7203354Dc06D9fd350c7a2437bcA92387a4', 8 + 2),
        (renBTC, 'RENBTC', '0xdeb288F737066589598e9214E782fa5A8eD689e8', 8 + 2),
        (SNX, 'SNX', '0x79291A9d692Df95334B1a0B3B4AE6bC606782f8c', 7 + 2),
        (sUSD, 'SUSD', '0x8e0b7e6062272B5eF4524250bFFF8e5Bd3497757', 4 + 1),
        (SUSHI, 'SUSHI', '0xe572CeF69f43c2E488b33924AF04BDacE19079cf', 8 + 2),
        (UMA, 'UMA', '0xf817B69EA583CAFF291E287CaE00Ea329d22765C', 8 + 2),
        (UNI, 'UNI', '0xD6aA3D25116d8dA79Ea0246c4826EB951872e02e', 8 + 2),
        (USDC, 'USDC', '0x986b5E1e1755e3C2440e960477f25201B0a8bbD4', 4 + 1),
        (USDT, 'USDT', '0xEe9F2375b4bdF6387aa8265dD4FB8F16512A1d46', 4 + 1),
        (WBTC, 'WBTC', '0xdeb288F737066589598e9214E782fa5A8eD689e8', 8 + 2),
        (wNXM, 'WNXM', '0xe5Dc0A609Ab8bCF15d3f35cFaa1Ff40f521173Ea', 8 + 2),
        (YFI, 'YFI', '0x7c5d4F8345e66f68099581Db340cd65B078C41f4', 7 + 1),
    ]

    token_addresses, symbols, link_eth_refs, deviations = zip(*token_info_eth_refs)

    # setup band oracle
    band_token_addresses = token_addresses + (INDEX,)
    band_symbols = symbols + ('INDEX',)
    band_oracle.setSymbols(band_token_addresses, band_symbols, {'from': deployer, 'gas_price': gas_strategy})
    band_oracle.setMaxDelayTimes(
        band_token_addresses, [3600 * 3 + 5 * 60] * len(band_token_addresses), {'from': deployer, 'gas_price': gas_strategy})  # ~3 hour

    # setup link oracle
    link_oracle.setRefsETH(token_addresses, link_eth_refs, {'from': deployer, 'gas_price': gas_strategy})
    link_oracle.setMaxDelayTimes(
        token_addresses, [3600 * 36 + 5 * 60] * len(token_addresses), {'from': deployer, 'gas_price': gas_strategy})  # ~1.5 day

    # setup agg oracle
    agg_token_addresses = token_addresses + (INDEX, WETH,)
    agg_deviations = list(map(lambda d: (100 + d) * 10**16, deviations + (8 + 2, 0, )))
    agg_sources = [[band_oracle.address, link_oracle.address]] * len(token_addresses) + \
        [[band_oracle.address]] + \
        [[band_oracle.address, link_oracle.address]]
    agg_oracle.setMultiPrimarySources(agg_token_addresses,
                                      agg_deviations,
                                      agg_sources,
                                      {'from': deployer, 'gas_price': gas_strategy})

    ########################################################################
    # replace in v1 bank
    # print('Replacing v1 simple oracle...')
    # replace_v1_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer)

    ########################################################################
    # check token prices

    # check_token_prices(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer)

    ########################################################################
    # try replacing in v2 bank

    # check_replace_v2_oracle(band_oracle, link_oracle, simple_oracle, agg_oracle, deployer)
