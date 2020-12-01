from brownie import accounts, MockOracle, ProxyOracle, MockERC20, MockCErc20, HomoraBank, BasicSpell, HouseHoldSpell

usdt_address = "0x88F904a95304Ca27D592cd413dd0d691CcB7Bc73"
cusdt_address = "0x7670090531521Ec4Cc62AbBaF31d9F4E70aA0002"
oracle_address = "0x3d248909654c843Bf8a40b9C4bAd39ED23519aa4"
homora_address = "0x36C2DBd86689350d269e6EECC3E7A1b0FcBa3Fc7"
basic_spell_address = "0x49c9492B1953af689D9a0e4dA1567fe4D8369B26"
household_spell_address = "0xa6ca228fdF4365e0bDa918b1B4552B750E2FD479"


def main():
    deployer = accounts.load('deployment_account')
    usdt = MockERC20.at(usdt_address)
    homora = HomoraBank.at(homora_address)
    household_spell = HouseHoldSpell.at(household_spell_address)
    usdt.approve(homora, 2**256-1, {'from': deployer})
    # Put collateral
    print('me', usdt.balanceOf("0x192686b09306E00fc529D8e7CbcF58f498620DE7"))
    print('bank', usdt.balanceOf(homora.address))
    homora.execute(0,
                   household_spell,
                   usdt.address,
                   household_spell.putCollateral.encode_input(
                       usdt.address, 100*10**18),
                   {'from': deployer})
    print('me', usdt.balanceOf("0x192686b09306E00fc529D8e7CbcF58f498620DE7"))
    print('bank', usdt.balanceOf(homora.address))

    # Take collateral
    print('me', usdt.balanceOf("0x192686b09306E00fc529D8e7CbcF58f498620DE7"))
    print('bank', usdt.balanceOf(homora.address))
    position_id = homora.nextPositionId()
    print(position_id)
    homora.execute(position_id - 1,
                   household_spell,
                   usdt.address,
                   household_spell.takeCollateral.encode_input(
                       usdt.address, 10*10**18),
                   {'from': deployer})
    print('me', usdt.balanceOf("0x192686b09306E00fc529D8e7CbcF58f498620DE7"))
    print('bank', usdt.balanceOf(homora.address))
