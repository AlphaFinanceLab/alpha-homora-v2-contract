from brownie import interface, accounts
from brownie import (ProxyAdminImpl, HomoraBank, TransparentUpgradeableProxyImpl, AggregatorOracle,
                     WERC20, WMasterChef, WLiquidityGauge, WStakingRewards,
                     CoreOracle, UniswapV2Oracle, BalancerPairOracle, CurveOracle, ProxyOracle,
                     UniswapV2SpellV1, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1,
                     SafeBoxETH, SafeBox,)

from .utils import *
from .tokens import Tokens

from brownie.network.gas.strategies import GasNowScalingStrategy

gas_strategy = GasNowScalingStrategy(
    initial_speed="fast", max_speed="fast", increment=1.085, block_duration=20)


CRV_REGISTRY = '0x7D86446dDb609eD0F5f8684AcF30380a356b2B4c'
CRV_TOKEN = '0xD533a949740bb3306d119CC777fa900bA034cd52'
MASTERCHEF = '0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd'
ETH = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'

SUSHI_LP_PID = {
    Tokens.SUSHI_SUSHI_WETH: 12,
    Tokens.SUSHI_DPI_WETH: 42,
    Tokens.SUSHI_LINK_WETH: 8,
    Tokens.SUSHI_SNX_WETH: 6,
    Tokens.SUSHI_SUSD_WETH: 3,
    Tokens.SUSHI_WBTC_WETH: 21,
    Tokens.SUSHI_YFI_WETH: 11
}


def fake_credit_limit(bank):
    comptroller = interface.IAny('0xab1c342c7bf5ec5f02adea1c2270670bca144cbb')
    comptroller_admin = comptroller.admin()
    comptroller._setCreditLimit(bank, 2**256-1, {'from': comptroller_admin})


