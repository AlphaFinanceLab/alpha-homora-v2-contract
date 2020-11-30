from brownie import accounts, interface, Contract
from brownie import HomoraBank


# def deploy_oracle()


def main():
    alice = accounts[0]
    oracle = 0
    homora = HomoraBank.deploy({'from': alice})
    homora.initialize(oracle, 1000, {'from': alice})  # 10% fee

    print(alice.balance())
    usdt = Contract.from_explorer('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    controller = interface.IComptroller('0x3d5BC3c8d13dcB8bF317092d84783c2697AE9258')
    crETH = interface.ICEther('0xD06527D5e56A3495252A528C4987003b712860eE')
    crUSDT = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    controller.enterMarkets([crETH, crUSDT], {'from': alice})
    crETH.mint({'value': '50 ether', 'from': alice})
    print('cr bal', crETH.balanceOf(alice))
    tx = crUSDT.borrow('1000000', {'from': alice})
    print(tx.gas_used)
    print(tx.return_value)
    tx = crUSDT.borrow('1000000', {'from': alice})
    print(tx.gas_used)
    print(tx.return_value)
    print('bal', usdt.balanceOf(alice))
