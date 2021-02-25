from brownie import accounts, interface, Contract, chain
from brownie import (HomoraBank, ProxyOracle, CoreOracle, BalancerPairOracle,
                     SimpleOracle, BalancerSpellV1, WERC20, MockCErc20, WStakingRewards)
from .utils import *
from brownie.exceptions import VirtualMachineError


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
    dfd = interface.IERC20Ex('0x20c36f062a31865bED8a5B1e512D9a1A20AA333A')
    dusd = interface.IERC20Ex('0x5BC25f649fc4e26069dDF4cF4010F9f706c23831')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')

    lp = interface.IERC20Ex('0xd8e9690eff99e21a2de25e0b148ffaf47f47c972')

    # pool is lp for balancer
    pool = interface.IBalancerPool('0xd8e9690eff99e21a2de25e0b148ffaf47f47c972')
    lp_dai = interface.IERC20Ex('0x8b6e6e7b5b3801fed2cafd4b22b8a16c2f2db21a')
    pool_dai = interface.IBalancerPool('0x8b6e6e7b5b3801fed2cafd4b22b8a16c2f2db21a')

    crdfd = MockCErc20.deploy(dfd, {'from': admin})
    crdusd = MockCErc20.deploy(dusd, {'from': admin})
    crdai = MockCErc20.deploy(dai, {'from': admin})
    crweth = MockCErc20.deploy(weth, {'from': admin})

    werc20 = WERC20.deploy({'from': admin})

    staking = accounts.at('0xf068236ecad5fabb9883bbb26a6445d6c7c9a924', force=True)

    wstaking = WStakingRewards.deploy(staking, lp, dfd, {'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([dfd, dusd], [2**112 // 2 // 700, 2**112 * 2 // 700])

    balancer_oracle = BalancerPairOracle.deploy(simple_oracle, {'from': alice})

    core_oracle = CoreOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy(core_oracle, {'from': admin})
    oracle.setWhitelistERC1155([werc20, wstaking], True, {'from': admin})
    core_oracle.setRoute(
        [dfd, dusd, lp],
        [simple_oracle, simple_oracle, balancer_oracle],
        {'from': admin},
    )
    oracle.setOracles(
        [dfd, dusd, lp],
        [
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
        ],
        {'from': admin},
    )

    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)
    homora.addBank(dfd, crdfd, {'from': admin})
    homora.addBank(dusd, crdusd, {'from': admin})

    # setup initial funds to alice
    mint_tokens(dfd, alice)
    mint_tokens(dusd, alice)

    mint_tokens(weth, alice)
    mint_tokens(dai, alice)

    mint_tokens(dfd, crdfd)

    # check alice's funds
    print(f'Alice dusd balance {dusd.balanceOf(alice)}')
    print(f'Alice dfd balance {dfd.balanceOf(alice)}')

    # Steal some LP from the staking pool
    mint_tokens(lp, alice)
    mint_tokens(lp, bob)

    # set approval
    dfd.approve(homora, 2**256-1, {'from': alice})
    dfd.approve(crdfd, 2**256-1, {'from': alice})
    dusd.approve(homora, 2**256-1, {'from': alice})
    dusd.approve(crdusd, 2**256-1, {'from': alice})
    dai.approve(homora, 2**256-1, {'from': alice})
    dai.approve(crdai, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})
    weth.approve(crweth, 2**256-1, {'from': alice})

    lp.approve(homora, 2**256-1, {'from': alice})
    lp.approve(staking, 2**256-1, {'from': bob})

    balancer_spell = BalancerSpellV1.deploy(
        homora, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', {'from': admin})
    # first time call to reduce gas
    balancer_spell.getPair(lp, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([balancer_spell], [True], {'from': admin})

    # whitelist lp in spell
    balancer_spell.setWhitelistLPTokens([lp, lp_dai], [True, True], {'from': admin})

    #####################################################################################
    print('=========================================================================')
    print('Case 1.')

    prevABal = dfd.balanceOf(alice)
    prevBBal = dusd.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_staking = lp.balanceOf(staking)

    prevARes = interface.IBalancerPool(lp).getBalance(dfd)
    prevBRes = interface.IBalancerPool(lp).getBalance(dusd)

    dfd_amt = 100 * 10**18
    dusd_amt = 10 ** 18
    lp_amt = 0
    borrow_dfd_amt = 0
    borrow_dusd_amt = 0

    # calculate slippage control
    total_dfd_amt = dfd_amt + borrow_dfd_amt
    total_dusd_amt = dusd_amt + borrow_dusd_amt
    dfd_weight = 0.58
    dusd_weight = 0.42

    ratio = (((prevARes + total_dfd_amt) / prevARes) ** dfd_weight) * \
        (((prevBRes + total_dusd_amt) / prevBRes) ** dusd_weight) - 1
    lp_desired = lp_amt + int(interface.IERC20(lp).totalSupply() * ratio * 0.995)
    print('lp desired', lp_desired)

    tx = homora.execute(
        0,
        balancer_spell,
        balancer_spell.addLiquidityWStakingRewards.encode_input(
            lp,  # lp token
            [dfd_amt,  # supply DFD
             dusd_amt,   # supply DUSD
             lp_amt,  # supply LP
             borrow_dfd_amt,  # borrow DFD
             borrow_dusd_amt,  # borrow DUSD
             0,  # borrow LP tokens
             lp_desired],  # LP desired
            wstaking
        ),
        {'from': alice}
    )

    curABal = dfd.balanceOf(alice)
    curBBal = dusd.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_staking = lp.balanceOf(staking)

    curARes = interface.IBalancerPool(lp).getBalance(dfd)
    curBRes = interface.IBalancerPool(lp).getBalance(dusd)

    print('spell lp balance', lp.balanceOf(balancer_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    _, _, _, dfdDebt, dfdShare = homora.getBankInfo(dfd)
    print('bank dfd dfdDebt', dfdDebt)
    print('bank dfd dfdShare', dfdShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('staking prev LP balance', prevLPBal_staking)
    print('staking cur LP balance', curLPBal_staking)

    print('prev dfd res', prevARes)
    print('cur dfd res', curARes)

    print('prev dusd res', prevBRes)
    print('cur dusd res', curBRes)

    # alice
    assert almostEqual(curABal - prevABal, -dfd_amt), 'incorrect DFD amt'
    assert almostEqual(curBBal - prevBBal, -dusd_amt), 'incorrect DUSD amt'
    assert curLPBal - prevLPBal == -lp_amt, 'incorrect LP amt'

    # spell
    assert dfd.balanceOf(balancer_spell) == 0, 'non-zero spell DFD balance'
    assert dusd.balanceOf(balancer_spell) == 0, 'non-zero spell DUSD balance'
    assert lp.balanceOf(balancer_spell) == 0, 'non-zero spell LP balance'
    assert dfdDebt == borrow_dfd_amt

    # check balance and pool reserves
    assert almostEqual(curABal - prevABal - borrow_dfd_amt, -
                       (curARes - prevARes)), 'not all DFD tokens go to LP pool'
    assert almostEqual(curBBal - prevBBal - borrow_dusd_amt, -
                       (curBRes - prevBRes)), 'not all DUSD tokens go to LP pool'

    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevDfd = dfd.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    tx = interface.IStakingRewards(staking).stake(collSize, {'from': bob})

    chain.sleep(20000)

    prevAliceDfdBalance = dfd.balanceOf(alice)
    print('Alice dfd balance', prevAliceDfdBalance)

    #####################################################################################
    print('=========================================================================')
    print('Case 2. add liquidity (failed tx desired)')

    weth_amt = 100 * 10**18
    dai_amt = 10 ** 18
    lp_amt = 0
    borrow_weth_amt = 0
    borrow_dai_amt = 0

    # calculate slippage control
    total_weth_amt = weth_amt + borrow_weth_amt
    total_dai_amt = dai_amt + borrow_dai_amt
    dfd_weight = 0.8
    dusd_weight = 0.2

    ratio = (((prevARes + total_weth_amt) / prevARes) ** dfd_weight) * \
        (((prevBRes + total_dai_amt) / prevBRes) ** dusd_weight) - 1
    lp_desired = lp_amt + int(interface.IERC20(lp).totalSupply() * ratio * 0.995)
    lp_desired = 0
    print('lp desired', lp_desired)

    try:
        tx = homora.execute(
            1,
            balancer_spell,
            balancer_spell.addLiquidityWStakingRewards.encode_input(
                lp_dai,  # lp token
                [weth_amt,  # supply DFD
                 dai_amt,   # supply DUSD
                 lp_amt,  # supply LP
                 borrow_weth_amt,  # borrow DFD
                 borrow_dai_amt,  # borrow DUSD
                 0,  # borrow LP tokens
                 lp_desired],  # LP desired
                wstaking
            ),
            {'from': alice}
        )
        assert False, 'tx should fail'
    except VirtualMachineError:
        pass

    #####################################################################################
    print('=========================================================================')
    print('Case 3. remove liquidity (failed tx desired)')

    lp_take_amt = 2**256-1  # max
    lp_want = 0
    weth_repay = 2**256-1  # max
    dai_repay = 2**256-1  # max

    real_weth_repay = homora.borrowBalanceStored(1, dfd)
    _, _, _, real_lp_take_amt = homora.getPositionInfo(1)

    expected_withdraw_dfd = collSize * prevARes // interface.IBalancerPool(lp).totalSupply()
    print('expected withdraw DFD', expected_withdraw_dfd)

    try:
        tx = homora.execute(
            1,
            balancer_spell,
            balancer_spell.removeLiquidityWStakingRewards.encode_input(
                lp_dai,  # LP token
                [lp_take_amt,  # take out LP tokens
                 lp_want,   # withdraw LP tokens to wallet
                 weth_repay,  # repay DFD
                 dai_repay,   # repay DUSD
                 0,   # repay LP
                 0,   # min DFD
                 0],  # min DUSD
                wstaking
            ),
            {'from': alice}
        )
        assert False, 'tx should fail'
    except VirtualMachineError:
        pass

    #####################################################################################
    print('=========================================================================')
    print('Case 4. remove liquidity')

    # remove liquidity from the same position
    prevABal = dfd.balanceOf(alice)
    prevBBal = dusd.balanceOf(alice)
    prevETHBal = alice.balance()
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_staking = lp.balanceOf(staking)
    prevETHBal = alice.balance()
    prevCrdfdBal = lp.balanceOf(crdfd)

    prevARes = interface.IBalancerPool(lp).getBalance(dfd)
    prevBRes = interface.IBalancerPool(lp).getBalance(dusd)

    lp_take_amt = 2**256-1  # max
    lp_want = 0
    dfd_repay = 2**256-1  # max
    dusd_repay = 0

    real_dfd_repay = homora.borrowBalanceStored(1, dfd)
    _, _, _, real_lp_take_amt = homora.getPositionInfo(1)

    expected_withdraw_dfd = collSize * prevARes // interface.IBalancerPool(lp).totalSupply()
    print('expected withdraw DFD', expected_withdraw_dfd)

    tx = homora.execute(
        1,
        balancer_spell,
        balancer_spell.removeLiquidityWStakingRewards.encode_input(
            lp,  # LP token
            [lp_take_amt,  # take out LP tokens
             lp_want,   # withdraw LP tokens to wallet
             dfd_repay,  # repay DFD
             dusd_repay,   # repay DUSD
             0,   # repay LP
             0,   # min DFD
             0],  # min DUSD
            wstaking
        ),
        {'from': alice}
    )

    curABal = dfd.balanceOf(alice)
    curBBal = dusd.balanceOf(alice)
    curETHBal = alice.balance()
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_staking = lp.balanceOf(staking)
    curETHBal = alice.balance()
    curCrdfdBal = lp.balanceOf(crdfd)

    curARes = interface.IBalancerPool(lp).getBalance(dfd)
    curBRes = interface.IBalancerPool(lp).getBalance(dusd)

    print('spell lp balance', lp.balanceOf(balancer_spell))
    print('spell dfd balance', dfd.balanceOf(balancer_spell))
    print('spell dusd balance', dusd.balanceOf(balancer_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('Alice delta ETH balance', curETHBal - prevETHBal)
    print('Alice delta LP balance', curLPBal - prevLPBal)
    print('remove liquidity gas', tx.gas_used)
    print('bank delta lp balance', curLPBal_bank - prevLPBal_bank)
    print('bank total lp balance', curLPBal_bank)

    _, _, _, dfdDebt, dfdShare = homora.getBankInfo(dfd)
    print('bank dfd totalDebt', dfdDebt)
    print('bank dfd totalShare', dfdShare)

    print('LP want', lp_want)

    print('bank delta LP amount', curLPBal_bank - prevLPBal_bank)
    print('LP take amount', lp_take_amt)

    print('prev staking LP balance', prevLPBal_staking)
    print('cur staking LP balance', curLPBal_staking)

    print('real dfd repay', real_dfd_repay)

    print('curCrdfdBal', curCrdfdBal)
    print('delta crdfd', curCrdfdBal - prevCrdfdBal)

    print('A res delta', prevARes - curARes)
    print('B res delta', prevBRes - curBRes)

    # alice
    assert almostEqual(curLPBal - prevLPBal, lp_want), 'incorrect LP amt'

    # staking
    assert almostEqual(curLPBal_staking - prevLPBal_staking, -
                       real_lp_take_amt), 'incorrect staking LP amt'

    # spell
    assert dfd.balanceOf(balancer_spell) == 0, 'non-zero spell DFD balance'
    assert dusd.balanceOf(balancer_spell) == 0, 'non-zero spell DUSD balance'
    assert lp.balanceOf(balancer_spell) == 0, 'non-zero spell LP balance'

    # check balance and pool reserves
    assert almostEqual(curABal - prevABal + real_dfd_repay, -
                       (curARes - prevARes)), 'inconsistent DFD from withdraw'
    assert almostEqual(curBBal - prevBBal + dusd_repay, -(curBRes - prevBRes)
                       ), 'inconsistent DUSD from withdraw'

    curAliceDfdBalance = dfd.balanceOf(alice)
    print('Alice dfd balance', curAliceDfdBalance)
    receivedDfd = curAliceDfdBalance - prevAliceDfdBalance + real_dfd_repay - (prevARes - curARes)
    print('received dfd', receivedDfd)

    # check with staking directly
    tx = interface.IStakingRewards(staking).getReward({'from': bob})
    receivedDfdFromStaking = dfd.balanceOf(bob) - prevDfd
    print('receivedDfdFromStaking', receivedDfdFromStaking)
    assert almostEqual(receivedDfd, receivedDfdFromStaking)

    return tx
