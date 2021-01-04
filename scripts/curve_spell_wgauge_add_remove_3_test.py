from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, ERC20KP3ROracle, SimpleOracle, CurveOracle, CurveSpellV1, WERC20, WLiquidityGauge, MockCErc20
)
import brownie
from brownie.exceptions import VirtualMachineError


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
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')

    lp = interface.IERC20Ex('0x6c3f90f043a72fa612cbac8115ee7e52bde6e490')
    pool = interface.ICurvePool('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7')
    registry = interface.ICurveRegistry(
        '0x7d86446ddb609ed0f5f8684acf30380a356b2b4c')

    crdai = interface.ICErc20('0x92B767185fB3B04F881e3aC8e5B0662a027A1D9f')
    crusdc = interface.ICErc20('0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')

    gauge = accounts.at(
        '0xbFcF63294aD7105dEa65aA58F8AE5BE2D9d0952A', force=True)
    wgauge = WLiquidityGauge.deploy(
        registry, '0xD533a949740bb3306d119CC777fa900bA034cd52', {'from': admin})

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([dai, usdt, usdc], [9060553589188986552095106856227,
                                               9002288773315920458132820329673073223442669,
                                               9011535487953795006625883219171279625142296])

    curve_oracle = CurveOracle.deploy(simple_oracle, registry, {'from': admin})
    curve_oracle.registerPool(lp)  # update pool info

    oracle = ProxyOracle.deploy({'from': admin})
    oracle.setWhitelistERC1155([werc20, wgauge], True, {'from': admin})
    oracle.setOracles(
        [
            '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
            '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',  # USDC
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '0x6c3f90f043a72fa612cbac8115ee7e52bde6e490',  # lp
        ],
        [
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
            [curve_oracle, 10000, 10000, 10000],
        ],
        {'from': admin},
    )

    # initialize
    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)

    # add bank
    homora.addBank(dai, crdai, {'from': admin})
    homora.addBank(usdc, crusdc, {'from': admin})
    homora.addBank(usdt, crusdt, {'from': admin})

    # setup initial funds 10^6 USDT + 10^6 USDC + 10^6 DAI to alice
    setup_transfer(dai, accounts.at('0xc3d03e4f041fd4cd388c549ee2a29a9e5075882f',
                                    force=True), alice, 10**6 * 10**18)
    setup_transfer(usdc, accounts.at('0xa191e578a6736167326d05c119ce0c90849e84b7',
                                     force=True), alice, 10**6 * 10**6)
    setup_transfer(usdt, accounts.at('0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503',
                                     force=True), alice, 10**6 * 10**6)

    # setup initial funds 10^6 USDT + 10^6 USDC + 10^6 DAI to homora bank
    setup_transfer(dai, accounts.at('0xc3d03e4f041fd4cd388c549ee2a29a9e5075882f',
                                    force=True), homora, 10**6 * 10**18)
    setup_transfer(usdc, accounts.at('0x397ff1542f962076d0bfe58ea045ffa2d347aca0',
                                     force=True), homora, 10**6 * 10**6)
    setup_transfer(usdt, accounts.at('0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503',
                                     force=True), homora, 10**6 * 10**6)

    # check alice's funds
    print(f'Alice dai balance {dai.balanceOf(alice)}')
    print(f'Alice usdc balance {usdc.balanceOf(alice)}')
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')

    # steal some LP from the staking pool
    lp.transfer(alice, 10**6 * 10**18,
                {'from': accounts.at('0x8038c01a0390a8c547446a0b2c18fc9aefecc10c', force=True)})

    # set approval
    dai.approve(homora, 2**256-1, {'from': alice})
    dai.approve(crdai, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    lp.approve(homora, 2**256-1, {'from': alice})

    curve_spell = CurveSpellV1.deploy(
        homora, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', wgauge, {'from': admin})

    # register gauge
    wgauge.registerGauge(0, 0)

    # set up pools
    curve_spell.getPool(lp)

    # first time call to reduce gas
    curve_spell.ensureApproveN(lp, 3, {'from': admin})

    #####################################################################################

    # TODO: Test borrow 3 assets simultaneously
    print('=========================================================================')
    print('Case 1.')

    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevCBal = usdt.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    dai_amt = 20000 * 10**18  # 20000 DAI
    usdc_amt = 50000 * 10**6  # 50000 USDC
    usdt_amt = 40000 * 10**6  # 40000 USDT
    lp_amt = 1 * 10**18
    borrow_dai_amt = 0  # 2000 * 10**18  # 2000 DAI
    borrow_usdc_amt = 200 * 10**6  # 200 USDC
    borrow_usdt_amt = 0  # 1000 * 10**6  # 1000 USDT
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 0
    gid = 0

    tx = homora.execute(
        0,
        curve_spell,
        curve_spell.addLiquidity3.encode_input(
            lp,  # LP
            [dai_amt, usdc_amt, usdt_amt],  # supply tokens
            lp_amt,  # supply LP
            [borrow_dai_amt, borrow_usdc_amt, borrow_usdt_amt],  # borrow tokens
            borrow_lp_amt,  # borrow LP
            minLPMint,  # min LP mint
            pid,
            gid
        ),
        {'from': alice}
    )

    position_id = tx.return_value
    print('position_id', position_id)
    print('tx gas used', tx.gas_used)

    curABal = dai.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curCBal = usdt.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_gauge = lp.balanceOf(gauge)

    print('spell lp balance', lp.balanceOf(curve_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('Alice delta C balance', curCBal - prevCBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    _, _, _, daiDebt, daiDebtShare = homora.getBankInfo(dai)
    _, _, _, usdcDebt, usdcDebtShare = homora.getBankInfo(usdc)
    _, _, _, usdtDebt, usdtDebtShare = homora.getBankInfo(usdt)
    _, _, _, lpDebt, usdcDebtShare = homora.getBankInfo(usdc)

    print('bank dai totalDebt', daiDebt)
    print('bank dai totalShare', daiDebtShare)

    print('bank usdt totalDebt', usdtDebt)
    print('bank usdt totalShare', usdtDebtShare)

    print('bank usdc totalDebt', usdcDebt)
    print('bank usdc totalShare', usdcDebtShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('gauge prev LP balance', prevLPBal_gauge)
    print('gauge cur LP balance', curLPBal_gauge)

    # alice
    assert almostEqual(curABal - prevABal, -dai_amt), 'incorrect DAI amt'
    assert almostEqual(curBBal - prevBBal, -usdc_amt), 'incorrect USDC amt'
    assert almostEqual(curCBal - prevCBal, -usdt_amt), 'incorrect USDT amt'
    assert almostEqual(curLPBal - prevLPBal, -lp_amt), 'incorrect LP amt'

    # spell
    assert dai.balanceOf(curve_spell) == 0, 'non-zero spell DAI balance'
    assert usdc.balanceOf(curve_spell) == 0, 'non-zero spell USDC balance'
    assert usdt.balanceOf(curve_spell) == 0, 'non-zero spell USDT balance'
    assert lp.balanceOf(curve_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert daiDebt == borrow_dai_amt
    assert usdcDebt == borrow_usdc_amt
    assert usdtDebt == borrow_usdt_amt

    # #####################################################################################

    print('=========================================================================')
    print('Case 2.')

    # remove liquidity from the same position
    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevCBal = usdt.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    _, _, _, collSize = homora.getPositionInfo(position_id)

    lp_take_amt = 2**256-1  # max
    lp_want = 1 * 10**17
    dai_repay = 2**256-1  # max
    usdc_repay = 2**256-1  # max
    usdt_repay = 2**256-1  # max
    lp_repay = 0

    tx = homora.execute(
        position_id,
        curve_spell,
        curve_spell.removeLiquidity3.encode_input(
            lp,  # LP token
            lp_take_amt,  # LP amount to take out
            lp_want,  # LP amount to withdraw to wallet
            [dai_repay, usdc_repay, usdt_repay],  # repay amounts
            lp_repay,  # repay LP amount
            [0, 0, 0]  # min amounts
        ),
        {'from': alice}
    )

    position_id = tx.return_value
    print('position_id', position_id)
    print('tx gas used', tx.gas_used)

    curABal = dai.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curCBal = usdt.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_gauge = lp.balanceOf(gauge)

    print('spell lp balance', lp.balanceOf(curve_spell))
    print('spell dai balance', dai.balanceOf(curve_spell))
    print('spell usdc balance', usdc.balanceOf(curve_spell))
    print('spell usdt balance', usdt.balanceOf(curve_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('Alice delta C balance', curCBal - prevCBal)
    print('Alice delta LP balance', curLPBal - prevLPBal)
    print('remove liquidity gas', tx.gas_used)
    print('bank delta lp balance', curLPBal_bank - prevLPBal_bank)
    print('bank total lp balance', curLPBal_bank)

    _, _, _, daiDebt, daiDebtShare = homora.getBankInfo(dai)
    _, _, _, usdcDebt, usdcDebtShare = homora.getBankInfo(usdc)
    _, _, _, usdtDebt, usdtDebtShare = homora.getBankInfo(usdt)
    print('bank dai totalDebt', daiDebt)
    print('bank dai totalDebt', daiDebt)

    print('bank usdc totalShare', usdcDebtShare)
    print('bank usdc totalShare', usdcDebtShare)

    print('bank usdt totalDebt', usdtDebt)
    print('bank usdt totalShare', usdtDebtShare)

    print('LP want', lp_want)

    print('bank delta LP amount', curLPBal_bank - prevLPBal_bank)
    print('LP take amount', lp_take_amt)

    print('prev gauge LP balance', prevLPBal_gauge)
    print('cur gauge LP balance', curLPBal_gauge)

    print('coll size', collSize)

    # alice
    assert almostEqual(curLPBal - prevLPBal, lp_want), 'incorrect LP amt'

    # gauge
    assert almostEqual(curLPBal_gauge - prevLPBal_gauge, -
                       collSize), 'incorrect gauge LP amt'

    # spell
    assert dai.balanceOf(curve_spell) == 0, 'non-zero spell DAI balance'
    assert usdc.balanceOf(curve_spell) == 0, 'non-zero spell USDC balance'
    assert usdt.balanceOf(curve_spell) == 0, 'non-zero spell USDT balance'
    assert lp.balanceOf(curve_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert usdcDebt == 0, 'usdcDebt should be 0'
    assert daiDebt == 0, 'daiDebt should be 0'
    assert usdtDebt == 0, 'usdtDebt should be 0'

    return tx
