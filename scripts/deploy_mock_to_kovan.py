from brownie import accounts, MockOracle, ProxyOracle, MockERC20, MockCErc20, HomoraBank, BasicSpell, HouseHoldSpell, WETH9


def main():
    deployer = accounts.load('deployment_account')
    usdt = MockERC20.deploy("USDT", "USDT", {'from': deployer})
    weth = WETH9.deploy({'from': deployer})
    cusdt = MockCErc20.deploy(usdt.address, {'from': deployer})
    cusdt.borrow(10000*10**18, {'from': deployer})
    mock_oracle = MockOracle.deploy({'from': deployer})
    mock_oracle.setETHPx(usdt.address, 500*10**18)
    oracle = ProxyOracle.deploy({'from': deployer})
    oracle.setOracles([usdt.address], [
                      (mock_oracle, 10000, 10000, 10000)])
    homora = HomoraBank.deploy({'from': deployer})
    homora.initialize(oracle, 1000, {'from': deployer})
    homora.addBank(usdt.address, cusdt.address, {'from': deployer})
    basic_spell = BasicSpell.deploy(
        homora.address, weth.address, {'from': deployer})
    household_spell = HouseHoldSpell.deploy(
        homora.address, weth.address, {'from': deployer})
    homora.execute(0, basic_spell.address, usdt.address,
                   basic_spell.ensureApprove.encode_input(usdt.address, deployer.address), {'from': deployer})
    print("ensure", basic_spell.approved(usdt.address, deployer.address))
    print('usdt', usdt.address)
    print('cusdt', cusdt.address)
    print('weth', weth.address)
    print('oracle', oracle.address)
    print('homora', homora.address)
    print('basic_spell', basic_spell.address)
    print('household_spell', household_spell.address)
    print(deployer)