def main():

    # set publish status based on fork or not
    # try:
    #     deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    #     deployer.transfer(deployer, 1)
    #     publish_status = False
    # except:
    #     publish_status = True

    publish_status = False

    #######################################################################
    # Load deployer account

    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    #######################################################################
    # Deploy/get aggregator oracle

    agg_oracle = AggregatorOracle.at('')

    #######################################################################
    # Deploy wrappers
    print('================================================================')
    print('Deploying Wrappers...')
    werc20 = WERC20.at('0x06799a1e4792001AA9114F0012b9650cA28059a3')
    wchef = WMasterChef.at('0xA2caEa05fF7B98f10Ad5ddc837F15905f33FEb60')
    wgauge = WLiquidityGauge.at('0xf1F32C8EEb06046d3cc3157B8F9f72B09D84ee5b')
    wstaking_index = WStakingRewards.at('0x011535FD795fD28c749363E080662D62fBB456a7')

    #######################################################################
    # Deploy oracles
    print('================================================================')
    print('Deploying Oracles...')
    core_oracle = CoreOracle.at('0x6be987c6d72e25F02f6f061F94417d83a6Aa13fC')
    uni_oracle = UniswapV2Oracle.at('0x7678eB6251f41FBF4e0DF36c90bfE32843C2dAf9')
    bal_oracle = BalancerPairOracle.at('0x040349970d87edeef60252117A4E660C49aea5Af')
    crv_oracle = CurveOracle.at('0x772937644A24AA105847931c74DA168fF1DBB6eA')
    proxy_oracle = ProxyOracle.at('0x914C687FFdAB6E1B47a327E7E4C10e4a058e009d')

    #######################################################################
    # Set oracle routes for base tokens
    print('================================================================')
    print('Setting oracle routers for base tokens to aggregator oracle...')
    base_token_list = [Tokens.ETH,
                       Tokens.WETH,
                       Tokens.AAVE,
                       Tokens.BAND,
                       Tokens.COMP,
                       Tokens.CRV,
                       Tokens.DAI,
                       Tokens.DPI,
                       Tokens.LINK,
                       Tokens.MKR,
                       Tokens.PERP,
                       Tokens.REN,
                       Tokens.RENBTC,
                       Tokens.SNX,
                       Tokens.SUSD,
                       Tokens.SUSHI,
                       Tokens.UMA,
                       Tokens.UNI,
                       Tokens.USDC,
                       Tokens.USDT,
                       Tokens.WBTC,
                       Tokens.YFI]

    core_oracle.setRoute(base_token_list, [agg_oracle] * len(base_token_list), {'from': deployer, 'gas_price': gas_strategy})

    #######################################################################
    # Deploy upgradeable homora bank
    print('================================================================')
    print('Deploying Homora Bank...')
    proxy_admin = ProxyAdminImpl.at('0x090eCE252cEc5998Db765073D07fac77b8e60CB2')
    bank_impl = HomoraBank.at('0x99c666810bA4Bf9a4C2318CE60Cb2c279Ee2cF56')
    bank = TransparentUpgradeableProxyImpl.at('0xba5eBAf3fc1Fcca67147050Bf80462393814E54B')
    bank = interface.IAny(bank)

    #######################################################################
    # Deploy spells
    print('================================================================')
    print('Deploying Spells...')
    uniswap_spell = UniswapV2SpellV1.at('0x7b1f4cDD4f599774feae6516460BCCD97Fc2100E')
    sushiswap_spell = SushiswapSpellV1.at('0xc4a59cfEd3FE06bDB5C21dE75A70B20dB280D8fE')
    balancer_spell = BalancerSpellV1.at('0x6b8079Bf80E07fB103a55E49EE226f729E1e38D5')
    curve_spell = CurveSpellV1.at('0x8b947D8448CFFb89EF07A6922b74fBAbac219795')

    #######################################################################
    # Deploy SafeBoxes
    print('================================================================')
    print('Deploying SafeBoxes...')
    safebox_eth = SafeBoxETH.at('0xeEa3311250FE4c3268F8E684f7C87A82fF183Ec1')
    safebox_dai = SafeBox.at('0xee8389d235E092b2945fE363e97CDBeD121A0439')
    safebox_usdt = SafeBox.at('0x020eDC614187F9937A1EfEeE007656C6356Fb13A')
    safebox_usdc = SafeBox.at('0x08bd64BFC832F1C2B3e07e634934453bA7Fa2db2')
    safebox_yfi = SafeBox.at('0xe52557bf7315Fd5b38ac0ff61304cb33BB973603')
    safebox_dpi = SafeBox.at('0xd80CE6816f263C3cA551558b2034B61bc9852b97')
    safebox_snx = SafeBox.at('0x4d38b1ac1fad488e22282db451613EDd10434bdC')
    safebox_susd = SafeBox.at('0x8897cA3e1B9BC5D5D715b653f186Cc7767bD4c66')

    #######################################################################
    # Set whitelist LP tokens for spells
    print('================================================================')
    print('Whitelisting LP tokens for uniswap spells...')
    uniswap_whitelist_lp_tokens = [
        Tokens.UNI_UNI_WETH,
        Tokens.UNI_DPI_WETH,
        Tokens.UNI_LINK_WETH,
        Tokens.UNI_SNX_WETH,
        Tokens.UNI_SUSD_WETH,
        Tokens.UNI_WBTC_WETH,
        Tokens.UNI_YFI_WETH
    ]
    # uniswap_spell.setWhitelistLPTokens(uniswap_whitelist_lp_tokens, [True] * len(uniswap_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

    print('Whitelisting LP tokens for sushiswap spells...')
    sushiswap_whitelist_lp_tokens = [
        Tokens.SUSHI_SUSHI_WETH,
        Tokens.SUSHI_DPI_WETH,
        Tokens.SUSHI_LINK_WETH,
        Tokens.SUSHI_SNX_WETH,
        Tokens.SUSHI_SUSD_WETH,
        Tokens.SUSHI_WBTC_WETH,
        Tokens.SUSHI_YFI_WETH
    ]
    # sushiswap_spell.setWhitelistLPTokens(sushiswap_whitelist_lp_tokens, [True] * len(sushiswap_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

    print('Whitelisting LP tokens for balancer spells...')
    balancer_whitelist_lp_tokens = [
        Tokens.BAL_PERP_USDC
    ]
    # balancer_spell.setWhitelistLPTokens(balancer_whitelist_lp_tokens, [True] * len(balancer_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

    print('Whitelisting LP tokens for balancer spells...')
    curve_whitelist_lp_tokens = [
        Tokens.CRV_DAI_USDC_USDT,
        # Tokens.CRV_DAI_USDC_USDT_SUSD
    ]
    # curve_spell.setWhitelistLPTokens(curve_whitelist_lp_tokens, [True] * len(curve_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

    # #######################################################################
    # # Open positions in each pool
    # print('================================================================')
    # print('Opening positions...')

    # fake_credit_limit(bank)  # for testing only. TODO: remove

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

    # # deposit some sUSD
    # # TODO: obtain some sUSD first
    # mint_tokens(Tokens.SUSD, deployer)
    # interface.IERC20(Tokens.SUSD).approve(safebox_susd, 2**256-1, {'from': deployer, 'gas_price': gas_strategy})
    # safebox_susd.deposit(10 * 10**18, {'from': deployer, 'gas_price': gas_strategy})

    # print(f'Opening Uniswap DPI WETH (INDEX)')
    # bank.execute(
    #     0,
    #     uniswap_spell,
    #     uniswap_spell.addLiquidityWStakingRewards.encode_input(
    #         Tokens.DPI,
    #         Tokens.WETH,
    #         [0,
    #          0,
    #          0,
    #          10 ** 6,
    #          10 ** 6,
    #          0,
    #          0,
    #          0],
    #         wstaking_index
    #     ),
    #     {'from': deployer, 'value': '0.1 ether', 'gas_price': gas_strategy}
    # )

    # for uni_lp in uniswap_whitelist_lp_tokens:
    #     token0 = interface.IAny(uni_lp).token0()
    #     token1 = interface.IAny(uni_lp).token1()
    #     print(f'Opening Uniswap {interface.IAny(token0).symbol()} {interface.IAny(token1).symbol()}')

    #     borrow_amt_0 = 10 ** (interface.IAny(token0).decimals() - 6) if token0 in borrowable_tokens else 0
    #     borrow_amt_1 = 10 ** (interface.IAny(token1).decimals() - 6) if token1 in borrowable_tokens else 0
    #     bank.execute(
    #         0,
    #         uniswap_spell,
    #         uniswap_spell.addLiquidityWERC20.encode_input(
    #             token0,
    #             token1,
    #             [0,
    #              0,
    #              0,
    #              borrow_amt_0,
    #              borrow_amt_1,
    #              0,
    #              0,
    #              0],
    #         ),
    #         {'from': deployer, 'value': '0.1 ether', 'gas_price': gas_strategy}
    #     )

    # for sushi_lp in sushiswap_whitelist_lp_tokens:
    #     token0 = interface.IAny(sushi_lp).token0()
    #     token1 = interface.IAny(sushi_lp).token1()
    #     print(f'Opening Sushiswap {interface.IAny(token0).symbol()} {interface.IAny(token1).symbol()}')

    #     borrow_amt_0 = 10 ** (interface.IAny(token0).decimals() - 6) if token0 in borrowable_tokens else 0
    #     borrow_amt_1 = 10 ** (interface.IAny(token1).decimals() - 6) if token1 in borrowable_tokens else 0
    #     bank.execute(
    #         0,
    #         sushiswap_spell,
    #         sushiswap_spell.addLiquidityWMasterChef.encode_input(
    #             token0,
    #             token1,
    #             [0,
    #              0,
    #              0,
    #              borrow_amt_0,
    #              borrow_amt_1,
    #              0,
    #              0,
    #              0],
    #             SUSHI_LP_PID[sushi_lp]
    #         ),
    #         {'from': deployer, 'value': '0.1 ether', 'gas_price': gas_strategy}
    #     )

    # mint_tokens(Tokens.USDC, deployer)
    # interface.IERC20(Tokens.USDC).approve(bank, 2**256-1, {'from': deployer, 'gas_price': gas_strategy})

    # for bal_lp in balancer_whitelist_lp_tokens:
    #     token0, token1 = interface.IAny(bal_lp).getFinalTokens()
    #     print(f'Opening Balancer {interface.IAny(token0).symbol()} {interface.IAny(token1).symbol()}')
    #     bank.execute(
    #         0,
    #         balancer_spell,
    #         balancer_spell.addLiquidityWERC20.encode_input(
    #             bal_lp,
    #             [0,
    #              10 * 10**6,
    #              0,
    #              0,
    #              10**6,
    #              0,
    #              0]
    #         ), {'from': deployer, 'gas_price': gas_strategy}
    #     )

    # print('Opening Curve 3pool')
    # bank.execute(
    #     0,
    #     curve_spell,
    #     curve_spell.addLiquidity3.encode_input(
    #         Tokens.CRV_DAI_USDC_USDT,
    #         [0, 10 * 10**6, 0],
    #         0,
    #         [10**18, 10**6, 10**6],
    #         0,
    #         0,
    #         0,
    #         0
    #     ),
    #     {'from': deployer, 'gas_price': gas_strategy}
    # )

    # print('Opening Curve sUSD')
    # bank.execute(
    #     0,
    #     curve_spell,
    #     curve_spell.addLiquidity4.encode_input(
    #         Tokens.CRV_DAI_USDC_USDT_SUSD,
    #         [0, 10 * 10**6, 0, 0],
    #         0,
    #         [10**18, 10**6, 10**6, 10**18],
    #         0,
    #         0,
    #         12,
    #         0
    #     ),
    #     {'from': deployer, 'gas_price': gas_strategy}
    # )
