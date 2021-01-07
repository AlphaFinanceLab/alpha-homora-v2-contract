import pytest
from brownie import interface
import brownie
from helper_uniswap import *


def test_temporary_state(admin, alice, bank, chain, werc20, ufactory, urouter, simple_oracle, core_oracle, oracle, usdc, usdt, UniswapV2SpellV1, UniswapV2Oracle):
    _NOT_ENTERED = 1
    _ENTERED = 2
    _NO_ID = 2**256 - 1
    _NO_ADDRESS = '0x0000000000000000000000000000000000000001'

    # before execute
    assert bank._GENERAL_LOCK() == _NOT_ENTERED
    assert bank._IN_EXEC_LOCK() == _NOT_ENTERED
    assert bank.POSITION_ID() == _NO_ID
    assert bank.SPELL() == _NO_ADDRESS

    # execute
    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle)
    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=0)

    # after execute
    assert bank._GENERAL_LOCK() == _NOT_ENTERED
    assert bank._IN_EXEC_LOCK() == _NOT_ENTERED
    assert bank.POSITION_ID() == _NO_ID
    assert bank.SPELL() == _NO_ADDRESS


def test_oracle(bank, oracle):
    print("bank's oracle", bank.oracle())
    print('oracle', oracle)
    assert bank.oracle() == oracle


def test_feeBps(bank):
    assert bank.feeBps() == 2000  # initially set to 2000


def test_next_position_id(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle):
    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle)

    assert bank.nextPositionId() == 1  # initially 1
    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=0)
    assert bank.nextPositionId() == 2
    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=1)
    assert bank.nextPositionId() == 2  # doesn't increase due to changing
    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=0)
    assert bank.nextPositionId() == 3


def test_all_banks(admin, bank, token, cToken, weth, dai, usdt, usdc, MockCErc20_2):
    # from setup_basic
    assert bank.allBanks(0) == weth
    assert bank.allBanks(1) == dai
    assert bank.allBanks(2) == usdt
    assert bank.allBanks(3) == usdc

    with brownie.reverts():
        bank.allBanks(4)

    bank.addBank(token, cToken)
    assert bank.allBanks(4) == token

    with brownie.reverts('cToken already exists'):
        bank.addBank(token, cToken)

    cToken_1 = MockCErc20_2.deploy(token, {'from': admin})

    with brownie.reverts('bank already exists'):
        bank.addBank(token, cToken_1)


def test_banks(admin, bank, weth, dai, usdt, usdc, token, cToken):
    for ind, coin in enumerate([weth, dai, usdt, usdc]):
        isListed, index, cToken1, reserve, pendingReserve, totalDebt, totalShare = bank.banks(coin)
        assert isListed
        assert index == ind
        assert reserve == 0
        assert pendingReserve == 0
        assert totalDebt == 0
        assert totalShare == 0

    # token is not listed yet
    isListed, index, cToken1, reserve, pendingReserve, totalDebt, totalShare = bank.banks(token)
    assert not isListed
    assert index == 0
    assert reserve == 0
    assert pendingReserve == 0
    assert totalDebt == 0
    assert totalShare == 0

    # add bank
    bank.addBank(token, cToken)
    isListed, index, cToken1, reserve, pendingReserve, totalDebt, totalShare = bank.banks(token)
    assert isListed
    assert index == 4
    assert reserve == 0
    assert pendingReserve == 0
    assert totalDebt == 0
    assert totalShare == 0


def test_cToken_in_bank(admin, bank, weth, dai, usdt, usdc, token, cToken):
    for ind, coin in enumerate([weth, dai, usdt, usdc]):
        _, _, cToken1, _, _, _, _ = bank.banks(coin)
        assert bank.cTokenInBank(cToken1)

    assert not bank.cTokenInBank(cToken)
    bank.addBank(token, cToken)
    assert bank.cTokenInBank(cToken)


def test_positions(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                   UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle):

    # position 0 not exist
    owner, collToken, collId, collateralSize, debtMap = bank.positions(0)
    assert owner == '0x0000000000000000000000000000000000000000'
    assert collToken == '0x0000000000000000000000000000000000000000'
    assert collId == 0
    assert collateralSize == 0
    assert debtMap == 0

    # position 1 not exist
    owner, collToken, collId, collateralSize, debtMap = bank.positions(1)
    assert owner == '0x0000000000000000000000000000000000000000'
    assert collToken == '0x0000000000000000000000000000000000000000'
    assert collId == 0
    assert collateralSize == 0
    assert debtMap == 0

    # create position 1
    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, core_oracle, oracle)

    execute_uniswap_werc20(admin, alice, bank, usdc, usdt, spell, pos_id=0)

    owner, collToken, collId, collateralSize, debtMap = bank.positions(1)
    tx = spell.getPair(usdt, usdc, {'from': admin})
    lp = tx.return_value
    assert owner == alice
    assert collToken == werc20
    assert collId == int(lp, 0)  # convert address to uint
    assert collateralSize > 0
    assert debtMap == (1 << 2) + (1 << 3)  # usdt, usdc are at index 2,3
