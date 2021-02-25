from brownie import accounts, interface, Contract, chain
from brownie import (HomoraBank, ProxyOracle, CoreOracle, BalancerPairOracle,
                     SimpleOracle, BalancerSpellV1, WERC20, MockCErc20, WStakingRewards)
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
    dfd = interface.IERC20Ex('0x20c36f062a31865bED8a5B1e512D9a1A20AA333A')
    dusd = interface.IERC20Ex('0x5BC25f649fc4e26069dDF4cF4010F9f706c23831')

    lp = interface.IERC20Ex('0xd8e9690eff99e21a2de25e0b148ffaf47f47c972')
    # pool is lp for balancer
    pool = interface.IBalancerPool('0xd8e9690eff99e21a2de25e0b148ffaf47f47c972')

    crdfd = MockCErc20.deploy(dfd, {'from': admin})
    crdusd = MockCErc20.deploy(dusd, {'from': admin})

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
    lp.approve(homora, 2**256-1, {'from': alice})
    lp.approve(staking, 2**256-1, {'from': bob})

    balancer_spell = BalancerSpellV1.deploy(
        homora, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', {'from': admin})
    # first time call to reduce gas
    balancer_spell.getPair(lp, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([balancer_spell], [True], {'from': admin})

    # whitelist lp in spell
    balancer_spell.setWhitelistLPTokens([lp], [True], {'from': admin})

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

    # #####################################################################################

    print('=========================================================================')
    print('Case 2. harvest first time')

    prevDfdBalance = dfd.balanceOf(alice)
    print('Alice DFD balance before harvest', prevDfdBalance)
    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevDfd = dfd.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    tx = interface.IStakingRewards(staking).stake(collSize, {'from': bob})

    chain.sleep(20000)

    tx = homora.execute(
        1,
        balancer_spell,
        balancer_spell.harvestWStakingRewards.encode_input(wstaking),
        {'from': alice}
    )

    print('tx gas used', tx.gas_used)

    curDfdBalance = dfd.balanceOf(alice)
    print('Alice DFD balance after harvest', curDfdBalance)
    receivedDfd = curDfdBalance - prevDfdBalance

    # check with staking directly
    tx = interface.IStakingRewards(staking).getReward({'from': bob})
    receivedDfdFromStaking = dfd.balanceOf(bob) - prevDfd
    print('receivedDfdFromStaking', receivedDfdFromStaking)
    assert almostEqual(receivedDfd, receivedDfdFromStaking)

    # #####################################################################################

    print('=========================================================================')
    print('Case 3. harvest second time')

    prevDfdBalance = dfd.balanceOf(alice)
    print('Alice DFD balance before harvest', prevDfdBalance)

    # staking directly
    prevDfd = dfd.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))

    chain.sleep(20000)

    tx = homora.execute(
        1,
        balancer_spell,
        balancer_spell.harvestWStakingRewards.encode_input(wstaking),
        {'from': alice}
    )

    print('tx gas used', tx.gas_used)

    curDfdBalance = dfd.balanceOf(alice)
    print('Alice DFD balance after harvest', curDfdBalance)
    receivedDfd = curDfdBalance - prevDfdBalance

    # check with staking directly
    tx = interface.IStakingRewards(staking).getReward({'from': bob})
    receivedDfdFromStaking = dfd.balanceOf(bob) - prevDfd
    print('receivedDfdFromStaking', receivedDfdFromStaking)
    assert almostEqual(receivedDfd, receivedDfdFromStaking)
