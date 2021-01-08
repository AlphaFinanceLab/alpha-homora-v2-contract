from brownie import accounts, interface, Contract, chain
from brownie import (
    WStakingRewards
)
from .utils import *


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def setup_transfer(asset, fro, to, amt):
    print(f'sending from {fro} {amt} {asset.name()} to {to}')
    asset.transfer(to, amt, {'from': fro})


def main():
    admin = accounts[0]
    alice = accounts[1]

    perp = interface.IERC20Ex('0xbC396689893D065F41bc2C6EcbeE5e0085233447')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')

    bpt = interface.IERC20Ex(
        '0xf54025af2dc86809be1153c1f20d77adb7e8ecf4')  # perp-usdc

    staking = accounts.at(
        '0xb9840a4a8a671f79de3df3b812feeb38047ce552', force=True)

    wstaking = WStakingRewards.deploy(staking, bpt, perp, {'from': admin})

    perp.approve(staking, 2**256-1, {'from': alice})
    usdc.approve(staking, 2**256-1, {'from': alice})
    bpt.approve(staking, 2**256-1, {'from': alice})
    perp.approve(wstaking, 2**256-1, {'from': alice})
    usdc.approve(wstaking, 2**256-1, {'from': alice})
    bpt.approve(wstaking, 2**256-1, {'from': alice})

    # setup initial funds to alice
    mint_tokens(perp, alice)
    mint_tokens(usdc, alice)
    mint_tokens(bpt, alice)

    ######################################################################
    # check getUnderlyingToken
    print('===========================================================')
    print('Case 1.')

    underlying = wstaking.getUnderlyingToken(0)
    assert underlying == bpt

    ######################################################################
    # check mint & burn
    print('===========================================================')
    print('Case 2.')
    amt = 10**2 * 10**18

    prevBPTBalance = bpt.balanceOf(alice)
    tx = wstaking.mint(amt, {'from':  alice})
    curBPTBalance = bpt.balanceOf(alice)
    stRewardPerToken = interface.IStakingRewards(staking).rewardPerToken()

    token_id = tx.return_value
    print('alice bpt balance', curBPTBalance)
    assert curBPTBalance - prevBPTBalance == -amt

    chain.sleep(5000)

    prevPerpBalance = perp.balanceOf(alice)
    prevBPTBalance = bpt.balanceOf(alice)
    tx = wstaking.burn(token_id, amt, {'from': alice})
    curBPTBalance = bpt.balanceOf(alice)
    curPerpBalance = perp.balanceOf(alice)
    enRewardPerToken = interface.IStakingRewards(staking).rewardPerToken()

    print('alice bpt balance', curBPTBalance)
    print('alice perp balance', curPerpBalance)
    assert curBPTBalance - prevBPTBalance == amt
    print('perp gained', curPerpBalance - prevPerpBalance)
    print('perp calculated reward',
          (enRewardPerToken - stRewardPerToken) * amt // (10**18))
    assert almostEqual(curPerpBalance - prevPerpBalance,
                       (enRewardPerToken - stRewardPerToken) * amt // (10**18))

    # check perp gained with directly staking (using large chain sleep time)
    prevReward = perp.balanceOf(alice)
    tx = interface.IStakingRewards(staking).stake(amt, {'from': alice})

    chain.sleep(5000)

    tx = interface.IStakingRewards(staking).withdraw(amt, {'from': alice})

    tx = interface.IStakingRewards(staking).getReward({'from': alice})
    curReward = perp.balanceOf(alice)
    print('perp gained from directly staking', curReward - prevReward)
    assert almostEqual(curPerpBalance - prevPerpBalance,
                       curReward - prevReward)

    ######################################################################
    # check mint & burn max_int
    print('===========================================================')
    print('Case 3.')
    amt = 10**2 * 10**18

    prevBPTBalance = bpt.balanceOf(alice)
    tx = wstaking.mint(amt, {'from':  alice})
    curBPTBalance = bpt.balanceOf(alice)
    stRewardPerToken = interface.IStakingRewards(staking).rewardPerToken()

    token_id = tx.return_value
    print('alice bpt balance', curBPTBalance)
    assert curBPTBalance - prevBPTBalance == -amt

    chain.sleep(5000)

    prevPerpBalance = perp.balanceOf(alice)
    prevBPTBalance = bpt.balanceOf(alice)
    tx = wstaking.burn(token_id, 2**256-1, {'from': alice})
    curBPTBalance = bpt.balanceOf(alice)
    curPerpBalance = perp.balanceOf(alice)
    enRewardPerToken = interface.IStakingRewards(staking).rewardPerToken()

    print('alice bpt balance', curBPTBalance)
    print('alice perp balance', curPerpBalance)
    assert curBPTBalance - prevBPTBalance == amt
    print('perp gained', curPerpBalance - prevPerpBalance)
    print('perp calculated reward',
          (enRewardPerToken - stRewardPerToken) * amt // (10**18))
    assert almostEqual(curPerpBalance - prevPerpBalance,
                       (enRewardPerToken - stRewardPerToken) * amt // (10**18))

    # check perp gained with directly staking (using large chain sleep time)
    prevReward = perp.balanceOf(alice)
    tx = interface.IStakingRewards(staking).stake(amt, {'from': alice})

    chain.sleep(5000)

    tx = interface.IStakingRewards(staking).withdraw(amt, {'from': alice})

    tx = interface.IStakingRewards(staking).getReward({'from': alice})
    curReward = perp.balanceOf(alice)
    print('perp gained from directly staking', curReward - prevReward)
    assert almostEqual(curPerpBalance - prevPerpBalance,
                       curReward - prevReward)

    ######################################################################
    # check mint & burn (try more than available--revert, half, then remaining)
    print('===========================================================')
    print('Case 4.')
    amt = 10**2 * 10**18

    prevBPTBalance = bpt.balanceOf(alice)
    tx = wstaking.mint(amt, {'from':  alice})
    curBPTBalance = bpt.balanceOf(alice)
    stRewardPerToken = interface.IStakingRewards(staking).rewardPerToken()

    token_id = tx.return_value
    print('alice bpt balance', curBPTBalance)
    assert curBPTBalance - prevBPTBalance == -amt

    try:
        tx = wstaking.burn(token_id, amt + 1, {'from': alice})
        assert tx.status == 0
    except:
        pass

    chain.sleep(5000)

    prevPerpBalance = perp.balanceOf(alice)
    prevBPTBalance = bpt.balanceOf(alice)
    tx = wstaking.burn(token_id, amt // 2, {'from': alice})

    interRewardPerToken = interface.IStakingRewards(staking).rewardPerToken()

    chain.sleep(5000)

    tx = wstaking.burn(token_id, 2**256-1, {'from': alice})
    curBPTBalance = bpt.balanceOf(alice)
    curPerpBalance = perp.balanceOf(alice)
    enRewardPerToken = interface.IStakingRewards(staking).rewardPerToken()

    print('perp gained', curPerpBalance - prevPerpBalance)
    print('perp calc reward', (interRewardPerToken - stRewardPerToken) * (amt // 2) // (10**18) +
          (enRewardPerToken - stRewardPerToken) * (amt - amt//2) // (10**18))
    assert almostEqual(curPerpBalance - prevPerpBalance,
                       (interRewardPerToken - stRewardPerToken) * (amt // 2) // (10**18) +
                       (enRewardPerToken - stRewardPerToken) * (amt - amt//2) // (10**18))

    # check perp gained with directly staking (using large chain sleep time)
    prevReward = perp.balanceOf(alice)
    tx = interface.IStakingRewards(staking).stake(amt, {'from': alice})

    chain.sleep(5000)

    tx = interface.IStakingRewards(staking).withdraw(amt//2, {'from': alice})

    chain.sleep(5000)

    tx = interface.IStakingRewards(staking).withdraw(
        amt-amt//2, {'from': alice})

    tx = interface.IStakingRewards(staking).getReward({'from': alice})
    curReward = perp.balanceOf(alice)
    print('perp gained from wstaking', curPerpBalance - prevPerpBalance)
    print('perp gained from directly staking', curReward - prevReward)
    assert almostEqual(curPerpBalance - prevPerpBalance,
                       curReward - prevReward)
