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


def test_safebox_eth(safebox):
    alice = accounts[1]

    deposit_amt = 100000 * 10**18

    prevETHBal = alice.balance()
    safebox.deposit({'from': alice, 'value': deposit_amt})
    curETHBal = alice.balance()

    assert almostEqual(curETHBal - prevETHBal, -
                       deposit_amt), 'incorrect deposit amount'

    withdraw_amt = safebox.balanceOf(alice) // 3

    prevETHBal = alice.balance()
    safebox.withdraw(withdraw_amt, {'from': alice})
    curETHBal = alice.balance()

    assert almostEqual(curETHBal - prevETHBal, deposit_amt //
                       3), 'incorrect first withdraw amount'

    withdraw_amt = safebox.balanceOf(alice)

    prevETHBal = alice.balance()
    safebox.withdraw(withdraw_amt, {'from': alice})
    curETHBal = alice.balance()

    assert almostEqual(curETHBal - prevETHBal, deposit_amt - deposit_amt //
                       3), 'incorrect second withdraw amount'


def test_safebox(token, safebox):
    print('testing', token.name())
    alice = accounts[1]

    mint_tokens(token, alice)

    token.approve(safebox, 2**256-1, {'from': alice})

    deposit_amt = 1 * 10**token.decimals()

    prevBal = token.balanceOf(alice)
    safebox.deposit(deposit_amt, {'from': alice})
    curBal = token.balanceOf(alice)

    assert almostEqual(curBal - prevBal, -
                       deposit_amt), 'incorrect deposit amount'

    withdraw_amt = safebox.balanceOf(alice) // 3

    prevBal = token.balanceOf(alice)
    safebox.withdraw(withdraw_amt, {'from': alice})
    curBal = token.balanceOf(alice)

    assert almostEqual(curBal - prevBal, deposit_amt //
                       3), 'incorrect first withdraw amount'

    withdraw_amt = safebox.balanceOf(alice)

    prevBal = token.balanceOf(alice)
    safebox.withdraw(withdraw_amt, {'from': alice})
    curBal = token.balanceOf(alice)

    assert almostEqual(curBal - prevBal, deposit_amt - deposit_amt //
                       3), 'incorrect second withdraw amount'


def test_bank_uniswap(token, bank):
    alice = accounts[1]
    print('testing', token.name())

    uniswap_spell = UniswapV2SpellV1.at(
        '0x7b1f4cDD4f599774feae6516460BCCD97Fc2100E')

    mint_tokens(token, alice)

    token.approve(bank, 2**256-1, {'from': alice})

    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    amt = 1 * (10 ** token.decimals())

    borrow_amt = int(0.01 * (10 ** token.decimals()))

    prevTokenAlice = token.balanceOf(alice)

    bank.execute(0, uniswap_spell, uniswap_spell.addLiquidityWERC20.encode_input(
        token, weth, [amt, 0, 0, borrow_amt, 10**12, 0, 0, 0]), {'from': alice})

    curTokenAlice = token.balanceOf(alice)

    assert almostEqual(curTokenAlice - prevTokenAlice, -
                       amt), 'incorrect input amt'


def test_bank_sushiswap(token, bank):
    alice = accounts[1]
    print('testing bank with token ', token.name())

    sushiswap_spell = SushiswapSpellV1.at(
        '0xc4a59cfEd3FE06bDB5C21dE75A70B20dB280D8fE')

    mint_tokens(token, alice)

    token.approve(bank, 2**256-1, {'from': alice})

    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    amt = 1 * (10**token.decimals())

    borrow_amt = int(0.01 * (10**token.decimals()))

    prevTokenAlice = token.balanceOf(alice)

    bank.execute(0, sushiswap_spell, sushiswap_spell.addLiquidityWMasterChef.encode_input(
        token, weth, [amt, 0, 0, borrow_amt, 10**12, 0, 0, 0], 12), {'from': alice})

    curTokenAlice = token.balanceOf(alice)

    assert almostEqual(curTokenAlice - prevTokenAlice, -
                       amt), 'incorrect input amt'


