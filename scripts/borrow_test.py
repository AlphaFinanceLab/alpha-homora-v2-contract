from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, ERC20KP3ROracle, UniswapV2LPKP3ROracle, HouseHoldSpell,
)


KP3R_ADDRESS = '0x73353801921417F465377c8d898c6f4C0270282C'
WETH_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'


def setup_bank_hack(homora):
    donator = accounts[5]
    fake = accounts.at(homora.address, force=True)
    controller = interface.IComptroller('0x3d5BC3c8d13dcB8bF317092d84783c2697AE9258')
    creth = interface.ICEtherEx('0xD06527D5e56A3495252A528C4987003b712860eE')
    creth.mint({'value': '90 ether', 'from': donator})
    creth.transfer(fake, creth.balanceOf(donator), {'from': donator})
    controller.enterMarkets([creth], {'from': fake})


def main():
    admin = accounts[0]
    alice = accounts[1]
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    lpusdt = interface.IERC20Ex('0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    router = interface.IUniswapV2Router02('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')
    erc20_oracle = ERC20KP3ROracle.deploy(KP3R_ADDRESS, {'from': admin})
    lp_oracle = UniswapV2LPKP3ROracle.deploy(KP3R_ADDRESS, {'from': admin})
    oracle = ProxyOracle.deploy({'from': admin})
    oracle.setOracles(
        [
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # USDT-ETH
        ],
        [
            [erc20_oracle, 10000, 10000, 10000],
            [lp_oracle, 10000, 10000, 10000],
        ],
        {'from': admin},
    )
    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)
    homora.addBank(usdt, crusdt, {'from': admin})
    # lpusdt.approve(homora, 2**256-1, {'from': alice})
    # Steal some LP from the staking pool
    lpusdt.transfer(alice, 1*10**17, {'from': accounts.at('0x6C3e4cb2E96B01F4b866965A91ed4437839A121a', force=True)})
    household_spell = HouseHoldSpell.deploy(homora, WETH_ADDRESS, {'from': admin})
    tx = homora.execute(
        0,  # position id
        household_spell,
        '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # USDT-ETH
        household_spell.putCollateral.encode_input(
            '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # USDT
            '0.00001 ether',  # valued at approximately $600
        ),
        {'from': alice},

    )
    print('put collateral gas', tx.gas_used)
    position_id = tx.return_value
    print(homora.getCollateralETHValue(position_id), homora.getBorrowETHValue(position_id))
    tx = homora.execute(
        position_id,  # position id
        household_spell,
        '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # USDT-ETH
        household_spell.borrow.encode_input(
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '500000000',  # $500
        ),
        {'from': alice},
    )
    print('bal', usdt.balanceOf(alice))
    print('put collateral gas', tx.gas_used)
    
    _,_,_,totalDebt,totalShare = homora.banks(usdt)
    print('bank usdt totalDebt', totalDebt)
    print('bank usdt totalShare', totalShare)

    usdt.approve(homora, 2**256-1, {'from' : alice})
    usdt.approve(crusdt, 2**256-1, {'from' : accounts.at(homora, force=True)})

    tx = homora.execute(
        position_id,  # position id
        household_spell,
        '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # USDT-ETH
        household_spell.repay.encode_input(
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '300000000',  # $300
        ),
        {'from': alice},
    )
    print('bal', usdt.balanceOf(alice))
    print('repay gas', tx.gas_used)
