from brownie import (accounts, BaseK3PROracle, HomoraBank, TripleSlopeInterestRate)


def main():
    deployer = accounts[0]
    oracle = BaseK3PROracle.deploy(
        '0x73353801921417F465377c8d898c6f4C0270282C',
        {'from': deployer},
    )
    ir = TripleSlopeInterestRate.deploy({'from': deployer})
    bank = HomoraBank.deploy({'from': deployer})
    bank.initialize()

    print(oracle)
