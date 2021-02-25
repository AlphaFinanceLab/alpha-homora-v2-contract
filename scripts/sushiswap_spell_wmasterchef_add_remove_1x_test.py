from brownie import accounts, interface, Contract, chain
from brownie import (HomoraBank, ProxyOracle, CoreOracle, UniswapV2Oracle,
                     SimpleOracle, SushiswapSpellV1, WERC20, WMasterChef, MockCErc20)
import brownie
from brownie.exceptions import VirtualMachineError
from .utils import *


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def setup_bank_hack(homora):
    donator = accounts[5]
    fake = accounts.at(homora.address, force=True)
    controller = interface.IComptroller(
        '0x3d5BC3c8d13dcB8bF317092d84783c2697AE9258')
    creth = interface.ICEtherEx('0xD06527D5e56A3495252A528C4987003b712860eE')
    creth.mint({'value': '90 ether', 'from': donator})
    creth.transfer(fake, creth.balanceOf(donator), {'from': donator})
    controller.enterMarkets([creth], {'from': fake})


def setup_transfer(asset, fro, to, amt):
    print(f'sending from {fro} {amt} {asset.name()} to {to}')
    asset.transfer(to, amt, {'from': fro})


def main():
    admin = accounts[0]

    alice = accounts[1]
    bob = accounts[2]
    usdt = interface.IERC20Ex('0xdac17f958d2ee523a2206206994597c13d831ec7')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')

    lp = interface.IERC20Ex('0x06da0fd433C1A5d7a4faa01111c044910A184553')
    lp_usdc = interface.IERC20Ex('0x3041cbd36888becc7bbcbc0045e3b1f144466f5f')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    crusdc = interface.ICErc20('0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322')

    sushi = interface.IERC20('0x6b3595068778dd592e39a122f4f5a5cf09c90fe2')

    # sushiswap router
    router = interface.IUniswapV2Router02(
        '0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f')

    chef = accounts.at(
        '0xc2edad668740f1aa35e4d8f227fb8e17dca888cd', force=True)
    wchef = WMasterChef.deploy(chef, {'from': admin})

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([usdt, weth, usdc], [2**112 // 700, 2**112, 2**112 // 700])

    uniswap_oracle = UniswapV2Oracle.deploy(simple_oracle, {'from': admin})
    core_oracle = CoreOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy(core_oracle, {'from': admin})
    oracle.setWhitelistERC1155([werc20, wchef], True, {'from': admin})
    core_oracle.setRoute(
        [usdt, weth, lp, usdc, lp_usdc],
        [simple_oracle, simple_oracle, uniswap_oracle, simple_oracle, uniswap_oracle],
        {'from': admin},
    )
    oracle.setOracles(
        [usdt, weth, lp, usdc, lp_usdc],
        [
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
        ],
        {'from': admin},
    )

    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)
    homora.addBank(usdt, crusdt, {'from': admin})
    homora.addBank(usdc, crusdc, {'from': admin})

    # setup initial funds to alice
    mint_tokens(usdt, alice)
    mint_tokens(weth, alice)
    mint_tokens(usdc, alice)

    # check alice's funds
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')
    print(f'Alice weth balance {weth.balanceOf(alice)}')

    # Steal some LP from the staking pool
    mint_tokens(lp, alice)
    mint_tokens(lp, bob)

    # set approval
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})
    lp.approve(homora, 2**256-1, {'from': alice})
    lp.approve(chef, 2**256-1, {'from': bob})

    sushiswap_spell = SushiswapSpellV1.deploy(
        homora, werc20, router, wchef, {'from': admin})
    # first time call to reduce gas
    sushiswap_spell.getPair(weth, usdt, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([sushiswap_spell], [True], {'from': admin})

    # whitelist lp in spell
    sushiswap_spell.setWhitelistLPTokens([lp], [True], {'from': admin})

    #####################################################################################
    print('=========================================================================')
    print('Case 1. add liquidity first time')

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_chef = lp.balanceOf(chef)

    if interface.IUniswapV2Pair(lp).token0() == usdt:
        prevARes, prevBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    else:
        prevBRes, prevARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    usdt_amt = 10 * 10**6
    weth_amt = 10**18
    lp_amt = 0
    borrow_usdt_amt = 0
    borrow_weth_amt = 0

    pid = 0

    tx = homora.execute(
        0,
        sushiswap_spell,
        sushiswap_spell.addLiquidityWMasterChef.encode_input(
            usdt,  # token 0
            weth,  # token 1
            [usdt_amt,  # supply USDT
             weth_amt,   # supply WETH
             lp_amt,  # supply LP
             borrow_usdt_amt,  # borrow USDT
             borrow_weth_amt,  # borrow WETH
             0,  # borrow LP tokens
             0,  # min USDT
             0],  # min WETH
            pid,
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_chef = lp.balanceOf(chef)

    if interface.IUniswapV2Pair(lp).token0() == usdt:
        curARes, curBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    else:
        curBRes, curARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    print('spell lp balance', lp.balanceOf(sushiswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    _, _, _, totalDebt, totalShare = homora.getBankInfo(usdt)
    print('bank usdt totalDebt', totalDebt)
    print('bank usdt totalShare', totalShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('chef prev LP balance', prevLPBal_chef)
    print('chef cur LP balance', curLPBal_chef)

    print('prev usdt res', prevARes)
    print('cur usdt res', curARes)

    print('prev weth res', prevBRes)
    print('cur weth res', curBRes)

    # alice
    assert almostEqual(curABal - prevABal, -usdt_amt), 'incorrect USDT amt'
    assert almostEqual(curBBal - prevBBal, -weth_amt), 'incorrect WETH amt'
    assert curLPBal - prevLPBal == -lp_amt, 'incorrect LP amt'

    # spell
    assert usdt.balanceOf(sushiswap_spell) == 0, 'non-zero spell USDT balance'
    assert weth.balanceOf(sushiswap_spell) == 0, 'non-zero spell WETH balance'
    assert lp.balanceOf(sushiswap_spell) == 0, 'non-zero spell LP balance'
    assert totalDebt == borrow_usdt_amt

    # check balance and pool reserves
    assert curABal - prevABal - borrow_usdt_amt == - \
        (curARes - prevARes), 'not all USDT tokens go to LP pool'
    assert almostEqual(curBBal - prevBBal - borrow_weth_amt, -
                       (curBRes - prevBRes)), 'not all WETH tokens go to LP pool'

    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevSushi = sushi.balanceOf(bob)
    pid = 0
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    tx = interface.IMasterChef(chef).deposit(pid, collSize, {'from': bob})

    chain.sleep(20000)

    prevAliceSushiBalance = sushi.balanceOf(alice)
    print('Alice sushi balance', prevAliceSushiBalance)

    #####################################################################################
    print('=========================================================================')
    print('Case 2. add liquidity (failed tx desired)')

    usdc_amt = 10 * 10**6
    weth_amt = 10**18
    lp_amt = 0
    borrow_usdc_amt = 0
    borrow_weth_amt = 0

    pid = 0

    try:
        tx = homora.execute(
            1,
            sushiswap_spell,
            sushiswap_spell.addLiquidityWMasterChef.encode_input(
                usdc,  # token 0
                weth,  # token 1
                [usdc_amt,  # supply USDC
                 weth_amt,   # supply WETH
                 lp_amt,  # supply LP
                 borrow_usdc_amt,  # borrow USDC
                 borrow_weth_amt,  # borrow WETH
                 0,  # borrow LP tokens
                 0,  # min USDC
                 0],  # min WETH
                pid,
            ),
            {'from': alice}
        )
        assert False, 'tx not fail'
    except VirtualMachineError:
        pass

    #####################################################################################
    print('=========================================================================')
    print('Case 3. remove liquidity (failed tx desired)')

    lp_take_amt = collSize
    lp_want = 0
    usdc_repay = 0
    weth_repay = 0

    try:
        tx = homora.execute(
            1,
            sushiswap_spell,
            sushiswap_spell.removeLiquidityWMasterChef.encode_input(
                usdc,  # token 0
                weth,  # token 1
                [lp_take_amt,  # take out LP tokens
                 lp_want,   # withdraw LP tokens to wallet
                 usdc_repay,  # repay USDC
                 weth_repay,  # repay WETH
                 0,  # repay LP tokens
                 0,  # min USDC
                 0],  # min WETH
            ),
            {'from': alice}
        )
        assert False, 'tx not failed'
    except VirtualMachineError:
        pass

    #####################################################################################
    print('=========================================================================')
    print('Case 4. remove liquidity')

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_chef = lp.balanceOf(chef)
    prevETHBal = alice.balance()

    if interface.IUniswapV2Pair(lp).token0() == usdt:
        prevARes, prevBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    else:
        prevBRes, prevARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    lp_take_amt = collSize
    lp_want = 0
    usdt_repay = 0
    weth_repay = 0

    pid = 0

    tx = homora.execute(
        1,
        sushiswap_spell,
        sushiswap_spell.removeLiquidityWMasterChef.encode_input(
            usdt,  # token 0
            weth,  # token 1
            [lp_take_amt,  # take out LP tokens
             lp_want,   # withdraw LP tokens to wallet
             usdt_repay,  # repay USDT
             weth_repay,  # repay WETH
             0,  # repay LP tokens
             0,  # min USDT
             0],  # min WETH
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_chef = lp.balanceOf(chef)
    curETHBal = alice.balance()

    if interface.IUniswapV2Pair(lp).token0() == usdt:
        curARes, curBRes, _ = interface.IUniswapV2Pair(lp).getReserves()
    else:
        curBRes, curARes, _ = interface.IUniswapV2Pair(lp).getReserves()

    print('spell lp balance', lp.balanceOf(sushiswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    _, _, _, totalDebt, totalShare = homora.getBankInfo(usdt)
    print('bank usdt totalDebt', totalDebt)
    print('bank usdt totalShare', totalShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('chef prev LP balance', prevLPBal_chef)
    print('chef cur LP balance', curLPBal_chef)

    print('prev usdt res', prevARes)
    print('cur usdt res', curARes)

    print('prev weth res', prevBRes)
    print('cur weth res', curBRes)

    # alice
    assert almostEqual(curBBal - prevBBal, 0), 'incorrect WETH amt'
    assert almostEqual(curLPBal - prevLPBal, lp_want), 'incorrect LP amt'

    # chef
    assert almostEqual(curLPBal_chef - prevLPBal_chef, -
                       lp_take_amt), 'incorrect chef LP amt'

    # spell
    assert usdt.balanceOf(sushiswap_spell) == 0, 'non-zero spell USDT balance'
    assert weth.balanceOf(sushiswap_spell) == 0, 'non-zero spell WETH balance'
    assert lp.balanceOf(sushiswap_spell) == 0, 'non-zero spell LP balance'

    # check balance and pool reserves
    assert almostEqual(curABal - prevABal + usdt_repay, -
                       (curARes - prevARes)), 'inconsistent USDT from withdraw'
    assert almostEqual(curBBal - prevBBal,
                       0), 'inconsistent WETH from withdraw'
    assert almostEqual(curETHBal - prevETHBal + weth_repay, -
                       (curBRes - prevBRes)), 'inconsistent ETH from withdraw'

    curAliceSushiBalance = sushi.balanceOf(alice)
    print('Alice sushi balance', curAliceSushiBalance)
    receivedSushi = curAliceSushiBalance - prevAliceSushiBalance
    print('received sushi', receivedSushi)

    # check with staking directly
    pid = 0
    tx = interface.IMasterChef(chef).withdraw(pid, collSize, {'from': bob})
    receivedSushiFromStaking = sushi.balanceOf(bob) - prevSushi
    print('receivedSushiFromStaking', receivedSushiFromStaking)
    assert almostEqual(receivedSushi, receivedSushiFromStaking)
