from brownie import (
    accounts, ERC20KP3ROracle, UniswapV2Oracle, BalancerPairOracle, ProxyOracle, CoreOracle,
    HomoraBank, CurveOracle, UniswapV2SpellV1, WERC20, WLiquidityGauge, WMasterChef,
    WStakingRewards, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1, SafeBox, SafeBoxETH
)
from brownie import interface
from .utils import *
from .tokens import Tokens


KP3R_NETWORK = '0x73353801921417F465377c8d898c6f4C0270282C'
CRV_REGISTRY = '0x7D86446dDb609eD0F5f8684AcF30380a356b2B4c'
CRV_TOKEN = '0xD533a949740bb3306d119CC777fa900bA034cd52'
MASTERCHEF = '0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd'
BANK = '0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb'


def get_safebox(token):
    if token == Tokens.weth:
        return SafeBoxETH.at('0xeEa3311250FE4c3268F8E684f7C87A82fF183Ec1')
    elif token == Tokens.dai:
        return SafeBox.at('0xee8389d235E092b2945fE363e97CDBeD121A0439')
    elif token == Tokens.usdt:
        return SafeBox.at('0x020eDC614187F9937A1EfEeE007656C6356Fb13A')
    elif token == Tokens.usdc:
        return SafeBox.at('0x08bd64BFC832F1C2B3e07e634934453bA7Fa2db2')
    elif token == Tokens.yfi:
        return SafeBox.at('0x3614644AE157280b5C1d17AE686C153a204aaf3b')
    elif token == Tokens.dpi:
        return SafeBox.at('0x9E6aCA6B13a0Bc3364D035fF6D97ff4dB319F88A')
    elif token == Tokens.snx:
        return SafeBox.at('0x9446614037a839730A92E28a7ec870344B7B8F09')
    elif token == Tokens.susd:
        return SafeBox.at('0x3E1F2Feb27738609a22aa8B192a1a9138c445aa0')
    else:
        raise Exception(f'safebox not supported for token {token}')


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def deposit_safebox(token):
    alice = accounts[0]

    mint_tokens(token, alice)

    safebox = get_safebox(token)

    token.approve(safebox, 0, {'from': alice})
    token.approve(safebox, 2**256-1, {'from': alice})

    if token == Tokens.weth:
        safebox.deposit({'from': alice, 'value': '100 ether'})
    else:
        safebox.deposit(token.balanceOf(alice), {'from': alice})


def test_uniswap_spell(uniswap_spell, homora, oracle, token0, token1):
    alice = accounts[0]

    token0 = interface.IERC20Ex(token0)
    token1 = interface.IERC20Ex(token1)

    mint_tokens(token0, alice)
    mint_tokens(token1, alice)

    token0.approve(homora, 0, {'from': alice})
    token1.approve(homora, 0, {'from': alice})

    token0.approve(homora, 2**256-1, {'from': alice})
    token1.approve(homora, 2**256-1, {'from': alice})

    prevABal = token0.balanceOf(alice)
    prevBBal = token1.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    token0_borrow_amt = 1 * 10**(token0.decimals() - 4) if homora.banks(token0)[0] else 0
    token1_borrow_amt = 1 * 10**(token1.decimals() - 4) if homora.banks(token1)[0] else 0

    # open a position
    homora.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidityWERC20.encode_input(
            token0,
            token1,
            [10 * 10**(token0.decimals() - 4),
             20 * 10**(token1.decimals() - 4),
             0,
             token0_borrow_amt,
             token1_borrow_amt,
             0,
             0,
             0],
        ),
        {'from': alice}
    )

    curABal = token0.balanceOf(alice)
    curBBal = token1.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = token0.balanceOf(alice)
    prevBBal = token1.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    token0_repay_amt = 2**256-1 if homora.banks(token0)[0] else 0
    token1_repay_amt = 2**256-1 if homora.banks(token1)[0] else 0

    # close the position
    homora.execute(
        position_id - 1,
        uniswap_spell,
        uniswap_spell.removeLiquidityWERC20.encode_input(
            token0,
            token1,
            [2**256-1,
             0,
             token0_repay_amt,
             token1_repay_amt,
             0,
             0,
             0],
        ),
        {'from': alice}
    )

    curABal = token0.balanceOf(alice)
    curBBal = token1.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(token0)
    tokenBPrice = oracle.getETHPx(token1)
    tokenETHPrice = oracle.getETHPx('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta ETH Bal', curETHBal - prevETHBal)

    print('token A price', tokenAPrice)
    print('token B price', tokenBPrice)
    print('token ETH price', tokenETHPrice)

    assert almostEqual(tokenAPrice * initABal + tokenBPrice * initBBal + tokenETHPrice * initETHBal,
                       tokenAPrice * finalABal + tokenBPrice * finalBBal + tokenETHPrice * finalETHBal), 'too much value lost'


