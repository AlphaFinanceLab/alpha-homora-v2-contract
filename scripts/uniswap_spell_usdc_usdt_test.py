from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, CoreOracle, UniswapV2Oracle, UniswapV2SpellV1, SimpleOracle, WERC20, WMasterChef
)
from .utils import *


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


# add collateral for the bank
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
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')

    lp = interface.IERC20Ex('0x3041cbd36888becc7bbcbc0045e3b1f144466f5f')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    crusdc = interface.ICErc20('0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322')

    router = interface.IUniswapV2Router02(
        '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')

    chef = accounts.at(
        '0xc2edad668740f1aa35e4d8f227fb8e17dca888cd', force=True)
    wchef = WMasterChef.deploy(chef, {'from': admin})

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([usdt, usdc], [8343331721347310729683379470025550036595362,
                                          8344470555541464992529317899641128796042472])

    uniswap_oracle = UniswapV2Oracle.deploy(simple_oracle, {'from': admin})

    core_oracle = CoreOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy(core_oracle, {'from': admin})
    oracle.setWhitelistERC1155([werc20], True, {'from': admin})
    core_oracle.setRoute(
        [usdt, usdc, lp],
        [simple_oracle, simple_oracle, uniswap_oracle],
        {'from': admin},
    )
    oracle.setOracles(
        [usdt, usdc, lp],
        [
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
        ],
        {'from': admin},
    )

    # initialize
    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)

    # add bank
    homora.addBank(usdt, crusdt, {'from': admin})
    homora.addBank(usdc, crusdc, {'from': admin})

    # setup initial funds to alice
    mint_tokens(usdt, alice)
    mint_tokens(usdc, alice)

    # check alice's funds
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')
    print(f'Alice usdc balance {usdc.balanceOf(alice)}')

    # steal some LP from the staking pool
    mint_tokens(lp, alice)

    # set approval
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    lp.approve(homora, 2**256-1, {'from': alice})

    uniswap_spell = UniswapV2SpellV1.deploy(
        homora, werc20, router,  {'from': admin})
    # first time call to reduce gas
    uniswap_spell.getPair(usdt, usdc, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([uniswap_spell], [True], {'from': admin})

    # whitelist token in bank
    homora.setWhitelistTokens([usdt, usdc], [True, True], {'from': admin})

    # whitelist lp in spell
    uniswap_spell.setWhitelistLPTokens([lp], [True], {'from': admin})

    #####################################################################################

    print('=========================================================================')
    print('Case 1.')

    prevABal = usdt.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_werc20 = lp.balanceOf(werc20)

    usdt_amt = 40000 * 10**6  # 40000 USDT
    usdc_amt = 50000 * 10**6  # 50000 USDC
    lp_amt = 1 * 10**7
    borrow_usdt_amt = 1000 * 10**6  # 1000 USDT
    borrow_usdc_amt = 200 * 10**6  # 200 USDC

    tx = homora.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidityWERC20.encode_input(
            usdt,  # token 0
            usdc,  # token 1
            [usdt_amt,  # supply USDT
             usdc_amt,   # supply USDC
             lp_amt,  # supply LP
             borrow_usdt_amt,  # borrow USDT
             borrow_usdc_amt,  # borrow USDC
             0,  # borrow LP tokens
             0,  # min USDT
             0],  # min USDC
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_werc20 = lp.balanceOf(werc20)

    print('spell lp balance', lp.balanceOf(uniswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    _, _, _, usdtDebt, usdtDebtShare = homora.getBankInfo(usdt)
    _, _, _, usdcDebt, usdcDebtShare = homora.getBankInfo(usdc)
    print('bank usdt totalDebt', usdtDebt)
    print('bank usdt totalShare', usdtDebtShare)

    print('bank usdc totalDebt', usdcDebt)
    print('bank usdc totalShare', usdcDebtShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('werc20 prev LP balance', prevLPBal_werc20)
    print('werc20 cur LP balance', curLPBal_werc20)

    # alice
    assert almostEqual(curABal - prevABal, -usdt_amt), 'incorrect USDT amt'
    assert almostEqual(curBBal - prevBBal, -usdc_amt), 'incorrect USDC amt'
    assert almostEqual(curLPBal - prevLPBal, -lp_amt), 'incorrect LP amt'

    # spell
    assert usdt.balanceOf(uniswap_spell) == 0, 'non-zero spell USDT balance'
    assert usdc.balanceOf(uniswap_spell) == 0, 'non-zero spell USDC balance'
    assert lp.balanceOf(uniswap_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert usdtDebt == borrow_usdt_amt
    assert usdcDebt == borrow_usdc_amt

    #####################################################################################

    print('=========================================================================')
    print('Case 2.')

    # remove liquidity from the same position
    prevABal = usdt.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_werc20 = lp.balanceOf(werc20)

    _, _, _, collSize = homora.getPositionInfo(1)

    lp_take_amt = 2**256-1  # max
    lp_want = 1 * 10**5
    usdt_repay = 2**256-1  # max
    usdc_repay = 2**256-1  # max

    tx = homora.execute(
        1,
        uniswap_spell,
        uniswap_spell.removeLiquidityWERC20.encode_input(
            usdt,  # token 0
            usdc,  # token 1
            [lp_take_amt,  # take out LP tokens
             lp_want,   # withdraw LP tokens to wallet
             usdt_repay,  # repay USDT
             usdc_repay,   # repay USDC
             0,   # repay LP
             0,   # min USDT
             0],  # min USDC
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_werc20 = lp.balanceOf(werc20)

    print('spell lp balance', lp.balanceOf(uniswap_spell))
    print('spell usdt balance', usdt.balanceOf(uniswap_spell))
    print('spell usdc balance', usdc.balanceOf(uniswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('Alice delta LP balance', curLPBal - prevLPBal)
    print('remove liquidity gas', tx.gas_used)
    print('bank delta lp balance', curLPBal_bank - prevLPBal_bank)
    print('bank total lp balance', curLPBal_bank)

    _, _, _, usdtDebt, usdtDebtShare = homora.getBankInfo(usdt)
    _, _, _, usdcDebt, usdcDebtShare = homora.getBankInfo(usdc)
    print('bank usdt totalDebt', usdtDebt)
    print('bank usdt totalShare', usdtDebtShare)

    print('bank usdc totalDebt', usdcDebt)
    print('bank usdc totalShare', usdcDebtShare)

    print('LP want', lp_want)

    print('bank delta LP amount', curLPBal_bank - prevLPBal_bank)
    print('LP take amount', lp_take_amt)

    print('prev werc20 LP balance', prevLPBal_werc20)
    print('cur werc20 LP balance', curLPBal_werc20)

    print('coll size', collSize)

    # alice
    assert almostEqual(curLPBal - prevLPBal, lp_want), 'incorrect LP amt'

    # werc20
    assert almostEqual(curLPBal_werc20 - prevLPBal_werc20, -
                       collSize), 'incorrect werc20 LP amt'

    # spell
    assert usdt.balanceOf(uniswap_spell) == 0, 'non-zero spell USDT balance'
    assert usdc.balanceOf(uniswap_spell) == 0, 'non-zero spell USDC balance'
    assert lp.balanceOf(uniswap_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert usdtDebt == 0, 'usdtDebt should be 0'
    assert usdcDebt == 0, 'usdcDebt should be 0'

    return tx
