import pytest
from brownie import interface


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
                40000 * 10**6,  # 40000 USDT
                50000 * 10**6,  # 50000 USDC
                0,
                1000 * 10**6,  # 1000 USDT
                200 * 10**6,  # 200 USDC
                0,  # borrow LP tokens
                0,  # min USDT
                0,  # min USDC
            ],
        ),
        {'from': alice}
    )


def test_temporary_state(admin, alice, bank, chain, werc20, ufactory, urouter, simple_oracle, oracle, usdc, usdt, UniswapV2SpellV1, UniswapV2Oracle):
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
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle)
    execute_uniswap(admin, alice, bank, usdc, usdt, spell, pos_id=0)

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
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle):
    spell = setup_uniswap(admin, alice, bank, werc20, urouter, ufactory, usdc, usdt, chain,
                          UniswapV2Oracle, UniswapV2SpellV1, simple_oracle, oracle)

    assert bank.nextPositionId() == 1  # initially 1
    execute_uniswap(admin, alice, bank, usdc, usdt, spell, pos_id=0)
    assert bank.nextPositionId() == 2
    execute_uniswap(admin, alice, bank, usdc, usdt, spell, pos_id=1)
    assert bank.nextPositionId() == 2  # doesn't increase due to changing
    execute_uniswap(admin, alice, bank, usdc, usdt, spell, pos_id=0)
    assert bank.nextPositionId() == 3
