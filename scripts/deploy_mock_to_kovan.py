from brownie import accounts, MockOracle, ProxyOracle, MockERC20, MockCErc20, HomoraBank, BasicSpell, HouseHoldSpell, MockWETH9


def main():
    deployer = accounts.load('deployment_account')
    usdt = MockERC20.deploy("USDT", "USDT", {'from': deployer})
    usdt.mint(deployer.address, "10000 ether")
    lptoken = MockERC20.deploy("LP-TOKEN", "LP-TOKEN", {'from': deployer})
    lptoken.mint(deployer.address, "5000 ether")
    weth = MockWETH9.deploy({'from': deployer})
    deployer.transfer(weth, "0.1 ether")
    weth.mint(deployer.address, "0.1 ether")

    cusdt = MockCErc20.deploy(usdt.address, {'from': deployer})
    cweth = MockCErc20.deploy(weth.address, {'from': deployer})

    mock_oracle = MockOracle.deploy({'from': deployer})
    mock_oracle.setETHPx(usdt.address, 500*10**18)
    mock_oracle.setETHPx(lptoken.address, 250*10**18)
    mock_oracle.setETHPx(weth.address, 1*10**18)

    oracle = ProxyOracle.deploy({'from': deployer})
    oracle.setOracles([usdt.address, lptoken.address, weth.address], [
                      (mock_oracle, 10000, 10000, 10000),
                      (mock_oracle, 10000, 10000, 10000),
                      (mock_oracle, 10000, 10000, 10000)])
    homora = HomoraBank.deploy({'from': deployer})
    homora.initialize(oracle, 1000, {'from': deployer})
    homora.addBank(usdt.address, cusdt.address, {'from': deployer})
    homora.addBank(weth.address, cweth.address, {'from': deployer})
    basic_spell = BasicSpell.deploy(
        homora.address, weth.address, {'from': deployer})
    household_spell = HouseHoldSpell.deploy(
        homora.address, weth.address, {'from': deployer})
    print('usdt', usdt.address)
    print('lptoken', lptoken.address)
    print('weth', weth.address)
    print('cusdt', cusdt.address)
    print('cweth', cweth.address)
    print('oracle', oracle.address)
    print('homora', homora.address)
    print('basic_spell', basic_spell.address)
    print('household_spell', household_spell.address)
    print(deployer)
