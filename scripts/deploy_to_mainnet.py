from brownie import (accounts, BasicK3PROracle, HomoraBank)


def main():
    deployer = accounts[0]
    oracle = BasicK3PROracle.deploy(
        '0x73353801921417F465377c8d898c6f4C0270282C',
        {'from': deployer},
    )
    # ir = TripleSlopeInterestRate.deploy({'from': deployer})
    # bank = HomoraBank.deploy({'from': deployer})
    # bank.initialize()
    print(oracle)
    data = oracle.getETHPx('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    print(data)
    print(1 / (data / (2**112)))