def test_uniswap_spell_wstaking(uniswap_spell, homora, wstaking, oracle):
    alice = accounts[0]

    dpi = interface.IERC20Ex('0x1494ca1f11d487c2bbe4543e90080aeba4ba3c2b')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    index = interface.IERC20Ex('0x0954906da0bf32d5479e25f46056d22f08464cab')

    mint_tokens(dpi, alice)
    mint_tokens(weth, alice)

    dpi.approve(homora, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})

    prevABal = dpi.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    # open a position
    homora.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidityWStakingRewards.encode_input(
            dpi,
            weth,
            [10**18,
             10**18,
             0,
             0,
             5 * 10**17,
             0,
             0,
             0],
            wstaking
        ),
        {'from': alice}
    )

    curABal = dpi.balanceOf(alice)
    curBBal = weth.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = dpi.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    # close the position
    homora.execute(
        position_id - 1,
        uniswap_spell,
        uniswap_spell.removeLiquidityWStakingRewards.encode_input(
            dpi,
            weth,
            [2**256-1,
             0,
             0,
             2**256-1,
             0,
             0,
             0],
            wstaking
        ),
        {'from': alice}
    )

    curABal = dpi.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(dpi)
    tokenBPrice = oracle.getETHPx(weth)
    tokenETHPrice = oracle.getETHPx('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta ETH Bal', curETHBal - prevETHBal)

    print('token A price', tokenAPrice)
    print('token B price', tokenBPrice)
    print('token ETH price', tokenETHPrice)

    print('index reward', index.balanceOf(alice))

    assert almostEqual(tokenAPrice * initABal + tokenBPrice * initBBal + tokenETHPrice * initETHBal,
                       tokenAPrice * finalABal + tokenBPrice * finalBBal + tokenETHPrice * finalETHBal), 'too much value lost'

    assert index.balanceOf(alice) > 0, 'should get some INDEX reward'


def test_sushiswap_spell(sushiswap_spell, homora, oracle, token0, token1):
    alice = accounts[0]

    token0 = interface.IERC20Ex(token0)
    token1 = interface.IERC20Ex(token1)

    mint_tokens(token0, alice)
    mint_tokens(token1, alice)

    token0.approve(homora, 0, {'from': alice})
    token1.approve(homora, 0, {'from': alice})
    token0.approve(homora, 2**256-1, {'from': alice})
    token1.approve(homora, 2**256-1, {'from': alice})

    prevABal = token0.balanceOf(alice)
    prevBBal = token1.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    token0_borrow_amt = 1 * 10**token0.decimals() if homora.banks(token0)[0] else 0
    token1_borrow_amt = 1 * 10**token1.decimals() if homora.banks(token1)[0] else 0

    homora.execute(
        0,
        sushiswap_spell,
        sushiswap_spell.addLiquidityWERC20.encode_input(
            token0,  # token 0
            token1,  # token 1
            [10 * 10**token0.decimals(),  # supply token0
             10 * 10**token1.decimals(),   # supply token1
             0,  # supply LP
             token0_borrow_amt,  # borrow token0
             token1_borrow_amt,  # borrow token1
             0,  # borrow LP tokens
             0,  # min token0
             0],  # min token1
        ),
        {'from': alice}
    )

    curABal = token0.balanceOf(alice)
    curBBal = token1.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = token0.balanceOf(alice)
    prevBBal = token1.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    token0_repay_amt = 2**256-1 if homora.banks(token0)[0] else 0
    token1_repay_amt = 2**256-1 if homora.banks(token1)[0] else 0

    homora.execute(
        position_id - 1,
        sushiswap_spell,
        sushiswap_spell.removeLiquidityWERC20.encode_input(
            token0,  # token 0
            token1,  # token 1
            [2**256-1,  # take out LP tokens
             0,   # withdraw LP tokens to wallet
             token0_repay_amt,  # repay token0
             token1_repay_amt,   # repay token1
             0,   # repay LP
             0,   # min token0
             0],  # min token1
        ),
        {'from': alice}
    )

    curABal = token0.balanceOf(alice)
    curBBal = token1.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(token0)
    tokenBPrice = oracle.getETHPx(token1)
    tokenETHPrice = oracle.getETHPx('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta ETH Bal', curETHBal - prevETHBal)

    print('token A price', tokenAPrice)
    print('token B price', tokenBPrice)
    print('token ETH price', tokenETHPrice)

    assert almostEqual(tokenAPrice * initABal + tokenBPrice * initBBal + tokenETHPrice * initETHBal,
                       tokenAPrice * finalABal + tokenBPrice * finalBBal + tokenETHPrice * finalETHBal), 'too much value lost'


