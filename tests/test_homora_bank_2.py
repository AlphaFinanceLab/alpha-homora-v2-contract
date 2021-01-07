import pytest
from brownie import interface, chain
import brownie
from utils import *
from helper_uniswap import *


def test_reinitialize(admin, bank, oracle):
    with brownie.reverts():
        bank.initialize(oracle, 2000, {'from': admin})


def test_accrue(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle):

    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle)

    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=0)

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
                    UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle):

    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle)

    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=0)

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
