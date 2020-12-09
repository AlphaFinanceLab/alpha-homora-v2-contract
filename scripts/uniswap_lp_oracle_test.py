from brownie import accounts, interface, Contract
from brownie import (
    SimpleOracle, UniswapLPOracle
)


def main():
    admin = accounts[0]
    alice = accounts[1]

    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    eth_usdt = interface.IERC20Ex('0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852')
    eth_usdc = interface.IERC20Ex('0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc')
    usdt_usdc = interface.IERC20Ex(
        '0x3041cbd36888becc7bbcbc0045e3b1f144466f5f')

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([dai, usdt, usdc, weth], [9060553589188986552095106856227,
                                                     9002288773315920458132820329673073223442669,
                                                     9011535487953795006625883219171279625142296,
                                                     2**112])

    uniswap_oracle = UniswapLPOracle.deploy(simple_oracle, {'from': admin})

    # expected ~100k * 2**112
    print('ETH-USDT LP:', uniswap_oracle.getETHPx(eth_usdt))
    # expected ~100k * 2**112
    print('ETH-USDC LP:', uniswap_oracle.getETHPx(eth_usdc))
    # expected ~3.8e9 * 2**112
    print('USDT-USDC LP:', uniswap_oracle.getETHPx(usdt_usdc))