def test_sushiswap_spell_wmasterchef(sushiswap_spell, homora, oracle, token0, token1, pid):

    alice = accounts[0]

    token0 = interface.IERC20Ex(token0)
    token1 = interface.IERC20Ex(token1)

    mint_tokens(token0, alice)
    mint_tokens(token1, alice)

    sushi = interface.IERC20Ex('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2')

    token0.approve(homora, 0, {'from': alice})
    token1.approve(homora, 0, {'from': alice})
    token0.approve(homora, 2**256-1, {'from': alice})
    token1.approve(homora, 2**256-1, {'from': alice})

    prevABal = token0.balanceOf(alice)
    prevBBal = token1.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    token0_borrow_amt = 1 * 10**token0.decimals() if homora.banks(token0)[0] else 0
    token1_borrow_amt = 1 * 10**token1.decimals() if homora.banks(token1)[0] else 0

    homora.execute(
        0,
        sushiswap_spell,
        sushiswap_spell.addLiquidityWMasterChef.encode_input(
            token0,  # token 0
            token1,  # token 1
            [10 * 10**token0.decimals(),  # supply token0
             10 * 10**token1.decimals(),   # supply token1
             0,  # supply LP
             token0_borrow_amt,  # borrow token0
             token1_borrow_amt,  # borrow token1
             0,  # borrow LP tokens
             0,  # min token0
             0],  # min token1
            pid
        ),
        {'from': alice}
    )

    curABal = token0.balanceOf(alice)
    curBBal = token1.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = token0.balanceOf(alice)
    prevBBal = token1.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    token0_repay_amt = 2**256-1 if homora.banks(token0)[0] else 0
    token1_repay_amt = 2**256-1 if homora.banks(token1)[0] else 0

    homora.execute(
        position_id - 1,
        sushiswap_spell,
        sushiswap_spell.removeLiquidityWMasterChef.encode_input(
            token0,  # token 0
            token1,  # token 1
            [2**256-1,  # take out LP tokens
             0,   # withdraw LP tokens to wallet
             token0_repay_amt,  # repay token0
             token1_repay_amt,   # repay token1
             0,   # repay LP
             0,   # min token0
             0],  # min token1
        ),
        {'from': alice}
    )

    curABal = token0.balanceOf(alice)
    curBBal = token1.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(token0)
    tokenBPrice = oracle.getETHPx(token1)
    tokenETHPrice = oracle.getETHPx('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta ETH Bal', curETHBal - prevETHBal)

    print('token A price', tokenAPrice)
    print('token B price', tokenBPrice)
    print('token ETH price', tokenETHPrice)

    print('sushi reward', sushi.balanceOf(alice))

    assert almostEqual(tokenAPrice * initABal + tokenBPrice * initBBal + tokenETHPrice * initETHBal,
                       tokenAPrice * finalABal + tokenBPrice * finalBBal + tokenETHPrice * finalETHBal), 'too much value lost'

    assert sushi.balanceOf(alice) > 0, 'should get some sushi reward'


def test_balancer_spell(balancer_spell, homora, oracle):
    alice = accounts[0]

    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    lp = interface.IERC20Ex('0x8b6e6e7b5b3801fed2cafd4b22b8a16c2f2db21a')

    mint_tokens(dai, alice)
    mint_tokens(weth, alice)

    dai.approve(homora, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})

    prevABal = dai.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    tx = homora.execute(
        0,
        balancer_spell,
        balancer_spell.addLiquidityWERC20.encode_input(
            lp,  # lp token
            [10 * 10**18,  # supply DAI
             10 * 10**18,   # supply WETH
             0,  # supply LP
             1 * 10**18,  # borrow DAI
             1 * 10**18,  # borrow WETH
             0,  # borrow LP tokens
             0]  # LP desired
        ),
        {'from': alice}
    )

    curABal = dai.balanceOf(alice)
    curBBal = weth.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = dai.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    tx = homora.execute(
        position_id - 1,
        balancer_spell,
        balancer_spell.removeLiquidityWERC20.encode_input(
            lp,  # LP token
            [2**256-1,  # take out LP tokens
             0,   # withdraw LP tokens to wallet
             2**256-1,  # repay DAI
             2**256-1,   # repay WETH
             0,   # repay LP
             0,   # min DAI
             0],  # min WETH
        ),
        {'from': alice}
    )

    curABal = dai.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(dai)
    tokenBPrice = oracle.getETHPx(weth)
    tokenETHPrice = oracle.getETHPx('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta ETH Bal', curETHBal - prevETHBal)

    print('token A price', tokenAPrice)
    print('token B price', tokenBPrice)
    print('token ETH price', tokenETHPrice)

    assert almostEqual(tokenAPrice * initABal + tokenBPrice * initBBal + tokenETHPrice * initETHBal,
                       tokenAPrice * finalABal + tokenBPrice * finalBBal + tokenETHPrice * finalETHBal), 'too much value lost'


