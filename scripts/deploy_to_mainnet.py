from brownie import accounts, ERC20KP3ROracle, UniswapV2LPKP3ROracle


def main():
    deployer = accounts[0]
    oracle = ERC20KP3ROracle.deploy(
        '0x73353801921417F465377c8d898c6f4C0270282C',
        {'from': deployer},
    )
    lp_oracle = UniswapV2LPKP3ROracle.deploy(
        '0x73353801921417F465377c8d898c6f4C0270282C',
        {'from': deployer},
    )

    # usdt
    data = oracle.getETHPx('0xdac17f958d2ee523a2206206994597c13d831ec7')
    print(data)
    print(1 / (data / (2**112)))

    # usdc
    data = oracle.getETHPx('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
    print(data)
    print(1 / (data / (2**112)))

    # usdt-usdc
    data = lp_oracle.getETHPx('0x3041cbd36888becc7bbcbc0045e3b1f144466f5f')
    print(data)
    print(data / (2**112))
