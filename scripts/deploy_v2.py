from brownie import (
    accounts, ERC20KP3ROracle, UniswapV2Oracle, BalancerPairOracle, ProxyOracle, CoreOracle,
    HomoraBank, CurveOracle, UniswapV2SpellV1, WERC20, WLiquidityGauge, WMasterChef,
    WStakingRewards, SushiswapSpellV1, BalancerSpellV1, CurveSpellV1,
)


KP3R_ORACLE = '0x79eacCe598871B4e66bAB1544C87f1e2Aff54f5a'
CRV_REGISTRY = '0x7D86446dDb609eD0F5f8684AcF30380a356b2B4c'
CRV_TOKEN = '0xD533a949740bb3306d119CC777fa900bA034cd52'
MASTERCHEF = '0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd'
BANK = '0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb'


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')
    werc20 = WERC20.deploy({'from': deployer})
    wmas = WMasterChef.deploy(MASTERCHEF, {'from': deployer})
    wliq = WLiquidityGauge.deploy(CRV_REGISTRY, CRV_TOKEN, {'from': deployer})
    wsindex = WStakingRewards.deploy(
        '0xB93b505Ed567982E2b6756177ddD23ab5745f309',
        '0x4d5ef58aAc27d99935E5b6B4A6778ff292059991',  # UNI DPI-WETH
        '0x0954906da0Bf32d5479e25f46056d22f08464cab',  # INDEX
        {'from': deployer},
    )
    wsperp = WStakingRewards.deploy(
        '0xb9840a4a8a671f79de3df3b812feeb38047ce552',
        '0xF54025aF2dc86809Be1153c1F20D77ADB7e8ecF4',  # BAL PERP-USDC 80-20
        '0xbC396689893D065F41bc2C6EcbeE5e0085233447',  # PERP
        {'from': deployer},
    )
    core_oracle = CoreOracle.deploy({'from': deployer})
    uni_oracle = UniswapV2Oracle.deploy(core_oracle, {'from': deployer})
    bal_oracle = BalancerPairOracle.deploy(core_oracle, {'from': deployer})
    crv_oracle = CurveOracle.deploy(core_oracle, CRV_REGISTRY, {'from': deployer})
    proxy_oracle = ProxyOracle.deploy(core_oracle, {'from': deployer})
    core_oracle.setRoute([
        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',  # WETH
        '0x6b175474e89094c44da98b954eedeac495271d0f',  # DAI
        '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',  # USDC
        '0xdac17f958d2ee523a2206206994597c13d831ec7',  # USDT
        '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',  # WBTC
        '0x1494ca1f11d487c2bbe4543e90080aeba4ba3c2b',  # DPI
        '0xbC396689893D065F41bc2C6EcbeE5e0085233447',  # PERP
        '0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f',  # SNX
        '0xa478c2975ab1ea89e8196811f51a7b7ade33eb11',  # UNI DAI-WETH
        '0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852',  # UNI WETH-USDT
        '0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc',  # UNI USDC-WETH
        '0xbb2b8038a1640196fbe3e38816f3e67cba72d940',  # UNI WBTC-WETH
        '0x4d5ef58aac27d99935e5b6b4a6778ff292059991',  # UNI DPI-WETH
        '0x8b6e6e7b5b3801fed2cafd4b22b8a16c2f2db21a',  # BAL WETH-DAI 80-20
        '0xf54025af2dc86809be1153c1f20d77adb7e8ecf4',  # BAL PERP-USDC 80-20
        '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',  # CRV 3-POOL
    ], [
        KP3R_ORACLE,
        KP3R_ORACLE,
        KP3R_ORACLE,
        KP3R_ORACLE,
        KP3R_ORACLE,
        KP3R_ORACLE,
        KP3R_ORACLE,
        KP3R_ORACLE,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        uni_oracle,
        bal_oracle,
        bal_oracle,
        crv_oracle,
    ], {'from': deployer})
    proxy_oracle.setOracles([
        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',  # WETH
        '0x6b175474e89094c44da98b954eedeac495271d0f',  # DAI
        '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',  # USDC
        '0xdac17f958d2ee523a2206206994597c13d831ec7',  # USDT
        '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',  # WBTC
        '0x1494ca1f11d487c2bbe4543e90080aeba4ba3c2b',  # DPI
        '0xbC396689893D065F41bc2C6EcbeE5e0085233447',  # PERP
        '0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f',  # SNX
        '0xa478c2975ab1ea89e8196811f51a7b7ade33eb11',  # UNI DAI-WETH
        '0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852',  # UNI WETH-USDT
        '0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc',  # UNI USDC-WETH
        '0xbb2b8038a1640196fbe3e38816f3e67cba72d940',  # UNI WBTC-WETH
        '0x4d5ef58aac27d99935e5b6b4a6778ff292059991',  # UNI DPI-WETH
        '0x8b6e6e7b5b3801fed2cafd4b22b8a16c2f2db21a',  # BAL WETH-DAI 80-20
        '0xf54025af2dc86809be1153c1f20d77adb7e8ecf4',  # BAL PERP-USDC 80-20
        '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',  # CRV 3-POOL
    ], [
        [12500, 8000, 10250],
        [10500, 9500, 10250],
        [10500, 9500, 10250],
        [10500, 9500, 10250],
        [12500, 8000, 10250],
        [50000, 0, 10250],
        [50000, 0, 10250],
        [50000, 0, 10250],
        [50000, 8000, 10250],
        [50000, 8000, 10250],
        [50000, 8000, 10250],
        [50000, 8000, 10250],
        [50000, 6000, 10250],
        [50000, 8000, 10250],
        [50000, 0, 10250],
        [50000, 9500, 10250],
    ], {'from': deployer})
    proxy_oracle.setWhitelistERC1155(
        [werc20, wmas, wliq, wsindex, wsperp],
        True,
        {'from': deployer},
    )
    bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    bank.setOracle(proxy_oracle, {'from': deployer})
    wliq.registerGauge(0, 0, {'from': deployer})

    UniswapV2SpellV1.deploy(
        bank, werc20, '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        {'from': deployer},
    )
    SushiswapSpellV1.deploy(
        bank, werc20, '0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f', wmas,
        {'from': deployer},
    )
    BalancerSpellV1.deploy(
        bank, werc20, '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
        {'from': deployer},
    )
    CurveSpellV1.deploy(
        bank, werc20, '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', wliq,
        {'from': deployer},
    )

    print('DONE')
