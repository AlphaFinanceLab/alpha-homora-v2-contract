from brownie import (
    accounts, ERC20KP3ROracle, UniswapV2Oracle, BalancerPairOracle, ProxyOracle, CoreOracle,
    HomoraBank, CurveOracle, UniswapV2SpellV1, WERC20, WLiquidityGauge, WMasterChef,
    WStakingRewards, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1, SafeBoxETH, SafeBox
)
from brownie import interface, accounts, chain
from .utils import *
from brownie.network.gas.strategies import GasNowScalingStrategy
from brownie import network

gas_strategy = GasNowScalingStrategy(
    initial_speed="fast", max_speed="fast", increment=1.085, block_duration=20)

# set gas strategy
network.gas_price(gas_strategy)


CRV_REGISTRY = '0x7D86446dDb609eD0F5f8684AcF30380a356b2B4c'
CRV_TOKEN = '0xD533a949740bb3306d119CC777fa900bA034cd52'
MASTERCHEF = '0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd'
BANK = '0xba5eBAf3fc1Fcca67147050Bf80462393814E54B'


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def test_bank_uniswap(
        token,
        bank,
        user,
        token_amt,
        weth_amt=0,
        msg_value=0,
        borrow_token_amt=0,
        borrow_weth_amt=0):

    print('testing bank::uniswapV2spellV1 with token', token.name())

    uniswap_spell = UniswapV2SpellV1.at(
        '0x7b1f4cDD4f599774feae6516460BCCD97Fc2100E')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    # token.approve(bank, 2**256-1, {'from': user})

    prevTokenUser = token.balanceOf(user)
    bank.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidityWERC20.encode_input(
            token,
            weth,
            [token_amt, weth_amt, 0, borrow_token_amt, borrow_weth_amt, 0, 0, 0]
        ),
        {'from': user, 'value': msg_value, 'gas_price': gas_strategy}
    )

    curTokenUser = token.balanceOf(user)

    assert almostEqual(curTokenUser - prevTokenUser, -token_amt), (
        'incorrect input amt'
    )


def test_bank_sushiswap(
        token,
        bank,
        user,
        pool_id,
        token_amt,
        weth_amt=0,
        msg_value=0,
        borrow_token_amt=0,
        borrow_weth_amt=0):

    print('testing bank::sushiswapSpellV1 with token', token.name())
    sushiswap_spell = SushiswapSpellV1.at(
        '0xc4a59cfEd3FE06bDB5C21dE75A70B20dB280D8fE'
    )
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    # token.approve(bank, 2**256-1, {'from': user})

    prevTokenUser = token.balanceOf(user)

    bank.execute(
        0,
        sushiswap_spell,
        sushiswap_spell.addLiquidityWMasterChef.encode_input(
            token,
            weth,
            [token_amt, weth_amt, 0, borrow_token_amt, borrow_weth_amt, 0, 0, 0],
            pool_id
        ),
        {'from': user, 'value': msg_value, 'gas_price': gas_strategy}
    )

    curTokenUser = token.balanceOf(user)
    assert almostEqual(curTokenUser - prevTokenUser, -token_amt), (
        'incorrect input amt'
    )


def main():

    deployer = accounts.at(
        '0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    cylink = '0xE7BFf2Da8A2f619c2586FB83938Fa56CE803aA16'
    cywbtc = '0x8Fc8BFD80d6A9F17Fb98A373023d72531792B431'
    cyuni = '0xFEEB92386A055E2eF7C2B598c872a4047a7dB59F'
    cysushi = '0x226F3738238932BA0dB2319a8117D9555446102f'

    link = interface.IERC20Ex('0x514910771AF9Ca656af840dff83E8264EcF986CA')
    wbtc = interface.IERC20Ex('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599')
    uni = interface.IERC20Ex('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984')
    sushi = interface.IERC20Ex('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2')

    bank = HomoraBank.at('0xba5eBAf3fc1Fcca67147050Bf80462393814E54B')
    # bank.addBank(link, cylink, {'from': deployer}) # already added
    # bank.addBank(wbtc, cywbtc, {'from': deployer}) # already added
    bank.addBank(uni, cyuni, {'from': deployer})
    bank.addBank(sushi, cysushi, {'from': deployer})

    bank.setWhitelistTokens(
        [wbtc.address, uni.address, sushi.address],
        [True, True, True],
        {'from': deployer}
    )

    #######################################################################
    # Try Opening positions in each pool

    tester = accounts.at(
        '0x60e86029ed1A8b91cB0dF8BBDFE56c4C2Ad2D073',
        force=True
    )
    # tester = accounts.load('homora-relaunch')

    # TODO: in production please remove this line and use real money.
    accounts[0].transfer(tester, '100 ether')

    print("opening wbtc-weth position with uniswap spell and borrowing wbtc...")
    test_bank_uniswap(
        wbtc,
        bank,
        tester,
        0,
        msg_value='0.03 ether',
        borrow_token_amt=10**5,
        borrow_weth_amt=0,
    )
    print("Done!!!")

    print("opening uni-weth position with uniswap spell and borrowing uni...")
    test_bank_uniswap(
        uni,
        bank,
        tester,
        0,
        msg_value='0.02 ether',
        borrow_token_amt=5 * 10**17,
        borrow_weth_amt=0,
    )
    print("Done!!!")

    print("opening sushi-weth position with sushiswap spell and borrowing sushi...")
    test_bank_sushiswap(
        sushi,
        bank,
        tester,
        12,
        0,
        msg_value='0.02 ether',
        borrow_token_amt=10**18,
        borrow_weth_amt=0,
    )
    print("Done!!!")
    print("End of deploy process!!!")

    ###########################################################
    # test banks with uniswap spell
    print('==========================================')
    print('testing banks')
    alice = accounts[1]
    mint_tokens(link, alice)
    print(int(0.001 * 10 ** link.decimals()))

    for token in [link, wbtc, uni]:
        mint_tokens(token, alice)
        test_bank_uniswap(
            token,
            bank,
            alice,
            10 ** token.decimals(),
            borrow_token_amt=int(0.001 * 10 ** token.decimals()),
            borrow_weth_amt=10**12,
        )

    for token, pool_id in [(sushi, 12)]:
        mint_tokens(token, alice)
        test_bank_sushiswap(
            token,
            bank,
            alice,
            pool_id,
            10 ** token.decimals(),
            borrow_token_amt=int(0.001 * 10 ** token.decimals()),
            borrow_weth_amt=10**12,
        )

    print("Done!!!!")
