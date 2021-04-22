
from brownie import interface

crv_registry = interface.ICurveRegistry('0x7d86446ddb609ed0f5f8684acf30380a356b2b4c')


class Tokens:
    ETH = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
    WETH = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    AAVE = '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9'
    BAND = '0xba11d00c5f74255f56a5e366f4f77f5a186d7f55'
    COMP = '0xc00e94cb662c3520282e6f5717214004a7f26888'
    CRV = '0xD533a949740bb3306d119CC777fa900bA034cd52'
    DAI = '0x6B175474E89094C44Da98b954EedeAC495271d0F'
    DPI = '0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b'
    INDEX = '0x0954906da0Bf32d5479e25f46056d22f08464cab'
    LINK = '0x514910771af9ca656af840dff83e8264ecf986ca'
    MKR = '0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2'
    PERP = '0xbC396689893D065F41bc2C6EcbeE5e0085233447'
    REN = '0x408e41876cccdc0f92210600ef50372656052a38'
    RENBTC = '0xeb4c2781e4eba804ce9a9803c67d0893436bb27d'
    SNX = '0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'
    SUSD = '0x57Ab1ec28D129707052df4dF418D58a2D46d5f51'
    SUSHI = '0x6B3595068778DD592e39A122f4f5a5cF09C90fE2'
    UMA = '0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828'
    UNI = '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'
    USDC = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
    USDT = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    WBTC = '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599'
    YFI = '0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'
    UNI_YFI_WETH = '0x2fDbAdf3C4D5A8666Bc06645B8358ab803996E28'
    UNI_DPI_WETH = '0x4d5ef58aAc27d99935E5b6B4A6778ff292059991'
    UNI_SUSD_WETH = '0xf80758aB42C3B07dA84053Fd88804bCB6BAA4b5c'
    UNI_UNI_WETH = '0xd3d2E2692501A5c9Ca623199D38826e513033a17'
    UNI_SNX_WETH = '0x43AE24960e5534731Fc831386c07755A2dc33D47'
    UNI_LINK_WETH = '0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'
    UNI_WBTC_WETH = '0xBb2b8038a1640196FbE3e38816F3e67Cba72D940'
    SUSHI_YFI_WETH = '0x088ee5007C98a9677165D78dD2109AE4a3D04d0C'
    SUSHI_DPI_WETH = '0x34b13F8CD184F55d0Bd4Dd1fe6C07D46f245c7eD'
    SUSHI_SUSD_WETH = '0xF1F85b2C54a2bD284B1cf4141D64fD171Bd85539'
    SUSHI_SNX_WETH = '0xA1d7b2d891e3A1f9ef4bBC5be20630C2FEB1c470'
    SUSHI_SUSHI_WETH = '0x795065dCc9f64b5614C407a6EFDC400DA6221FB0'
    SUSHI_LINK_WETH = '0xC40D16476380e4037e6b1A2594cAF6a6cc8Da967'
    SUSHI_WBTC_WETH = '0xCEfF51756c56CeFFCA006cD410B03FFC46dd3a58'
    BAL_PERP_USDC = '0xF54025aF2dc86809Be1153c1F20D77ADB7e8ecF4'
    BAL_DAI_WETH = '0x8b6e6E7B5b3801FEd2CaFD4b22b8A16c2F2Db21a'
    CRV_DAI_USDC_USDT = '0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'  # crv 3pool
    CRV_DAI_USDC_USDT_SUSD = '0xC25a3A3b969415c80451098fa907EC722572917F'  # crv susd

    # cyTokens
    CY_WETH = '0x41c84c0e2EE0b740Cf0d31F63f3B6F627DC6b393'
    CY_DAI = '0x8e595470Ed749b85C6F7669de83EAe304C2ec68F'
    CY_LINK = '0xE7BFf2Da8A2f619c2586FB83938Fa56CE803aA16'
    CY_YFI = '0xFa3472f7319477c9bFEcdD66E4B948569E7621b9'
    CY_SNX = '0x12A9cC33A980DAa74E00cc2d1A0E74C57A93d12C'
    CY_WBTC = '0x8Fc8BFD80d6A9F17Fb98A373023d72531792B431'
    CY_USDT = '0x48759F220ED983dB51fA7A8C0D2AAb8f3ce4166a'
    CY_USDC = '0x76Eb2FE28b36B3ee97F3Adae0C69606eeDB2A37c'
    CY_SUSD = '0xa7c4054AFD3DbBbF5bFe80f41862b89ea05c9806'
    CY_DPI = '0x7736Ffb07104c0C400Bb0CC9A7C228452A732992'


def check_tokens():
    tokens = dict(filter(lambda k: not k[0].startswith('_'), vars(Tokens).items()))

    for k, v in tokens.items():
        print(k, v)
        if k == 'ETH' or k == 'MKR':
            continue
        if interface.IERC20Ex(v).symbol().upper() == k:
            continue
        elif k.startswith('UNI_'):
            assert interface.IERC20Ex(v).symbol() == 'UNI-V2'
            token0 = interface.IERC20Ex(interface.IERC20Ex(v).token0()).symbol().upper()
            token1 = interface.IERC20Ex(interface.IERC20Ex(v).token1()).symbol().upper()
            assert k == f'UNI_{token0}_{token1}', 'uni: ' + f'{token0} + {token1}'
        elif k.startswith('SUSHI_'):
            assert interface.IERC20Ex(v).symbol() == 'SLP'
            token0 = interface.IERC20Ex(interface.IERC20Ex(v).token0()).symbol().upper()
            token1 = interface.IERC20Ex(interface.IERC20Ex(v).token1()).symbol().upper()
            assert k == f'SUSHI_{token0}_{token1}', 'sushi: ' + f'{token0} + {token1}'
        elif k.startswith('BAL_'):
            token0, token1 = interface.IERC20Ex(v).getFinalTokens()
            token0 = interface.IERC20Ex(token0).symbol().upper()
            token1 = interface.IERC20Ex(token1).symbol().upper()
            assert interface.IERC20Ex(v).symbol() == 'BPT'
            assert k == f'BAL_{token0}_{token1}', 'bal: ' + f'{token0} + {token1}'
        elif k.startswith('CRV_'):
            pool = crv_registry.get_pool_from_lp_token(v)
            n, _ = crv_registry.get_n_coins(pool)
            coins = crv_registry.get_coins(pool)[:n]
            coin_names = list(map(lambda coin: interface.IERC20Ex(coin).symbol().upper(), coins))
            assert k == f'CRV_' + '_'.join(coin_names), 'crv: ' + '+'.join(coin_names)
        elif k.startswith('CY_'):
            cy_token = interface.IERC20Ex(v)
            assert k == f'CY_' + cy_token.symbol()[2:].upper(), 'cy: ' + cy_token.symbol()[2:].upper()
        else:
            raise Exception(f'Error: {k} not found')


def main():
    check_tokens()