def test_balancer_spell_wstaking(balancer_spell, homora, wstaking, oracle):
    alice = accounts[0]

    perp = interface.IERC20Ex('0xbC396689893D065F41bc2C6EcbeE5e0085233447')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')

    lp = interface.IERC20Ex('0xf54025af2dc86809be1153c1f20d77adb7e8ecf4')

    mint_tokens(perp, alice)
    mint_tokens(usdc, alice)

    perp.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})

    prevABal = perp.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    tx = homora.execute(
        0,
        balancer_spell,
        balancer_spell.addLiquidityWStakingRewards.encode_input(
            lp,  # lp token
            [10**18,  # supply PERP
             2 * 10**6,   # supply USDC
             0,  # supply LP
             0,  # borrow PERP
             0,  # borrow USDC
             0,  # borrow LP tokens
             0],  # LP desired
            wstaking,
        ),
        {'from': alice}
    )

    curABal = perp.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = perp.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    tx = homora.execute(
        position_id - 1,
        balancer_spell,
        balancer_spell.removeLiquidityWStakingRewards.encode_input(
            lp,  # LP token
            [2**256-1,  # take out LP tokens
             0,   # withdraw LP tokens to wallet
             0,  # repay PERP
             0,   # repay USDC
             0,   # repay LP
             0,   # min PERP
             0],  # min USDC
            wstaking,
        ),
        {'from': alice}
    )

    curABal = perp.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(perp)
    tokenBPrice = oracle.getETHPx(usdc)
    tokenETHPrice = oracle.getETHPx('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta ETH Bal', curETHBal - prevETHBal)

    print('token A price', tokenAPrice)
    print('token B price', tokenBPrice)
    print('token ETH price', tokenETHPrice)

    assert almostEqual(tokenAPrice * initABal + tokenBPrice * initBBal + tokenETHPrice * initETHBal,
                       tokenAPrice * finalABal + tokenBPrice * finalBBal + tokenETHPrice * finalETHBal), 'too much value lost'


