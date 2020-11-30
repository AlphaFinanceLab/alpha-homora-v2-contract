from brownie import accounts, interface, Contract
from brownie import HomoraBank, ProxyOracle, SimpleOracle


# def deploy_oracle()

def main():
    admin = accounts[0]
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    router = interface.IUniswapV2Router02('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')

    simple_oracle = SimpleOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy({'from': admin})
    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    homora.addBank(usdt, crusdt, {'from': admin})
    print(admin.balance())
    controller = interface.IComptroller('0x3d5BC3c8d13dcB8bF317092d84783c2697AE9258')
    crETH = interface.ICEther('0xD06527D5e56A3495252A528C4987003b712860eE')
    crUSDT = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    controller.enterMarkets([crETH, crUSDT], {'from': admin})
    crETH.mint({'value': '50 ether', 'from': admin})
    print('cr bal', crETH.balanceOf(admin))
    tx = crUSDT.borrow('1000000', {'from': admin})
    print(tx.gas_used)
    print(tx.return_value)
    tx = crUSDT.borrow('1000000', {'from': admin})
    print(tx.gas_used)
    print(tx.return_value)
    print('bal', usdt.balanceOf(admin))
