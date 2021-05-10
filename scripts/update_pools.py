from brownie import interface, accounts
from brownie import (CoreOracle, UniswapV2Oracle, BalancerPairOracle, CurveOracle, ProxyOracle,
                     UniswapV2SpellV1, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1,)
from .utils import *
from .tokens import Tokens

from brownie.network.gas.strategies import GasNowScalingStrategy
from brownie import network

gas_strategy = GasNowScalingStrategy(
    initial_speed="fast", max_speed="fast", increment=1.085, block_duration=20)

# set gas price
network.gas_price(gas_strategy)


def fake_credit_limit(bank):
    comptroller = interface.IAny('0xab1c342c7bf5ec5f02adea1c2270670bca144cbb')
    comptroller_admin = comptroller.admin()
    accounts[9].transfer(comptroller_admin, '10 ether')
    comptroller._setCreditLimit(bank, 2**256-1, {'from': comptroller_admin, 'gas_price': gas_strategy})


def main():
    #######################################################################
    # Load deployer account

    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    #######################################################################
    # Deploy upgradeable homora bank
    print('================================================================')
    print('Deploying Homora Bank...')
    bank = interface.IAny('0xba5eBAf3fc1Fcca67147050Bf80462393814E54B')

    #######################################################################
    # Deploy spells
    print('================================================================')
    print('Deploying Spells...')
    uniswap_spell = UniswapV2SpellV1.at('0x7b1f4cDD4f599774feae6516460BCCD97Fc2100E')
    sushiswap_spell = SushiswapSpellV1.at('0xc4a59cfEd3FE06bDB5C21dE75A70B20dB280D8fE')
    balancer_spell = BalancerSpellV1.at('0x6b8079Bf80E07fB103a55E49EE226f729E1e38D5')
    curve_spell = CurveSpellV1.at('0x8b947D8448CFFb89EF07A6922b74fBAbac219795')

    #######################################################################
    # Set oracle routes for lp tokens
    print('================================================================')
    print('Setting oracle routes for LP tokens...')
    uni_oracle = UniswapV2Oracle.at('0x7678eB6251f41FBF4e0DF36c90bfE32843C2dAf9')
    core_oracle = CoreOracle.at('0x6be987c6d72e25F02f6f061F94417d83a6Aa13fC')

    core_oracle_configs = [
        (Tokens.UNI_USDC_USDT, uni_oracle),
        (Tokens.UNI_DAI_USDC, uni_oracle),
    ]

    core_oracle_tokens, core_oracle_base_oracles = zip(*core_oracle_configs)

    core_oracle.setRoute(core_oracle_tokens, core_oracle_base_oracles, {'from': deployer, 'gas_price': gas_strategy})
    #######################################################################
    # Set oracle token factors
    # NOTE: base tokens should have 0 collateral factors
    # NOTE: LP tokens should have 50000 borrow factors
    print('================================================================')
    print('Setting oracle token factors...')

    proxy_oracle = ProxyOracle.at('0x914C687FFdAB6E1B47a327E7E4C10e4a058e009d')

    token_factors = [
        (Tokens.UNI_USDC_USDT, [50000, 9502, 10250]),
        (Tokens.UNI_DAI_USDC, [50000, 9502, 10250]),
    ]

    proxy_oracle_tokens, proxy_oracle_configs = zip(*token_factors)

    proxy_oracle.setTokenFactors(proxy_oracle_tokens, proxy_oracle_configs, {'from': deployer, 'gas_price': gas_strategy})

    # unset Uniswap SUSD-WETH
    proxy_oracle.unsetTokenFactors([Tokens.UNI_SUSD_WETH], {'from': deployer})

    #######################################################################
    # Set whitelist LP tokens for spells
    print('================================================================')
    print('Update whitelisting LP tokens for uniswap spells...')

    uniswap_whitelist_lp_tokens = [
        Tokens.UNI_SUSD_WETH,  # FALSE
        Tokens.UNI_USDC_USDT,
        Tokens.UNI_DAI_USDC,
    ]

    uniswap_spell.setWhitelistLPTokens(uniswap_whitelist_lp_tokens, [False, True, True], {'from': deployer, 'gas_price': gas_strategy})

    # #######################################################################
    # # Open positions in each pool
    # print('================================================================')
    # print('Opening positions...')

    # # fake_credit_limit(bank)  # for testing only. TODO: remove

    # borrowable_tokens = [
    #     Tokens.WETH,
    #     Tokens.DAI,
    #     Tokens.LINK,
    #     Tokens.YFI,
    #     Tokens.SNX,
    #     Tokens.WBTC,
    #     Tokens.USDT,
    #     Tokens.USDC,
    #     Tokens.SUSD,
    #     Tokens.DPI
    # ]

    # user = accounts.at('0x60e86029ed1A8b91cB0dF8BBDFE56c4C2Ad2D073', force=True)
    # # user = accounts.load('homora-relaunch')

    # accounts[9].transfer(user, '10 ether')

    # interface.IERC20(Tokens.USDC).approve(bank, 5 * 10**6, {'from': user})
    # interface.IERC20(Tokens.DAI).approve(bank, 5 * 10**18, {'from': user})

    # for uni_lp in uniswap_whitelist_lp_tokens[1:]:
    #     token0 = interface.IAny(uni_lp).token0()
    #     token1 = interface.IAny(uni_lp).token1()
    #     print(f'Opening Uniswap {interface.IAny(token0).symbol()} {interface.IAny(token1).symbol()}')

    #     borrow_amt_0 = 10 ** (interface.IAny(token0).decimals() - 5) if token0 in borrowable_tokens else 0
    #     borrow_amt_1 = 10 ** (interface.IAny(token1).decimals() - 5) if token1 in borrowable_tokens else 0
    #     # print(f'borrowing {borrow_amt_0}')
    #     # print(f'borrowing {borrow_amt_1}')
    #     bank.execute(
    #         0,
    #         uniswap_spell,
    #         uniswap_spell.addLiquidityWERC20.encode_input(
    #             token0,
    #             token1,
    #             [5 * 10**interface.IAny(token0).decimals(),
    #              0,
    #              0,
    #              borrow_amt_0,
    #              0,  # borrow_amt_1,
    #              0,
    #              0,
    #              0],
    #         ),
    #         {'from': user}
    #     )
