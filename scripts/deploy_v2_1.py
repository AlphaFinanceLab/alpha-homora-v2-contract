from brownie import (
    accounts, ERC20KP3ROracle, UniswapV2Oracle, BalancerPairOracle, ProxyOracle, CoreOracle,
    HomoraBank, CurveOracle, UniswapV2SpellV1, WERC20, WLiquidityGauge, WMasterChef,
    WStakingRewards, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1,
)
from brownie import interface
from .utils import *


KP3R_NETWORK = '0x73353801921417F465377c8d898c6f4C0270282C'
CRV_REGISTRY = '0x7D86446dDb609eD0F5f8684AcF30380a356b2B4c'
CRV_TOKEN = '0xD533a949740bb3306d119CC777fa900bA034cd52'
MASTERCHEF = '0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd'
BANK = '0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb'


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def test_uniswap_spell(uniswap_spell, homora, oracle):
    alice = accounts[0]

    yfi = interface.IERC20Ex('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    mint_tokens(yfi, alice)
    mint_tokens(weth, alice)

    yfi.approve(homora, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})

    prevABal = yfi.balanceOf(alice)
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
        uniswap_spell.addLiquidityWERC20.encode_input(
            yfi,
            weth,
            [10 * 10**18,
             10 * 10**18,
             0,
             0,
             10**18,
             0,
             0,
             0],
        ),
        {'from': alice}
    )

    curABal = yfi.balanceOf(alice)
    curBBal = weth.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = yfi.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    # close the position
    homora.execute(
        position_id - 1,
        uniswap_spell,
        uniswap_spell.removeLiquidityWERC20.encode_input(
            yfi,
            weth,
            [2**256-1,
             0,
             0,
             2**256-1,
             0,
             0,
             0],
        ),
        {'from': alice}
    )

    curABal = yfi.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(yfi)
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