def test_curve_spell_wgauge(curve_spell, homora, oracle):
    alice = accounts[0]

    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')

    lp = interface.IERC20Ex('0x6c3f90f043a72fa612cbac8115ee7e52bde6e490')

    mint_tokens(dai, alice)
    mint_tokens(usdc, alice)
    mint_tokens(usdt, alice)

    dai.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(homora, 0, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})

    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevCBal = usdt.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initCBal = prevCBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)
    print('prev C bal', prevCBal)

    tx = homora.execute(
        0,
        curve_spell,
        curve_spell.addLiquidity3.encode_input(
            lp,  # LP
            [10**18, 10**6, 10**6],  # supply tokens
            0,  # supply LP
            [10**18, 10**6, 10**6],  # borrow tokens
            0,  # borrow LP
            0,  # min LP mint
            0,  # pid
            0  # gid
        ),
        {'from': alice}
    )

    curABal = dai.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curCBal = usdt.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta C Bal', curCBal - prevCBal)

    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    tx = homora.execute(
        position_id - 1,
        curve_spell,
        curve_spell.removeLiquidity3.encode_input(
            lp,  # LP token
            2**256-1,  # LP amount to take out
            0,  # LP amount to withdraw to wallet
            [2**256-1, 2**256-1, 2**256-1],  # repay amounts
            0,  # repay LP amount
            [0, 0, 0]  # min amounts
        ),
        {'from': alice}
    )

    curABal = dai.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curCBal = usdt.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalCBal = curCBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(dai)
    tokenBPrice = oracle.getETHPx(usdc)
    tokenCPrice = oracle.getETHPx(usdt)
    tokenETHPrice = oracle.getETHPx('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)
    print('alice delta C Bal', curCBal - prevCBal)
    print('alice delta ETH Bal', curETHBal - prevETHBal)

    print('token A price', tokenAPrice)
    print('token B price', tokenBPrice)
    print('token C price', tokenCPrice)
    print('token ETH price', tokenETHPrice)

    assert almostEqual(tokenAPrice * initABal + tokenBPrice * initBBal + tokenCPrice * initCBal + tokenETHPrice * initETHBal,
                       tokenAPrice * finalABal + tokenBPrice * finalBBal + tokenCPrice * finalCBal + tokenETHPrice * finalETHBal), 'too much value lost'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    werc20 = WERC20.at('0xe28D9dF7718b0b5Ba69E01073fE82254a9eD2F98')
    wmas = WMasterChef.at('0x373ae78a14577682591E088F2E78EF1417612c68')
    wliq = WLiquidityGauge.at('0xfdB4f97953150e47C8606758C13e70b5a789a7ec')
    wsindex = WStakingRewards.at('0x713df2DDDA9C7d7bDa98A9f8fCd82c06c50fbd90')
    wsperp = WStakingRewards.at('0xC4635854480ffF80F742645da0310e9e59795c63')

    uni_kp3r_oracle = ERC20KP3ROracle.at('0x8E2A3777AB22e1c5f6d1fF2BcC6C4aA6aB1DeA14')
    sushi_kp3r_oracle = ERC20KP3ROracle.at('0xC331687FD71bb1D7f2e237091F8888dDcaD50C9a')
    core_oracle = CoreOracle.at('0x1E5BDdd0cDF8839d6b27b34927869eF0AD7bf692')
    uni_oracle = UniswapV2Oracle.at('0x910aD02D355c2966e8dD8E32C890cD50DB29C3B9')
    bal_oracle = BalancerPairOracle.at('0x8F93B0AA2643bf74ab38d6a5910fA82D2da02134')
    crv_oracle = CurveOracle.at('0x04DE0E42B3b0483248deafE86C4F5428613b76Ff')
    proxy_oracle = ProxyOracle.at('0x43c425fB2b00a991A51b18c217D749E393bF1AB2')

    # pair token with oracle
    from .tokens import Tokens

    # re-set oracles
    oracle_params = [
        # lp tokens
        [Tokens.bal_dai_weth, [12616, 7927, 10250]],
    ]

    token_list_2, param_list = zip(*oracle_params)

    proxy_oracle.setOracles(token_list_2, param_list, {'from': deployer})

    print('DONE')

    ###########################################################
    # test spells (UNCOMMENT TO TEST)

    # for token in [Tokens.weth, Tokens.dai, Tokens.usdc, Tokens.usdt, Tokens.dpi, Tokens.yfi, Tokens.snx, Tokens.susd]:
    #     token = interface.IERC20Ex(token)
    #     deposit_safebox(token)

    # bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    # uniswap_spell = UniswapV2SpellV1.at('0xc671B7251a789de0835a2fa33c83c8D4afB39092')
    # sushiswap_spell = SushiswapSpellV1.at('0x21Fa95485f4571A3a0d0c396561cF4D8D13D445d')
    # balancer_spell = BalancerSpellV1.at('0x15B79c184A6a8E19a4CA1F637081270343E4D15D')
    # curve_spell = CurveSpellV1.at('0x42C750024E02816eE32EB2eB4DA79ff5BF343D30')

    # test_uniswap_spell(uniswap_spell, bank, core_oracle, Tokens.weth, Tokens.dpi)
    # test_uniswap_spell(uniswap_spell, bank, core_oracle, Tokens.weth, Tokens.yfi)
    # test_uniswap_spell(uniswap_spell, bank, core_oracle, Tokens.weth, Tokens.snx)
    # test_uniswap_spell(uniswap_spell, bank, core_oracle, Tokens.weth, Tokens.susd)
    # test_uniswap_spell(uniswap_spell, bank, core_oracle, Tokens.weth, Tokens.uni)

    # test_uniswap_spell_wstaking(uniswap_spell, bank, wsindex, core_oracle)

    # test_sushiswap_spell(sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.dpi)
    # test_sushiswap_spell(sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.yfi)
    # test_sushiswap_spell(sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.snx)
    # test_sushiswap_spell(sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.susd)
    # test_sushiswap_spell(sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.sushi)

    # test_sushiswap_spell_wmasterchef(
    #     sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.dpi, 42)
    # test_sushiswap_spell_wmasterchef(
    #     sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.yfi, 11)
    # test_sushiswap_spell_wmasterchef(sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.snx, 6)
    # test_sushiswap_spell_wmasterchef(
    #     sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.susd, 3)
    # test_sushiswap_spell_wmasterchef(
    #     sushiswap_spell, bank, core_oracle, Tokens.weth, Tokens.sushi, 12)

    # test_balancer_spell_wstaking(balancer_spell, bank, wsperp, core_oracle)
    # test_curve_spell_wgauge(curve_spell, bank, core_oracle)