def main():

    publish_status = False

    deployer = accounts.at(
        '0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    # deploy safeboxes (uni + sushi)

    cylink = '0xE7BFf2Da8A2f619c2586FB83938Fa56CE803aA16'
    cywbtc = '0x8Fc8BFD80d6A9F17Fb98A373023d72531792B431'
    cyuni = '0xFEEB92386A055E2eF7C2B598c872a4047a7dB59F'
    cysushi = '0x226F3738238932BA0dB2319a8117D9555446102f'

    safebox_link = SafeBox.deploy(cylink, 'Interest Bearing ChainLink Token', 'ibLINKv2', {
                                  'from': deployer}, publish_source=publish_status)
    safebox_wbtc = SafeBox.deploy(cywbtc, 'Interest Bearing Wrapped BTC', 'ibWBTCv2', {
                                  'from': deployer}, publish_source=publish_status)
    safebox_uni = SafeBox.deploy(cyuni, 'Interest Bearing Uniswap', 'ibUNIv2', {
                                 'from': deployer}, publish_source=publish_status)
    safebox_sushi = SafeBox.deploy(cysushi, 'Interest Bearing SushiToken', 'ibSUSHI', {
                                   'from': deployer}, publish_source=publish_status)

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

    # TODO: in production please remove this line and use real money.
    accounts[0].transfer(tester, '100 ether')

    print("opening wbtc-weth on uniswap spell with borrowing...")
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    uniswap_spell = UniswapV2SpellV1.at(
        '0x7b1f4cDD4f599774feae6516460BCCD97Fc2100E')
    bank.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidityWERC20.encode_input(
            wbtc,
            weth,
            [0, 0, 0, 10**5, 10**7, 0, 0, 0]
        ),
        {'from': tester, 'value': '0.03 ether', 'gas_price': gas_strategy}
    )
    print("pass!!!")

    print("opening uni-weth on uniswap spell with borrowing...")
    bank.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidityWERC20.encode_input(
            uni,
            weth,
            [0, 0, 0, 10**17, 10**10, 0, 0, 0]
        ),
        {'from': tester, 'value': '0.01 ether', 'gas_price': gas_strategy}
    )
    print("pass!!!")

    print("opening sushi-weth on sushiswap spell with borrowing...")
    sushiswap_spell = SushiswapSpellV1.at(
        '0xc4a59cfEd3FE06bDB5C21dE75A70B20dB280D8fE')
    bank.execute(
        0,
        sushiswap_spell,
        sushiswap_spell.addLiquidityWMasterChef.encode_input(
            sushi,
            weth,
            [0, 0, 0, 5*10**16, 10**10, 0, 0, 0],
            12
        ),
        {'from': tester, 'value': '0.01 ether', 'gas_price': gas_strategy}
    )
    print("pass!!!")

    ###########################################################
    # test cyToken
    print('==========================================')
    print('asserting cyTokens')

    for token in [cyuni, cysushi]:
        assert interface.IERC20Ex(token).symbol() == 'cy' + \
            interface.IERC20Ex(interface.IERC20Ex(token).underlying()).symbol()

    ###########################################################
    # test safeboxes
    print('==========================================')
    print('testing safeboxes')

    test_safebox(link, safebox_link)
    test_safebox(wbtc, safebox_wbtc)
    test_safebox(uni, safebox_uni)
    test_safebox(sushi, safebox_sushi)

    ###########################################################
    # test banks with uniswap spell
    print('==========================================')
    print('testing banks')

    mint_tokens(link, accounts[3])
    link.approve(safebox_link, 2**256-1, {'from': accounts[3]})
    safebox_link.deposit(
        link.balanceOf(accounts[3], {'from': accounts[3]}),
        {'from': accounts[3]}
    )
    test_bank_uniswap(link, bank)

    mint_tokens(wbtc, accounts[3])
    wbtc.approve(safebox_wbtc, 2**256-1, {'from': accounts[3]})
    safebox_wbtc.deposit(
        wbtc.balanceOf(accounts[3], {'from': accounts[3]}),
        {'from': accounts[3]}
    )
    test_bank_uniswap(wbtc, bank)

    mint_tokens(uni, accounts[3])
    uni.approve(safebox_uni, 2**256-1, {'from': accounts[3]})
    safebox_uni.deposit(
        uni.balanceOf(accounts[3], {'from': accounts[3]}),
        {'from': accounts[3]}
    )
    test_bank_uniswap(uni, bank)

    mint_tokens(sushi, accounts[3])
    sushi.approve(safebox_sushi, 2**256-1, {'from': accounts[3]})
    safebox_sushi.deposit(
        sushi.balanceOf(accounts[3], {'from': accounts[3]}),
        {'from': accounts[3]}
    )
    test_bank_sushiswap(sushi, bank)

    print("Done!!!!")
