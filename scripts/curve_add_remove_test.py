from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, ERC20KP3ROracle, SimpleOracle, CurveOracle, CurveSpellV1, WERC20
)


KP3R_ADDRESS = '0x73353801921417F465377c8d898c6f4C0270282C'


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
    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')

    lp = interface.IERC20Ex('0x6c3f90f043a72fa612cbac8115ee7e52bde6e490')
    pool = interface.ICurvePool('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7')

    crdai = interface.ICErc20('0x92B767185fB3B04F881e3aC8e5B0662a027A1D9f')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    crusdc = interface.ICErc20('0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322')

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([dai, usdt, usdc, lp], [9060553589188986552095106856227,
                                                   9002288773315920458132820329673073223442669,
                                                   9011535487953795006625883219171279625142296,
                                                   9002288773315920458132820329673])

    oracle = ProxyOracle.deploy({'from': admin})
    oracle.setWhitelistERC1155([werc20], True, {'from': admin})
    oracle.setOracles(
        [
            '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',  # USDC
            '0x6c3f90f043a72fa612cbac8115ee7e52bde6e490',  # lp
        ],
        [
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
        ],
        {'from': admin},
    )

    # initialize
    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)

    # add bank
    homora.addBank(dai, crdai, {'from': admin})
    homora.addBank(usdt, crusdt, {'from': admin})
    homora.addBank(usdc, crusdc, {'from': admin})

    # setup initial funds 10^6 USDT + 10^6 USDC + 10^6 DAI to alice
    setup_transfer(usdt, accounts.at('0xbe0eb53f46cd790cd13851d5eff43d12404d33e8',
                                     force=True), alice, 10**6 * 10**6)
    setup_transfer(usdc, accounts.at('0xa191e578a6736167326d05c119ce0c90849e84b7',
                                     force=True), alice, 10**6 * 10**6)
    setup_transfer(dai, accounts.at('0xc3d03e4f041fd4cd388c549ee2a29a9e5075882f',
                                    force=True), alice, 10**6 * 10**18)

    # setup initial funds 10^6 USDT + 10^6 USDC + 10^6 DAI to homora bank
    setup_transfer(usdt, accounts.at('0xbe0eb53f46cd790cd13851d5eff43d12404d33e8',
                                     force=True), homora, 10**6 * 10**6)
    setup_transfer(usdc, accounts.at('0x397ff1542f962076d0bfe58ea045ffa2d347aca0',
                                     force=True), homora, 10**6 * 10**6)
    setup_transfer(dai, accounts.at('0xc3d03e4f041fd4cd388c549ee2a29a9e5075882f',
                                    force=True), homora, 10**6 * 10**18)

    # check alice's funds
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')
    print(f'Alice usdc balance {usdc.balanceOf(alice)}')
    print(f'Alice dai balance {dai.balanceOf(alice)}')

    # steal some LP from the staking pool
    lp.transfer(alice, 10**6 * 10**18,
                {'from': accounts.at('0x8038c01a0390a8c547446a0b2c18fc9aefecc10c', force=True)})

    # set approval
    dai.approve(homora, 2**256-1, {'from': alice})
    dai.approve(crdai, 2**256-1, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    lp.approve(homora, 2**256-1, {'from': alice})

    curve_spell = CurveSpellV1.deploy(homora, werc20, {'from': admin})

    # add pools
    curve_spell.addPools(lp, [dai, usdt, usdc])
    curve_spell.addPoolOf(lp, pool)

    # first time call to reduce gas
    curve_spell.ensureApproveAll(lp, {'from': admin})

    #####################################################################################

    print('=========================================================================')
    print('Case 1.')

    prevABal = dai.balanceOf(alice)
    prevBBal = usdt.balanceOf(alice)
    prevCBal = usdc.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_werc20 = lp.balanceOf(werc20)

    dai_amt = 1  # 20000 * 10**18  # 20000 DAI
    usdt_amt = 0  # 40000 * 10**6  # 40000 USDT
    usdc_amt = 0  # 50000 * 10**6  # 50000 USDC
    lp_amt = 0  # 1 * 10**18
    borrow_dai_amt = 0  # 2000 * 10**18  # 2000 DAI
    borrow_usdt_amt = 0  # 1000 * 10**6  # 1000 USDT
    borrow_usdc_amt = 0  # 200 * 10**6  # 200 USDC
    borrow_lp_amt = 0

    tx = homora.execute(
        0,
        curve_spell,
        curve_spell.addLiquidity.encode_input(
            lp,  # LP
            [dai_amt, usdt_amt, usdc_amt],  # supply tokens
            lp_amt,  # supply LP
            [borrow_dai_amt, borrow_usdt_amt, borrow_usdc_amt],  # borrow tokens
            borrow_lp_amt,  # borrow LP
            [0, 0, 0]  # min amts
        ),
        {'from': alice}
    )

    position_id = tx.return_value
    print('position_id', position_id)
    return tx

    curABal = dai.balanceOf(alice)
    curBBal = usdt.balanceOf(alice)
    curCBal = usdc.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_werc20 = lp.balanceOf(werc20)

    print('spell lp balance', lp.balanceOf(curve_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('Alice delta C balance', curCBal - prevCBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    _, _, _, daiDebt, daiDebtShare = homora.getBankInfo(dai)
    _, _, _, usdtDebt, usdtDebtShare = homora.getBankInfo(usdt)
    _, _, _, usdcDebt, usdcDebtShare = homora.getBankInfo(usdc)
    _, _, _, lpDebt, usdcDebtShare = homora.getBankInfo(usdc)

    print('bank dai totalDebt', daiDebt)
    print('bank dai totalShare', daiDebtShare)

    print('bank usdt totalDebt', usdtDebt)
    print('bank usdt totalShare', usdtDebtShare)

    print('bank usdc totalDebt', usdcDebt)
    print('bank usdc totalShare', usdcDebtShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('werc20 prev LP balance', prevLPBal_werc20)
    print('werc20 cur LP balance', curLPBal_werc20)

    # alice
    assert almostEqual(curABal - prevABal, -dai_amt), 'incorrect DAI amt'
    assert almostEqual(curBBal - prevBBal, -usdt_amt), 'incorrect USDT amt'
    assert almostEqual(curCBal - prevCBal, -usdc_amt), 'incorrect USDC amt'
    assert almostEqual(curLPBal - prevLPBal, -lp_amt), 'incorrect LP amt'

    # spell
    assert dai.balanceOf(curve_spell) == 0, 'non-zero spell DAI balance'
    assert usdt.balanceOf(curve_spell) == 0, 'non-zero spell USDT balance'
    assert usdc.balanceOf(curve_spell) == 0, 'non-zero spell USDC balance'
    assert lp.balanceOf(curve_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert daiDebt == borrow_dai_amt
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

    _, _, _, collSize = homora.getPositionInfo(position_id)

    lp_take_amt = 2**256-1  # max
    lp_want = 1 * 10**5
    usdt_repay = 2**256-1  # max
    usdc_repay = 2**256-1  # max

    tx = homora.execute(
        position_id,
        uniswap_spell,
        uniswap_spell.removeLiquidity.encode_input(
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
