from brownie import (HomoraBank, UniswapV2SpellV1, SushiswapSpellV1, BalancerSpellV1,
                     CurveSpellV1, WERC20, WMasterChef, WLiquidityGauge, WStakingRewards)
from brownie import interface, accounts, Contract
from .utils_fork import *


def test_uniswap_spell(bank, uniswap_spell):
    alice = accounts[1]

    comptroller = interface.IAny('0xAB1c342C7bf5Ec5F02ADEA1c2270670bCa144CbB')
    cream = '0x6d5a7597896a703fe8c85775b23395a48f971305'
    comptroller._setCreditLimit(bank, 2**256-1, {'from': cream})

    uni = interface.IAny('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984')
    weth = interface.IAny('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    mint_tokens(uni, alice)
    mint_tokens(weth, alice, amount=1000 * 10**18)

    uni.approve(bank, 2**256-1, {'from': alice})
    weth.approve(bank, 2**256-1, {'from': alice})

    bank.execute(0, uniswap_spell, uniswap_spell.addLiquidityWERC20.encode_input(
        uni, weth, [10 * 10**18, 10 * 10**18, 0, 0, 10**18, 0, 0, 0]
    ), {'from': alice})


def test_sushiswap_spell(bank, sushiswap_spell):
    alice = accounts[1]

    comptroller = interface.IAny('0xAB1c342C7bf5Ec5F02ADEA1c2270670bCa144CbB')
    cream = '0x6d5a7597896a703fe8c85775b23395a48f971305'
    comptroller._setCreditLimit(bank, 2**256-1, {'from': cream})

    sushi = interface.IAny('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2')
    weth = interface.IAny('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')

    mint_tokens(sushi, alice)
    mint_tokens(weth, alice, amount=1000 * 10**18)

    sushi.approve(bank, 2**256-1, {'from': alice})
    weth.approve(bank, 2**256-1, {'from': alice})

    bank.execute(0, sushiswap_spell, sushiswap_spell.addLiquidityWMasterChef.encode_input(
        sushi, weth, [10 * 10**18, 10 * 10**18, 0, 0, 10**18, 0, 0, 0], 12
    ), {'from': alice})


def test_balancer_spell(bank, balancer_spell):
    alice = accounts[1]

    comptroller = interface.IAny('0xAB1c342C7bf5Ec5F02ADEA1c2270670bCa144CbB')
    cream = '0x6d5a7597896a703fe8c85775b23395a48f971305'
    comptroller._setCreditLimit(bank, 2**256-1, {'from': cream})

    perp = interface.IAny('0xbC396689893D065F41bc2C6EcbeE5e0085233447')
    usdc = interface.IAny('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
    lp = interface.IAny('0xF54025aF2dc86809Be1153c1F20D77ADB7e8ecF4')

    wstaking = interface.IAny('0xC4635854480ffF80F742645da0310e9e59795c63')

    mint_tokens(perp, alice)
    mint_tokens(usdc, alice)

    perp.approve(bank, 2**256-1, {'from': alice})
    usdc.approve(bank, 2**256-1, {'from': alice})

    bank.execute(0, balancer_spell, balancer_spell.addLiquidityWStakingRewards.encode_input(
        lp, [10 * 10**18, 10 * 10**6, 0, 0, 10**6, 0, 0], wstaking
    ), {'from': alice})


def test_curve_spell(bank, curve_spell):
    alice = accounts[1]

    comptroller = interface.IAny('0xAB1c342C7bf5Ec5F02ADEA1c2270670bCa144CbB')
    cream = '0x6d5a7597896a703fe8c85775b23395a48f971305'
    comptroller._setCreditLimit(bank, 2**256-1, {'from': cream})

    dai = interface.IAny('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    usdc = interface.IAny('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
    usdt = interface.IAny('0xdAC17F958D2ee523a2206206994597C13D831ec7')

    lp = interface.IAny('0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490')

    mint_tokens(dai, alice)
    mint_tokens(usdc, alice)
    mint_tokens(usdt, alice)

    dai.approve(bank, 2**256-1, {'from': alice})
    usdc.approve(bank, 2**256-1, {'from': alice})
    usdt.approve(bank, 2**256-1, {'from': alice})

    bank.execute(0, curve_spell, curve_spell.addLiquidity3.encode_input(
        lp, [10 * 10**18, 10 * 10**6, 10 * 10**6], 0, [10**18, 10**6, 10**6], 0, 0, 0, 0
    ), {'from': alice})


def main():
    deployer = accounts.at('0xB593d82d53e2c187dc49673709a6E9f806cdC835', force=True)
    # deployer = accounts.load('gh')

    weth = interface.IAny('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    dai = interface.IAny('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    usdc = interface.IAny('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
    usdt = interface.IAny('0xdAC17F958D2ee523a2206206994597C13D831ec7')

    werc20 = WERC20.at('0xe28D9dF7718b0b5Ba69E01073fE82254a9eD2F98')
    wmas = WMasterChef.at('0x373ae78a14577682591E088F2E78EF1417612c68')
    wliq = WLiquidityGauge.at('0xfdB4f97953150e47C8606758C13e70b5a789a7ec')
    wsindex = WStakingRewards.at('0x713df2DDDA9C7d7bDa98A9f8fCd82c06c50fbd90')
    wsperp = WStakingRewards.at('0xC4635854480ffF80F742645da0310e9e59795c63')

    # upgrade bank's implementation
    bank_impl = HomoraBank.deploy({'from': deployer})
    proxy_admin = Contract.from_explorer('0x090eCE252cEc5998Db765073D07fac77b8e60CB2')
    bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    proxy_admin.upgrade(bank, bank_impl, {'from': deployer})

    # re-deploy spells
    uniswap_spell = UniswapV2SpellV1.deploy(
        bank, werc20, '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D', {'from': deployer})
    sushiswap_spell = SushiswapSpellV1.deploy(
        bank, werc20, '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F', wmas, {'from': deployer})
    balancer_spell = BalancerSpellV1.deploy(bank, werc20, weth, {'from': deployer})
    curve_spell = CurveSpellV1.deploy(bank, werc20, weth, wliq, {'from': deployer})

    # set whitelist spells in bank
    bank.setWhitelistSpells([uniswap_spell, sushiswap_spell,
                             balancer_spell, curve_spell], [True] * 4, {'from': deployer})

    # set whitelist tokens in bank
    bank.setWhitelistTokens([weth, dai, usdc, usdt], [True] * 4, {'from': deployer})

    # set whitelist lp tokens in spells
    uniswap_spell.setWhitelistLPTokens(['0xd3d2E2692501A5c9Ca623199D38826e513033a17'], [
                                       True], {'from': deployer})
    sushiswap_spell.setWhitelistLPTokens(
        ['0x795065dCc9f64b5614C407a6EFDC400DA6221FB0'], [True], {'from': deployer})
    balancer_spell.setWhitelistLPTokens(
        ['0xF54025aF2dc86809Be1153c1F20D77ADB7e8ecF4'], [True], {'from': deployer})
    curve_spell.setWhitelistLPTokens(['0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490'], [
                                     True], {'from': deployer})

    ##############################################################################################
    # test execute each spell

    # test_uniswap_spell(bank, uniswap_spell)
    # test_sushiswap_spell(bank, sushiswap_spell)
    # test_balancer_spell(bank, balancer_spell)
    # test_curve_spell(bank, curve_spell)
