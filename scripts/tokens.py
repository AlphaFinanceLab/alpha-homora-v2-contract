
from brownie import interface

crv_registry = interface.ICurveRegistry('0x7d86446ddb609ed0f5f8684acf30380a356b2b4c')


class Tokens:
    weth = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    dai = '0x6B175474E89094C44Da98b954EedeAC495271d0F'
    usdc = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
    usdt = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    dpi = '0x1494CA1F11D487c2bBe4543E90080AeBa4BA3C2b'
    yfi = '0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'
    perp = '0xbC396689893D065F41bc2C6EcbeE5e0085233447'
    snx = '0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'
    susd = '0x57Ab1ec28D129707052df4dF418D58a2D46d5f51'
    uni = '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'
    sushi = '0x6B3595068778DD592e39A122f4f5a5cF09C90fE2'
    uni_yfi_weth = '0x2fDbAdf3C4D5A8666Bc06645B8358ab803996E28'
    uni_dpi_weth = '0x4d5ef58aAc27d99935E5b6B4A6778ff292059991'
    uni_susd_weth = '0xf80758aB42C3B07dA84053Fd88804bCB6BAA4b5c'
    uni_uni_weth = '0xd3d2E2692501A5c9Ca623199D38826e513033a17'
    uni_snx_weth = '0x43AE24960e5534731Fc831386c07755A2dc33D47'
    sushi_yfi_weth = '0x088ee5007C98a9677165D78dD2109AE4a3D04d0C'
    sushi_dpi_weth = '0x34b13F8CD184F55d0Bd4Dd1fe6C07D46f245c7eD'
    sushi_susd_weth = '0xF1F85b2C54a2bD284B1cf4141D64fD171Bd85539'
    sushi_snx_weth = '0xA1d7b2d891e3A1f9ef4bBC5be20630C2FEB1c470'
    sushi_sushi_weth = '0x795065dCc9f64b5614C407a6EFDC400DA6221FB0'
    bal_perp_usdc = '0xF54025aF2dc86809Be1153c1F20D77ADB7e8ecF4'
    bal_dai_weth = '0x8b6e6E7B5b3801FEd2CaFD4b22b8A16c2F2Db21a'
    crv_dai_usdc_usdt = '0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'  # crv 3pool
    crv_dai_usdc_usdt_susd = '0xC25a3A3b969415c80451098fa907EC722572917F'  # crv susd


def check_tokens():
    tokens = dict(filter(lambda k: not k[0].startswith('_'), vars(Tokens).items()))

    for k, v in tokens.items():
        if interface.IERC20Ex(v).symbol().lower() == k:
            continue
        elif k.startswith('uni_'):
            assert interface.IERC20Ex(v).symbol() == 'UNI-V2'
            token0 = interface.IERC20Ex(interface.IERC20Ex(v).token0()).symbol().lower()
            token1 = interface.IERC20Ex(interface.IERC20Ex(v).token1()).symbol().lower()
            assert k == f'uni_{token0}_{token1}', 'uni: ' + f'{token0} + {token1}'
        elif k.startswith('sushi_'):
            assert interface.IERC20Ex(v).symbol() == 'SLP'
            token0 = interface.IERC20Ex(interface.IERC20Ex(v).token0()).symbol().lower()
            token1 = interface.IERC20Ex(interface.IERC20Ex(v).token1()).symbol().lower()
            assert k == f'sushi_{token0}_{token1}', 'sushi: ' + f'{token0} + {token1}'
        elif k.startswith('bal_'):
            token0, token1 = interface.IERC20Ex(v).getFinalTokens()
            token0 = interface.IERC20Ex(token0).symbol().lower()
            token1 = interface.IERC20Ex(token1).symbol().lower()
            assert interface.IERC20Ex(v).symbol() == 'BPT'
            assert k == f'bal_{token0}_{token1}', 'bal: ' + f'{token0} + {token1}'
        elif k.startswith('crv_'):
            pool = crv_registry.get_pool_from_lp_token(v)
            n, _ = crv_registry.get_n_coins(pool)
            coins = crv_registry.get_coins(pool)[:n]
            coin_names = list(map(lambda coin: interface.IERC20Ex(coin).symbol().lower(), coins))
            assert k == f'crv_' + '_'.join(coin_names), 'crv: ' + '+'.join(coin_names)


def main():
    check_tokens()
