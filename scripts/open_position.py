from brownie import *


def main():
    bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    cream = Contract.from_explorer('0xab1c342c7bf5ec5f02adea1c2270670bca144cbb')
    admin_cream = accounts.at('0x6D5a7597896A703Fe8c85775B23395a48f971305', force=True)
    cream._setCreditLimit(bank, 2**256-1, {'from': admin_cream})
    spell = UniswapV2SpellV1.at('0x40778F8dc76edCdDe50a5Cd237f27Ee1c79dB32C')
    me = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    tx = bank.execute(
        0,
        spell,
        spell.addLiquidity.encode_input(
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # token 0
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # token 1
            [
                0,  # supply USDT
                0,   # supply WETH
                0,  # supply LP
                0,  # borrow USDT
                '1 ether',  # borrow WETH
                0,  # borrow LP tokens
                0,  # min USDT
                0
            ],  # min WETH
        ),
        {'from': me, 'value': '2 ether'}
    )
    print(bank.getCollateralETHValue(1))
    print(bank.getBorrowETHValue(1))
    print(bank.nextPositionId())
