from brownie import interface
from brownie import SafeBox, SafeBoxETH


def main():
    safebox_eth = SafeBoxETH.at('0xeEa3311250FE4c3268F8E684f7C87A82fF183Ec1')
    safebox_usdt = SafeBox.at('0x020eDC614187F9937A1EfEeE007656C6356Fb13A')
    safebox_usdc = SafeBox.at('0x08bd64BFC832F1C2B3e07e634934453bA7Fa2db2')
    safebox_dai = SafeBox.at('0xee8389d235E092b2945fE363e97CDBeD121A0439')

    cy_eth = interface.IAny(safebox_eth.cToken())
    cy_usdt = interface.IAny(safebox_usdt.cToken())
    cy_usdc = interface.IAny(safebox_usdc.cToken())
    cy_dai = interface.IAny(safebox_dai.cToken())

    print('eth', safebox_eth.totalSupply() * cy_eth.exchangeRateStored() / 1e36)
    print('usdt', safebox_usdt.totalSupply() * cy_usdt.exchangeRateStored() / 1e24)
    print('usdc', safebox_usdc.totalSupply() * cy_usdc.exchangeRateStored() / 1e24)
    print('dai', safebox_dai.totalSupply() * cy_dai.exchangeRateStored() / 1e36)