def test_sushiswap_spell(sushiswap_spell, homora, oracle):
    alice = accounts[0]

    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    mint_tokens(usdt, alice)
    mint_tokens(weth, alice)

    usdt.approve(homora, 0, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    homora.execute(
        0,
        sushiswap_spell,
        sushiswap_spell.addLiquidityWERC20.encode_input(
            usdt,  # token 0
            weth,  # token 1
            [10 * 10**6,  # supply USDT
             10 * 10**18,   # supply WETH
             0,  # supply LP
             0,  # borrow USDT
             10**18,  # borrow WETH
             0,  # borrow LP tokens
             0,  # min USDT
             0],  # min WETH
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    homora.execute(
        position_id - 1,
        sushiswap_spell,
        sushiswap_spell.removeLiquidityWERC20.encode_input(
            usdt,  # token 0
            weth,  # token 1
            [2**256-1,  # take out LP tokens
             0,   # withdraw LP tokens to wallet
             0,  # repay USDT
             2**256-1,   # repay WETH
             0,   # repay LP
             0,   # min USDT
             0],  # min WETH
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(usdt)
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


def test_sushiswap_spell_wmasterchef(sushiswap_spell, homora, oracle):
    alice = accounts[0]

    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    sushi = interface.IERC20Ex('0x6b3595068778dd592e39a122f4f5a5cf09c90fe2')

    mint_tokens(usdt, alice)
    mint_tokens(weth, alice)

    usdt.approve(homora, 0, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    initABal = prevABal
    initBBal = prevBBal
    initETHBal = prevETHBal

    print('prev A bal', prevABal)
    print('prev B bal', prevBBal)

    homora.execute(
        0,
        sushiswap_spell,
        sushiswap_spell.addLiquidityWMasterChef.encode_input(
            usdt,  # token 0
            weth,  # token 1
            [10 * 10**6,  # supply USDT
             10 * 10**18,   # supply WETH
             0,  # supply LP
             0,  # borrow USDT
             10**18,  # borrow WETH
             0,  # borrow LP tokens
             0,  # min USDT
             0],  # min WETH
            0
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)

    print('alice delta A Bal', curABal - prevABal)
    print('alice delta B Bal', curBBal - prevBBal)

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevETHBal = alice.balance()

    position_id = homora.nextPositionId()

    homora.execute(
        position_id - 1,
        sushiswap_spell,
        sushiswap_spell.removeLiquidityWMasterChef.encode_input(
            usdt,  # token 0
            weth,  # token 1
            [2**256-1,  # take out LP tokens
             0,   # withdraw LP tokens to wallet
             0,  # repay USDT
             2**256-1,   # repay WETH
             0,   # repay LP
             0,   # min USDT
             0],  # min WETH
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curETHBal = alice.balance()

    finalABal = curABal
    finalBBal = curBBal
    finalETHBal = curETHBal

    tokenAPrice = oracle.getETHPx(usdt)
    tokenBPrice = oracle.getETHPx(weth)
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
            [10**18, 0, 0],  # borrow tokens
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
            [2**256-1, 0, 0],  # repay amounts
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

    kp3r_oracle = ERC20KP3ROracle.at('0x8E2A3777AB22e1c5f6d1fF2BcC6C4aA6aB1DeA14')
    core_oracle = CoreOracle.at('0x1E5BDdd0cDF8839d6b27b34927869eF0AD7bf692')
    uni_oracle = UniswapV2Oracle.deploy(core_oracle, {'from': deployer})
    bal_oracle = BalancerPairOracle.at('0x8F93B0AA2643bf74ab38d6a5910fA82D2da02134')
    crv_oracle = CurveOracle.at('0x04DE0E42B3b0483248deafE86C4F5428613b76Ff')
    proxy_oracle = ProxyOracle.deploy(core_oracle, {'from': deployer})
    # re-route to new uniswap oracle
    core_oracle.setRoute([
        '0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e',  # YFI
        '0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11',  # UNI DAI-WETH
        '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # UNI WETH-USDT
        '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',  # UNI USDC-WETH
        '0xBb2b8038a1640196FbE3e38816F3e67Cba72D940',  # UNI WBTC-WETH
        '0x2fDbAdf3C4D5A8666Bc06645B8358ab803996E28',  # UNI WETH-YFI
        '0x4d5ef58aAc27d99935E5b6B4A6778ff292059991',  # UNI DPI-WETH
        '0x06da0fd433C1A5d7a4faa01111c044910A184553',  # SUSHI WETH-USDT
        '0x088ee5007C98a9677165D78dD2109AE4a3D04d0C',  # SUSHI WETH-YFI
        '0x34b13F8CD184F55d0Bd4Dd1fe6C07D46f245c7eD',  # SUSHI DPI-WETH
    ], [
        kp3r_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
    ], {'from': deployer})

    # re-set oracles
    proxy_oracle.setOracles([
        '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
        '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC
        '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
        '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',  # WBTC
        '0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b',  # DPI
        '0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e',  # YFI
        '0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11',  # UNI DAI-WETH
        '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # UNI WETH-USDT
        '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',  # UNI USDC-WETH
        '0xBb2b8038a1640196FbE3e38816F3e67Cba72D940',  # UNI WBTC-WETH
        '0x2fDbAdf3C4D5A8666Bc06645B8358ab803996E28',  # UNI WETH-YFI
        '0x4d5ef58aAc27d99935E5b6B4A6778ff292059991',  # UNI DPI-WETH
        '0x06da0fd433C1A5d7a4faa01111c044910A184553',  # SUSHI WETH-USDT
        '0x088ee5007C98a9677165D78dD2109AE4a3D04d0C',  # SUSHI WETH-YFI
        '0x34b13F8CD184F55d0Bd4Dd1fe6C07D46f245c7eD',  # SUSHI DPI-WETH
        '0x8b6e6E7B5b3801FEd2CaFD4b22b8A16c2F2Db21a',  # BAL WETH-DAI 80-20
        '0xF54025aF2dc86809Be1153c1F20D77ADB7e8ecF4',  # BAL PERP-USDC 80-20
        '0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490',  # CRV 3-POOL
    ], [
        [14350, 6970, 10250],  # WETH
        [10840, 9230, 10250],  # DAI
        [10840, 9230, 10250],  # USDC
        [10840, 9230, 10250],  # USDT
        [14350, 6970, 10250],  # WBTC
        [50000, 0, 10250],  # DPI
        [50000, 0, 10250],  # YFI
        [50000, 6970, 10250],  # UNI DAI-WETH
        [50000, 6970, 10250],  # UNI WETH-USDT
        [50000, 6970, 10250],  # UNI USDC-WETH
        [50000, 6970, 10250],  # UNI WBTC-WETH
        [50000, 6970, 10250],  # UNI WETH-YFI
        [50000, 6970, 10250],  # UNI DPI-WETH
        [50000, 6970, 10250],  # SUSHI WETH-USDT
        [50000, 6970, 10250],  # SUSHI WETH-YFI
        [50000, 6970, 10250],  # SUSHI DPI-WETH
        [50000, 6970, 10250],  # BAL WETH-DAI 80-20
        [50000, 0, 10250],  # BAL PERP-USDC 80-20
        [50000, 9230, 10250],  # CRV 3-POOL
    ], {'from': deployer})

    proxy_oracle.setWhitelistERC1155(
        [werc20, wmas, wliq, wsindex, wsperp],
        True,
        {'from': deployer},
    )

    bank_impl = HomoraBank.deploy({'from': deployer})
    proxy_admin = Contract.from_explorer('0x090eCE252cEc5998Db765073D07fac77b8e60CB2')
    bank = Contract.from_explorer('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    proxy_admin.upgrade(bank, bank_impl, {'from': deployer})

    bank.setOracle(proxy_oracle, {'from': deployer})

    uniswap_spell = UniswapV2SpellV1.deploy(
        bank, werc20, '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        {'from': deployer},
    )
    sushiswap_spell = SushiswapSpellV1.deploy(
        bank, werc20, '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F', wmas,
        {'from': deployer},
    )
    balancer_spell = BalancerSpellV1.at('0x15B79c184A6a8E19a4CA1F637081270343E4D15D')
    curve_spell = CurveSpellV1.deploy(
        bank, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', wliq,
        {'from': deployer},
    )

    print('DONE')

    ###########################################################
    # test spells (UNCOMMENT TO TEST)

    # test_uniswap_spell(uniswap_spell, bank, core_oracle)
    # test_uniswap_spell_wstaking(uniswap_spell, bank, wsindex, core_oracle)
    # test_sushiswap_spell(sushiswap_spell, bank, core_oracle)
    # test_sushiswap_spell_wmasterchef(sushiswap_spell, bank, core_oracle)
    # test_balancer_spell(balancer_spell, bank, core_oracle)
    # test_balancer_spell_wstaking(balancer_spell, bank, wsperp, core_oracle)
    # test_curve_spell_wgauge(curve_spell, bank, core_oracle)
