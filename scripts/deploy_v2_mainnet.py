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
    try:
        accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
        publish_status = False
    except:
        publish_status = True

    #######################################################################
    # Load deployer account

    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    #######################################################################
    # Deploy/get aggregator oracle

    agg_oracle = AggregatorOracle.at('0x636478DcecA0308ec6b39e3ab1e6b9EBF00Cd01c')

    #######################################################################
    # Deploy wrappers
    print('================================================================')
    print('Deploying Wrappers...')
    werc20 = WERC20.deploy({'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    wchef = WMasterChef.deploy(MASTERCHEF, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    wgauge = WLiquidityGauge.deploy(CRV_REGISTRY, CRV_TOKEN, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    wstaking_index = WStakingRewards.deploy(
        '0xB93b505Ed567982E2b6756177ddD23ab5745f309',  # staking contract
        Tokens.UNI_DPI_WETH,  # UNI DPI-WETH
        Tokens.INDEX,  # INDEX
        {'from': deployer, 'gas_price': gas_strategy},
        publish_source=publish_status
    )

    #######################################################################
    # Deploy spells
    print('================================================================')
    print('Deploying Spells...')
    uniswap_spell = UniswapV2SpellV1.deploy(
        bank, werc20, '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D', {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    sushiswap_spell = SushiswapSpellV1.deploy(
        bank, werc20, '0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f', wchef, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    balancer_spell = BalancerSpellV1.deploy(
        bank, werc20, Tokens.WETH, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    curve_spell = CurveSpellV1.deploy(
        bank, werc20, Tokens.WETH, wgauge, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)

    #######################################################################
    # Deploy oracles
    print('================================================================')
    print('Deploying Oracles...')
    core_oracle = CoreOracle.deploy({'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    uni_oracle = UniswapV2Oracle.deploy(core_oracle, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    bal_oracle = BalancerPairOracle.deploy(core_oracle, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    crv_oracle = CurveOracle.deploy(core_oracle, CRV_REGISTRY, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    proxy_oracle = ProxyOracle.deploy(core_oracle, {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)

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
    # Set oracle routes for lp tokens
    print('================================================================')
    print('Setting oracle routes for LP tokens...')
    core_oracle_configs = [
        (Tokens.UNI_UNI_WETH, uni_oracle),
        (Tokens.UNI_DPI_WETH, uni_oracle),
        (Tokens.UNI_LINK_WETH, uni_oracle),
        (Tokens.UNI_SNX_WETH, uni_oracle),
        (Tokens.UNI_SUSD_WETH, uni_oracle),
        (Tokens.UNI_WBTC_WETH, uni_oracle),
        (Tokens.UNI_YFI_WETH, uni_oracle),
        (Tokens.SUSHI_SUSHI_WETH, uni_oracle),
        (Tokens.SUSHI_DPI_WETH, uni_oracle),
        (Tokens.SUSHI_LINK_WETH, uni_oracle),
        (Tokens.SUSHI_SNX_WETH, uni_oracle),
        (Tokens.SUSHI_SUSD_WETH, uni_oracle),
        (Tokens.SUSHI_WBTC_WETH, uni_oracle),
        (Tokens.SUSHI_YFI_WETH, uni_oracle),
        (Tokens.BAL_PERP_USDC, bal_oracle),
        (Tokens.CRV_DAI_USDC_USDT, crv_oracle),
        (Tokens.CRV_DAI_USDC_USDT_SUSD, crv_oracle),
    ]

    core_oracle_tokens, core_oracle_base_oracles = zip(*core_oracle_configs)

    core_oracle.setRoute(core_oracle_tokens, core_oracle_base_oracles, {'from': deployer, 'gas_price': gas_strategy})

    #######################################################################
    # Set oracle token factors
    # NOTE: base tokens should have 0 collateral factors
    # NOTE: LP tokens should have 50000 borrow factors
    print('================================================================')
    print('Setting oracle token factors...')

    token_factors = [
        (Tokens.WETH, [12616, 0, 10250]),
        (Tokens.AAVE, [14886, 0, 10250]),
        (Tokens.BAND, [16271, 0, 10250]),
        (Tokens.COMP, [14886, 0, 10250]),
        (Tokens.CRV, [16271, 0, 10250]),
        (Tokens.DAI, [10525, 0, 10250]),
        (Tokens.DPI, [14886, 0, 10250]),
        (Tokens.LINK, [13681, 0, 10250]),
        (Tokens.MKR, [16271, 0, 10250]),
        (Tokens.PERP, [16271, 0, 10250]),
        (Tokens.REN, [16271, 0, 10250]),
        (Tokens.RENBTC, [12616, 0, 10250]),
        (Tokens.SNX, [14886, 0, 10250]),
        (Tokens.SUSD, [11217, 0, 10250]),
        (Tokens.SUSHI, [14886, 0, 10250]),
        (Tokens.UMA, [37472, 0, 10250]),
        (Tokens.UNI, [16271, 0, 10250]),
        (Tokens.USDC, [10525, 0, 10250]),
        (Tokens.USDT, [10525, 0, 10250]),
        (Tokens.WBTC, [12616, 0, 10250]),
        (Tokens.YFI, [13681, 0, 10250]),
        (Tokens.UNI_UNI_WETH, [50000, 6146, 10250]),
        (Tokens.UNI_DPI_WETH, [50000, 6718, 10250]),
        (Tokens.UNI_LINK_WETH, [50000, 7309, 10250]),
        (Tokens.UNI_SNX_WETH, [50000, 6718, 10250]),
        (Tokens.UNI_SUSD_WETH, [50000, 7927, 10250]),
        (Tokens.UNI_WBTC_WETH, [50000, 7927, 10250]),
        (Tokens.UNI_YFI_WETH, [50000, 7309, 10250]),
        (Tokens.SUSHI_SUSHI_WETH, [50000, 6718, 10250]),
        (Tokens.SUSHI_DPI_WETH, [50000, 6718, 10250]),
        (Tokens.SUSHI_LINK_WETH, [50000, 7309, 10250]),
        (Tokens.SUSHI_SNX_WETH, [50000, 6718, 10250]),
        (Tokens.SUSHI_SUSD_WETH, [50000, 7927, 10250]),
        (Tokens.SUSHI_WBTC_WETH, [50000, 7927, 10250]),
        (Tokens.SUSHI_YFI_WETH, [50000, 7309, 10250]),
        (Tokens.BAL_PERP_USDC, [50000, 6146, 10250]),
        (Tokens.CRV_DAI_USDC_USDT, [50000, 9502, 10250]),
        (Tokens.CRV_DAI_USDC_USDT_SUSD, [50000, 8915, 10250])
    ]

    proxy_oracle_tokens, proxy_oracle_configs = zip(*token_factors)

    proxy_oracle.setTokenFactors(proxy_oracle_tokens, proxy_oracle_configs, {'from': deployer, 'gas_price': gas_strategy})

    #######################################################################
    # Set whitelist ERC1155 for wrappers in Proxy Oracle
    print('================================================================')
    print('Whitelisting wrappers in Proxy Oracle...')
    proxy_oracle.setWhitelistERC1155(
        [werc20, wchef, wgauge, wstaking_index],
        True,
        {'from': deployer, 'gas_price': gas_strategy}
    )

    #######################################################################
    # Deploy upgradeable homora bank
    print('================================================================')
    print('Deploying Homora Bank...')
    proxy_admin = ProxyAdminImpl.at('0x090eCE252cEc5998Db765073D07fac77b8e60CB2')
    bank_impl = HomoraBank.deploy({'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    bank = TransparentUpgradeableProxyImpl.deploy(
        bank_impl, proxy_admin, bank_impl.initialize.encode_input(proxy_oracle, 2000), {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    bank = interface.IAny(bank)

    #######################################################################
    # Deploy SafeBoxes
    print('================================================================')
    print('Deploying SafeBoxes...')
    safebox_eth = SafeBoxETH.at('0xeEa3311250FE4c3268F8E684f7C87A82fF183Ec1')
    safebox_dai = SafeBox.at('0xee8389d235E092b2945fE363e97CDBeD121A0439')
    safebox_usdt = SafeBox.at('0x020eDC614187F9937A1EfEeE007656C6356Fb13A')
    safebox_usdc = SafeBox.at('0x08bd64BFC832F1C2B3e07e634934453bA7Fa2db2')
    safebox_yfi = SafeBox.deploy(Tokens.CY_YFI, 'Interest Bearing yearn.finance v2', 'ibYFIv2', {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    safebox_dpi = SafeBox.deploy(Tokens.CY_DPI, 'Interest Bearing DefiPulse Index v2', 'ibDPIv2', {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    safebox_snx = SafeBox.deploy(Tokens.CY_SNX, 'Interest Bearing Synthetix Network Token v2', 'ibSNXv2', {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)
    safebox_susd = SafeBox.deploy(Tokens.CY_SUSD, 'Interest Bearing Synth sUSD v2', 'ibsUSDv2', {'from': deployer, 'gas_price': gas_strategy}, publish_source=publish_status)

    #######################################################################
    # Register pool in curve oracle
    print('================================================================')
    print('Registering Curve pools...')
    crv_oracle.registerPool('0x6c3f90f043a72fa612cbac8115ee7e52bde6e490', {'from': deployer, 'gas_price': gas_strategy})  # CRV 3-pool
    crv_oracle.registerPool('0xC25a3A3b969415c80451098fa907EC722572917F', {'from': deployer, 'gas_price': gas_strategy})  # CRV sUSD

    #######################################################################
    # Register liquidity gauge in gauge wrapper
    print('================================================================')
    print('Registering Liquidity Gauge in Gauge Wrapper...')
    wgauge.registerGauge(0, 0, {'from': deployer, 'gas_price': gas_strategy})  # CRV 3-pool (pid 0)
    wgauge.registerGauge(12, 0, {'from': deployer, 'gas_price': gas_strategy})  # CRV sUSD (pid 12)

    #######################################################################
    # Set whitelist spells in Homora Bank
    print('================================================================')
    print('Whitelisting Spells in HomoraBank...')
    whitelist_spells = [uniswap_spell, sushiswap_spell, balancer_spell, curve_spell]
    bank.setWhitelistSpells(whitelist_spells, [True] * len(whitelist_spells), {'from': deployer, 'gas_price': gas_strategy})

    #######################################################################
    # Set whitelist tokens in Homora Bank
    print('================================================================')
    print('Whitelisting Tokens in Homora Bank...')

    bank_whitelist_tokens = [Tokens.WETH, Tokens.DAI, Tokens.LINK, Tokens.YFI, Tokens.SNX, Tokens.WBTC,
                             Tokens.USDT, Tokens.USDC, Tokens.SUSD, Tokens.DPI]
    bank.setWhitelistTokens(bank_whitelist_tokens, [True] * len(bank_whitelist_tokens), {'from': deployer, 'gas_price': gas_strategy})

    #######################################################################
    # Add cTokens to Homora Bank
    print('================================================================')
    print('Adding banks to Homora Bank...')
    bank.addBank(Tokens.WETH, Tokens.CY_WETH, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.DAI, Tokens.CY_DAI, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.LINK, Tokens.CY_LINK, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.YFI, Tokens.CY_YFI, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.SNX, Tokens.CY_SNX, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.WBTC, Tokens.CY_WBTC, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.USDT, Tokens.CY_USDT, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.USDC, Tokens.CY_USDC, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.SUSD, Tokens.CY_SUSD, {'from': deployer, 'gas_price': gas_strategy})
    bank.addBank(Tokens.DPI, Tokens.CY_DPI, {'from': deployer, 'gas_price': gas_strategy})

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
    uniswap_spell.setWhitelistLPTokens(uniswap_whitelist_lp_tokens, [True] * len(uniswap_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

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
    sushiswap_spell.setWhitelistLPTokens(sushiswap_whitelist_lp_tokens, [True] * len(sushiswap_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

    print('Whitelisting LP tokens for balancer spells...')
    balancer_whitelist_lp_tokens = [
        Tokens.BAL_PERP_USDC
    ]
    balancer_spell.setWhitelistLPTokens(balancer_whitelist_lp_tokens, [True] * len(balancer_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

    print('Whitelisting LP tokens for balancer spells...')
    curve_whitelist_lp_tokens = [
        Tokens.CRV_DAI_USDC_USDT,
        Tokens.CRV_DAI_USDC_USDT_SUSD
    ]
    curve_spell.setWhitelistLPTokens(curve_whitelist_lp_tokens, [True] * len(curve_whitelist_lp_tokens), {'from': deployer, 'gas_price': gas_strategy})

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
    #         {'from': deployer, 'value': '0.1 ether'}
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
