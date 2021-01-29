from brownie import (SafeBoxETH, IbETHRouterV2)
from brownie import accounts, interface, chain
from .utils import *
from math import sqrt


def almostEqual(a, b, thresh=0.01):
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def main():
    admin = accounts[0]
    alice = accounts[1]

    alpha = interface.IERC20Ex('0xa1faa113cbe53436df28ff0aee54275c13b40975')
    ibethv2 = SafeBoxETH.at('0xeEa3311250FE4c3268F8E684f7C87A82fF183Ec1')

    mint_tokens(alpha, alice)
    mint_tokens(alpha, admin)

    ibethv2.deposit({'from': alice, 'value': '100000 ether'})
    ibethv2.deposit({'from': admin, 'value': '100000 ether'})

    pair = interface.IUniswapV2Pair('0xf79a07cd3488BBaFB86dF1bAd09a6168D935c017')
    # sushi router
    router = interface.IUniswapV2Router02('0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f')

    ibethv2_router = IbETHRouterV2.deploy(alpha, ibethv2, router, {'from': admin})

    alpha.approve(ibethv2_router, 2**256-1, {'from': alice})
    ibethv2.approve(ibethv2_router, 2**256-1, {'from': alice})
    pair.approve(ibethv2_router, 2**256-1, {'from': alice})

    #######################################################################
    # setup liquidity first time

    init_alpha_amt = 1000 * 10**alpha.decimals()
    init_ibethv2_amt = 1 * 10**ibethv2.decimals()

    ibethv2.transfer(pair, init_ibethv2_amt, {'from': admin})
    alpha.transfer(pair, init_alpha_amt, {'from': admin})

    pair.mint(admin, {'from': admin})

    prevIbethv2Bal = ibethv2.balanceOf(admin)
    ibethv2.deposit({'from': admin, 'value': '1 ether'})
    curIbethv2Bal = ibethv2.balanceOf(admin)
    ibethv2_eth_rate = 10**18 / (curIbethv2Bal - prevIbethv2Bal)
    print('conversion rate', ibethv2_eth_rate)
    print('init ibethv2 amt', init_ibethv2_amt * ibethv2_eth_rate)
    print('deposited', 10**18, 'ether')
    print('received', curIbethv2Bal - prevIbethv2Bal, 'ibethv2')

    ########################################################################
    # check state vars
    print('=======================================')
    print('Case. check state vars')

    assert ibethv2_router.alpha() == alpha
    assert ibethv2_router.ibETHv2() == ibethv2
    assert ibethv2_router.lpToken() == pair
    assert ibethv2_router.router() == router

    #######################################################################
    # test swap exact ETH to ALPHA
    print('===========================================')
    print('Case. test swap exact eth to alpha')

    eth_amt = 10**12

    prevETHBal = alice.balance()
    prevAlphaBal = alpha.balanceOf(alice)

    ibethv2_router.swapExactETHToAlpha(
        0, alice, 2**256-1, {'from': alice, 'value': eth_amt, 'gas_price': 0})

    curETHBal = alice.balance()
    curAlphaBal = alpha.balanceOf(alice)

    print('∆ alpha', curAlphaBal - prevAlphaBal)
    print('calc alpha', eth_amt * (init_alpha_amt / init_ibethv2_amt) / ibethv2_eth_rate * 0.997)

    assert curETHBal - prevETHBal == -eth_amt, 'incorrect ETH amount'
    assert almostEqual(curAlphaBal - prevAlphaBal, eth_amt * (init_alpha_amt / init_ibethv2_amt) /
                       ibethv2_eth_rate * 0.997), 'incorrect alpha amount'

    #######################################################################
    # test swap exact ALPHA to ETH
    print('=========================================')
    print('Case. swap exact alpha to eth')

    alpha_amt = 10**18

    prevETHBal = alice.balance()
    prevAlphaBal = alpha.balanceOf(alice)

    ibethv2_router.swapExactAlphaToETH(
        alpha_amt, 0, alice, 2**256-1, {'from': alice, 'gas_price': 0}
    )

    curETHBal = alice.balance()
    curAlphaBal = alpha.balanceOf(alice)

    print('∆ eth', curETHBal - prevETHBal)
    print('calc eth', alpha_amt / (init_alpha_amt / init_ibethv2_amt) * ibethv2_eth_rate * 0.997)

    assert almostEqual(curETHBal - prevETHBal, alpha_amt / (init_alpha_amt / init_ibethv2_amt) *
                       ibethv2_eth_rate * 0.997), 'incorrect ETH amount'
    assert almostEqual(curAlphaBal - prevAlphaBal, -alpha_amt), 'incorrect alpha amount'

    #######################################################################
    # test add liquidity eth alpha optimal
    print('=========================================')
    print('Case. test add liquidity eth alpha optimal')

    alpha_amt = 100000 * 10**18
    eth_amt = 1000 * 10**18

    prevETHBal = alice.balance()
    prevAlphaBal = alpha.balanceOf(alice)
    prevLPBal = pair.balanceOf(alice)

    prevLPSupply = pair.totalSupply()
    r0, r1, _ = pair.getReserves()

    ibethv2_router.addLiquidityETHAlphaOptimal(
        alpha_amt, 0, alice, 2**256-1, {'from': alice, 'value': eth_amt, 'gas_price': 0})

    curETHBal = alice.balance()
    curAlphaBal = alpha.balanceOf(alice)
    curLPBal = pair.balanceOf(alice)

    new_r0, new_r1, _ = pair.getReserves()

    expected_lp = (sqrt((new_r0 * new_r1) / (r0 * r1)) - 1) * prevLPSupply

    print('prev total lp supply', prevLPSupply)
    print('prev reserves', r0, r1)
    print('cur reserves', new_r0, new_r1)
    print('∆ lp', curLPBal - prevLPBal)
    print('calc lp', expected_lp)

    assert almostEqual(new_r0, r0 + alpha_amt), 'incorrect r0 new amt'
    assert almostEqual(new_r1, r1 + eth_amt / ibethv2_eth_rate), 'incorrect r1 new amt'

    assert curETHBal - prevETHBal == -eth_amt, 'incorrect ETH add'
    assert curAlphaBal - prevAlphaBal == -alpha_amt, 'incorrect Alpha add'
    assert almostEqual(curLPBal - prevLPBal, expected_lp), 'incorrect LP received'

    # ###########################################################################
    # # test add liquidity ibethv2 alpha optimal
    print('=========================================')
    print('Case. test add liquidity ibethv2 alpha optimal')

    alpha_amt = 1000000 * 10**18
    ibethv2_amt = 1000 * 10**5

    prevETHBal = alice.balance()
    prevIbethv2Bal = ibethv2.balanceOf(alice)
    prevAlphaBal = alpha.balanceOf(alice)
    prevLPBal = pair.balanceOf(alice)

    prevLPSupply = pair.totalSupply()
    r0, r1, _ = pair.getReserves()

    ibethv2_router.addLiquidityIbETHv2AlphaOptimal(
        ibethv2_amt, alpha_amt, 0, alice, 2**256-1, {'from': alice, 'gas_price': 0})

    curETHBal = alice.balance()
    curAlphaBal = alpha.balanceOf(alice)
    curIbethv2Bal = ibethv2.balanceOf(alice)
    curLPBal = pair.balanceOf(alice)

    new_r0, new_r1, _ = pair.getReserves()
    expected_lp = (sqrt((new_r0 * new_r1) / (r0 * r1)) - 1) * prevLPSupply

    print('prev total lp supply', prevLPSupply)
    print('prev reserves', r0, r1)
    print('cur reserves', new_r0, new_r1)
    print('∆ lp', curLPBal - prevLPBal)
    print('calc lp', expected_lp)

    assert almostEqual(new_r0, r0 + alpha_amt), 'incorrect r0 new amt'
    assert almostEqual(new_r1, r1 + ibethv2_amt), 'incorrect r1 new amt'

    assert curIbethv2Bal - prevIbethv2Bal == -ibethv2_amt, 'incorrect ibethv2 add'
    assert curAlphaBal - prevAlphaBal == -alpha_amt, 'incorrect Alpha add'
    assert almostEqual(curLPBal - prevLPBal, expected_lp), 'incorrect LP received'

    ###############################################################################
    # test remove liquidity eth alpha
    print('===========================================')
    print('Case. test remove liquidity eth alpha')

    lp_amt = pair.balanceOf(alice) // 3

    prevETHBal = alice.balance()
    prevIbethv2Bal = ibethv2.balanceOf(alice)
    prevAlphaBal = alpha.balanceOf(alice)
    prevLPBal = pair.balanceOf(alice)

    prevLPSupply = pair.totalSupply()

    r0, r1, _ = pair.getReserves()  # token0 = alpha

    ibethv2_router.removeLiquidityETHAlpha(lp_amt, 0, 0, alice, 2**256-1, {'from': alice})

    curETHBal = alice.balance()
    curAlphaBal = alpha.balanceOf(alice)
    curIbethv2Bal = ibethv2.balanceOf(alice)
    curLPBal = pair.balanceOf(alice)

    print('∆ alpha', curAlphaBal - prevAlphaBal)
    print('∆ ibethv2', curIbethv2Bal - prevIbethv2Bal)

    assert curLPBal - prevLPBal == -lp_amt, 'incorrect LP withdraw'
    assert almostEqual(curAlphaBal - prevAlphaBal, lp_amt /
                       prevLPSupply * r0), 'incorrect alpha withdraw amount'
    assert almostEqual(curETHBal - prevETHBal, lp_amt /
                       prevLPSupply * r1 * ibethv2_eth_rate), 'incorrect eth withraw amount'

    ##################################################################################
    # test remove liquidity alpha only
    print('===============================================')
    print('Case. test remove liquidity alpha only')

    lp_amt = pair.balanceOf(alice) // 10**3

    prevETHBal = alice.balance()
    prevIbethv2Bal = ibethv2.balanceOf(alice)
    prevAlphaBal = alpha.balanceOf(alice)
    prevLPBal = pair.balanceOf(alice)

    prevLPSupply = pair.totalSupply()

    r0, r1, _ = pair.getReserves()  # token0 = alpha

    ibethv2_router.removeLiquidityAlphaOnly(lp_amt, 0, alice, 2**256-1, {'from': alice})

    curETHBal = alice.balance()
    curAlphaBal = alpha.balanceOf(alice)
    curIbethv2Bal = ibethv2.balanceOf(alice)
    curLPBal = pair.balanceOf(alice)

    assert curLPBal - prevLPBal == -lp_amt, 'incorrect LP withdraw'
    assert almostEqual(curAlphaBal - prevAlphaBal, lp_amt /
                       prevLPSupply * r0 * 2), 'incorrect alpha withdraw amount'
