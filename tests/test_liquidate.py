import pytest
from brownie import interface
import brownie
from utils import *


def setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain, UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle):
    spell = UniswapV2SpellV1.deploy(bank, werc20, urouter, {'from': admin})
    usdc.mint(admin, 10000000 * 10**6, {'from': admin})
    usdt.mint(admin, 10000000 * 10**6, {'from': admin})
    usdc.approve(urouter, 2**256-1, {'from': admin})
    usdt.approve(urouter, 2**256-1, {'from': admin})
    urouter.addLiquidity(
        usdc,
        usdt,
        1000000 * 10**6,
        1000000 * 10**6,
        0,
        0,
        admin,
        chain.time() + 60,
        {'from': admin},
    )

    lp = ufactory.getPair(usdc, usdt)
    print('admin lp bal', interface.IERC20(lp).balanceOf(admin))
    uniswap_lp_oracle = UniswapV2Oracle.deploy(simple_oracle, {'from': admin})

    print('usdt Px', simple_oracle.getETHPx(usdt))
    print('usdc Px', simple_oracle.getETHPx(usdc))

    core_oracle.setRoute([usdc, usdt, lp], [simple_oracle, simple_oracle, uniswap_lp_oracle])
    print('lp Px', uniswap_lp_oracle.getETHPx(lp))
    oracle.setOracles(
        [usdc, usdt, lp],
        [
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
        ],
        {'from': admin},
    )
    usdc.mint(alice, 10000000 * 10**6, {'from': admin})
    usdt.mint(alice, 10000000 * 10**6, {'from': admin})
    usdc.approve(bank, 2**256-1, {'from': alice})
    usdt.approve(bank, 2**256-1, {'from': alice})

    return spell


def execute_uniswap_werc20(admin, alice, bank, token0, token1, spell, pos_id=0):
    spell.getPair(token0, token1, {'from': admin})
    tx = bank.execute(
        pos_id,
        spell,
        spell.addLiquidityWERC20.encode_input(
            token0,  # token 0
            token1,  # token 1
            [
                10 * 10**6,  # 10 USDC
                2 * 10**6,  # 2 USDT
                0,
                1000 * 10**6,  # 1000 USDC
                200 * 10**6,  # 200 USDT
                0,  # borrow LP tokens
                0,  # min USDC
                0,  # min USDT
            ],
        ),
        {'from': alice}
    )


def setup_bob(admin, bob, bank, usdt, usdc):
    usdt.mint(bob, 10000 * 10**6, {'from': admin})
    usdt.approve(bank, 2**256-1, {'from': bob})
    usdc.mint(bob, 10000 * 10**6, {'from': admin})
    usdc.approve(bank, 2**256-1, {'from': bob})


def test_liquidate(admin, alice, bob, bank, chain, werc20, ufactory, urouter, simple_oracle, oracle, usdc, usdt, UniswapV2SpellV1, UniswapV2Oracle, core_oracle):
    setup_bob(admin, bob, bank, usdt, usdc)

    # execute
    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle)
    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=0)

    pos_id = 1

    print('collateral value', bank.getCollateralETHValue(pos_id))
    print('borrow value', bank.getBorrowETHValue(pos_id))

    # bob tries to liquidate
    with brownie.reverts('position still healthy'):
        bank.liquidate(pos_id, usdt, 10 * 10**18, {'from': bob})

    # change oracle settings
    lp = ufactory.getPair(usdc, usdt)
    uniswap_lp_oracle = UniswapV2Oracle.deploy(simple_oracle, {'from': admin})
    oracle.setOracles(
        [lp],
        [
            [10000, 9900, 10500],
        ],
        {'from': admin},
    )

    print('collateral value', bank.getCollateralETHValue(pos_id))
    print('borrow value', bank.getBorrowETHValue(pos_id))

    # ready to be liquidated
    bank.liquidate(pos_id, usdt, 100 * 10**6, {'from': bob})
    print('bob lp', werc20.balanceOfERC20(lp, bob))
    print('calc bob lp', 100 * 10**6 * simple_oracle.getETHPx(usdt) //
          uniswap_lp_oracle.getETHPx(lp) * 105 // 100)
    assert almostEqual(werc20.balanceOfERC20(lp, bob), 100 * 10**6 *
                       simple_oracle.getETHPx(usdt) // uniswap_lp_oracle.getETHPx(lp) * 105 // 100)

    print('collateral value', bank.getCollateralETHValue(pos_id))
    print('borrow value', bank.getBorrowETHValue(pos_id))

    oracle.setOracles(
        [usdt, usdc],
        [
            [10700, 10000, 10300],
            [10200, 10000, 10100],
        ],
        {'from': admin},
    )

    print('collateral value', bank.getCollateralETHValue(pos_id))
    print('borrow value', bank.getBorrowETHValue(pos_id))

    # liquidate 300 USDC

    prevBobBal = werc20.balanceOfERC20(lp, bob)
    bank.liquidate(pos_id, usdc, 300 * 10**6, {'from': bob})
    curBobBal = werc20.balanceOfERC20(lp, bob)
    print('delta bob lp', curBobBal - prevBobBal)
    print('calc delta bob lp', 300 * 10**6 * simple_oracle.getETHPx(usdc) //
          uniswap_lp_oracle.getETHPx(lp) * 105 * 101 // 100 // 100)
    assert almostEqual(curBobBal - prevBobBal, 300 * 10**6 * simple_oracle.getETHPx(usdc) //
                       uniswap_lp_oracle.getETHPx(lp) * 105 * 101 // 100 // 100)

    # change usdc price
    simple_oracle.setETHPx([usdc], [2**112 * 10**12 // 500])

    print('collateral value', bank.getCollateralETHValue(pos_id))
    print('borrow value', bank.getBorrowETHValue(pos_id))

    # liquidate max USDC (remaining 700)
    prevBobBal = werc20.balanceOfERC20(lp, bob)
    _, _, _, stCollSize = bank.getPositionInfo(pos_id)
    bank.liquidate(pos_id, usdc, 2**256-1, {'from': bob})
    curBobBal = werc20.balanceOfERC20(lp, bob)
    _, _, _, enCollSize = bank.getPositionInfo(pos_id)
    print('delta bob lp', curBobBal - prevBobBal)
    print('calc delta bob lp', stCollSize - enCollSize)
    assert almostEqual(curBobBal - prevBobBal, stCollSize - enCollSize)

    # try to liquidate more than available
    with brownie.reverts():
        bank.liquidate(pos_id, usdt, 101 * 10**6, {'from': bob})

    # liquidate 100 USDT (remaining 100)
    prevBobBal = werc20.balanceOfERC20(lp, bob)
    bank.liquidate(pos_id, usdt, 100 * 10**6, {'from': bob})
    curBobBal = werc20.balanceOfERC20(lp, bob)
    print('delta bob lp', curBobBal - prevBobBal)
    assert almostEqual(curBobBal - prevBobBal, 0)
