from brownie import accounts, ERC20KP3ROracle, LpTokenKP3ROracle


def main():
    deployer = accounts[0]
    oracle = ERC20KP3ROracle.deploy(
        '0x73353801921417F465377c8d898c6f4C0270282C',
        {'from': deployer},
    )
    lp_oracle = LpTokenKP3ROracle.deploy(
        '0x73353801921417F465377c8d898c6f4C0270282C',
        {'from': deployer},
    )
    data = oracle.getETHPx('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    print(data)
    print(1 / (data / (2**112)))
    data = lp_oracle.getETHPx('0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852')
    print(data)
    print(data / (2**112))
