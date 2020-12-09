import pytest


def test_uniswap_add_two_tokens(
    a, chain, bank, werc20, ufactory, urouter, simple_oracle, oracle, usdc, usdt, UniswapV2SpellV1,
):
    spell = UniswapV2SpellV1.deploy(bank, werc20, urouter, {'from': a[0]})
    usdc.mint(a[0], 10000000 * 10**6, {'from': a[0]})
    usdt.mint(a[0], 10000000 * 10**6, {'from': a[0]})
    usdc.approve(urouter, 2**256-1, {'from': a[0]})
    usdt.approve(urouter, 2**256-1, {'from': a[0]})
    urouter.addLiquidity(
        usdc,
        usdt,
        1000000 * 10**6,
        1000000 * 10**6,
        0,
        0,
        a[0],
        chain.time() + 60,
        {'from': a[0]},
    )
    lp = ufactory.getPair(usdc, usdt)
    simple_oracle.setETHPx(
        [lp],
        [10**50],  # Way too much!
    )
    oracle.setOracles(
        [usdc, usdt, lp],
        [
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
        ],
        {'from': a[0]},
    )
    usdc.mint(a[1], 10000000 * 10**6, {'from': a[0]})
    usdt.mint(a[1], 10000000 * 10**6, {'from': a[0]})
    usdc.approve(bank, 2**256-1, {'from': a[1]})
    usdt.approve(bank, 2**256-1, {'from': a[1]})
    spell.getPair(usdc, usdt, {'from': a[0]})
    tx = bank.execute(
        0,
        spell,
        spell.addLiquidity.encode_input(
            usdt,  # token 0
            usdc,  # token 1
            [
                40000 * 10**6,  # 40000 USDT
                50000 * 10**6,  # 50000 USDC
                0,
                1000 * 10**6,  # 1000 USDT
                200 * 10**6,  # 200 USDC
                0,  # borrow LP tokens
                0,  # min USDT
                0,
            ],  # min USDC
        ),
        {'from': a[1]}
    )
    assert 900000 <= tx.gas_used <= 1000000
