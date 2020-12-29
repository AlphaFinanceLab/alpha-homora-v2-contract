import pytest
from brownie import interface, chain
import brownie
from utils import *


def setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain, UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle):
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

    print('lp Px', uniswap_lp_oracle.getETHPx(lp))
    oracle.setOracles(
        [usdc, usdt, lp],
        [
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
            [uniswap_lp_oracle, 10000, 10000, 10000],
        ],
        {'from': admin},
    )
    usdc.mint(alice, 10000000 * 10**6, {'from': admin})
    usdt.mint(alice, 10000000 * 10**6, {'from': admin})
    usdc.approve(bank, 2**256-1, {'from': alice})
    usdt.approve(bank, 2**256-1, {'from': alice})

    return spell


def execute_uniswap(admin, alice, bank, token0, token1, spell, pos_id=0):
    spell.getPair(token0, token1, {'from': admin})
    tx = bank.execute(
        pos_id,
        spell,
        spell.addLiquidity.encode_input(
            token0,  # token 0
            token1,  # token 1
            [
                40000 * 10**6,  # 40000 USDC
                50000 * 10**6,  # 50000 USDT
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


def test_reinitialize(admin, bank, oracle):
    with brownie.reverts():
        bank.initialize(oracle, 2000, {'from': admin})


def test_accrue(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle):

    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle)

    execute_uniswap(admin, alice, bank, usdc, usdt, spell, pos_id=0)

    _, _, cusdt, _, prevPendingReserve, prevUSDTTotalDebt, prevUSDTTotalShare = bank.banks(usdt)
    print('totalDebt', prevUSDTTotalDebt)
    print('totalShare', prevUSDTTotalShare)

    chain.sleep(100000)

    # not accrue yet
    _, _, cusdt, _, curPendingReserve, curUSDTTotalDebt, curUSDTTotalShare = bank.banks(usdt)
    print('totalDebt', curUSDTTotalDebt)
    print('totalShare', curUSDTTotalShare)

    assert prevUSDTTotalDebt == curUSDTTotalDebt
    assert prevUSDTTotalShare == curUSDTTotalShare

    bank.accrue(usdt)

    _, _, cusdt, _, curPendingReserve, curUSDTTotalDebt, curUSDTTotalShare = bank.banks(usdt)
    print('totalDebt', curUSDTTotalDebt)
    print('totalShare', curUSDTTotalShare)

    assert prevUSDTTotalShare == curUSDTTotalShare

    usdt_interest = curUSDTTotalDebt - prevUSDTTotalDebt
    usdt_fee = usdt_interest * bank.feeBps() // 10000  # 20%

    assert curPendingReserve - prevPendingReserve == usdt_fee


def test_accrue_all(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                    UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle):

    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle)

    execute_uniswap(admin, alice, bank, usdc, usdt, spell, pos_id=0)

    _, _, cusdt, _, prevUSDTPendingReserve, prevUSDTTotalDebt, prevUSDTTotalShare = bank.banks(usdt)
    print('totalDebt', prevUSDTTotalDebt)
    print('totalShare', prevUSDTTotalShare)

    _, _, cusdc, _, prevUSDCPendingReserve, prevUSDCTotalDebt, prevUSDCTotalShare = bank.banks(usdc)
    print('totalDebt', prevUSDCTotalDebt)
    print('totalShare', prevUSDCTotalShare)

    chain.sleep(100000)

    # not accrue yet
    _, _, cusdt, _, curPendingReserve, curUSDTTotalDebt, curUSDTTotalShare = bank.banks(usdt)
    _, _, cusdc, _, curUSDCPendingReserve, curUSDCTotalDebt, curUSDCTotalShare = bank.banks(usdc)

    assert prevUSDTTotalDebt == curUSDTTotalDebt
    assert prevUSDTTotalShare == curUSDTTotalShare

    assert prevUSDCTotalDebt == curUSDCTotalDebt
    assert prevUSDCTotalShare == curUSDCTotalShare

    # accrue usdt, usdc
    bank.accrueAll([usdt, usdc])

    _, _, cusdt, _, curUSDTPendingReserve, curUSDTTotalDebt, curUSDTTotalShare = bank.banks(usdt)
    print('totalDebt', curUSDTTotalDebt)
    print('totalShare', curUSDTTotalShare)

    assert prevUSDTTotalShare == curUSDTTotalShare

    usdt_interest = curUSDTTotalDebt - prevUSDTTotalDebt
    usdt_fee = usdt_interest * bank.feeBps() // 10000  # 20%

    assert curUSDTPendingReserve - prevUSDTPendingReserve == usdt_fee

    assert almostEqual(usdt_interest, 200000000 * 10 // 100 * 100000 // (365*86400))

    _, _, cusdc, _, curUSDCPendingReserve, curUSDCTotalDebt, curUSDCTotalShare = bank.banks(usdc)
    print('totalDebt', curUSDCTotalDebt)
    print('totalShare', curUSDCTotalShare)

    assert prevUSDCTotalShare == curUSDCTotalShare

    usdc_interest = curUSDCTotalDebt - prevUSDCTotalDebt
    usdc_fee = usdc_interest * bank.feeBps() // 10000  # 20%

    assert curUSDCPendingReserve - prevUSDCPendingReserve == usdc_fee

    assert almostEqual(usdc_interest, 1000000000 * 10 // 100 * 100000 // (365*86400))
