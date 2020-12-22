import pytest
from brownie import interface


def test_uniswap_add_two_tokens(
    admin, alice, chain, bank, werc20, ufactory, urouter, simple_oracle, oracle, usdc, usdt, UniswapV2SpellV1, UniswapV2Oracle,
):
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
    spell.getPair(usdc, usdt, {'from': admin})
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
                0,  # min USDC
            ],
        ),
        {'from': alice}
    )

    position_id = tx.return_value
    print('tx gas used', tx.gas_used)
    print('bank collateral size', bank.getPositionInfo(position_id))
    print('bank collateral value', bank.getCollateralETHValue(position_id))
    print('bank borrow value', bank.getBorrowETHValue(position_id))

    print('bank usdt', bank.getBankInfo(usdt))
    print('bank usdc', bank.getBankInfo(usdc))

    print('usdt Px', simple_oracle.getETHPx(usdt))
    print('usdc Px', simple_oracle.getETHPx(usdc))

    print('lp Px', uniswap_lp_oracle.getETHPx(lp))
