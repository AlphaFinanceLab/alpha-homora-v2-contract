import pytest
from brownie import interface
import brownie


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
        2**256-1,
        {'from': admin},
    )

    lp = ufactory.getPair(usdc, usdt)
    print('admin lp bal', interface.IERC20(lp).balanceOf(admin))
    uniswap_lp_oracle = UniswapV2Oracle.deploy(core_oracle, {'from': admin})

    print('usdt Px', simple_oracle.getETHPx(usdt))
    print('usdc Px', simple_oracle.getETHPx(usdc))

    core_oracle.setRoute([usdc, usdt, lp], [simple_oracle, simple_oracle,
                                            uniswap_lp_oracle], {'from': admin})

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
