from brownie import accounts, interface, Contract, chain
from brownie import (
    HomoraBank, ProxyOracle, CoreOracle, ERC20KP3ROracle, SimpleOracle, CurveOracle, CurveSpellV1, WERC20, WLiquidityGauge, MockCErc20
)
import brownie
from brownie.exceptions import VirtualMachineError
from .utils import *

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
    bob = accounts[2]
    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    adai = interface.IERC20Ex('0x028171bCA77440897B824Ca71D1c56caC55b68A3')
    ausdc = interface.IERC20Ex('0xBcca60bB61934080951369a648Fb03DF4F96263C')
    ausdt = interface.IERC20Ex('0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811')

    lp = interface.IERC20Ex('0x6c3f90f043a72fa612cbac8115ee7e52bde6e490')
    pool = interface.ICurvePool('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7')
    lp_aave = interface.IERC20Ex('0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900')
    pool_aave = interface.ICurvePool('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE')
    registry = interface.ICurveRegistry(
        '0x7d86446ddb609ed0f5f8684acf30380a356b2b4c')

    crdai = interface.ICErc20('0x92B767185fB3B04F881e3aC8e5B0662a027A1D9f')
    crusdc = interface.ICErc20('0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    cradai = MockCErc20.deploy(adai, {'from': admin})
    crausdc = MockCErc20.deploy(ausdc, {'from': admin})
    crausdt = MockCErc20.deploy(ausdt, {'from': admin})

    gauge = accounts.at(
        '0xbFcF63294aD7105dEa65aA58F8AE5BE2D9d0952A', force=True)
    wgauge = WLiquidityGauge.deploy(
        registry, '0xD533a949740bb3306d119CC777fa900bA034cd52', {'from': admin})
    crv = interface.IERC20Ex(wgauge.crv())

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([dai, usdt, usdc, adai, ausdc, ausdt], [2**112 // 700,
                                                                   2**112 // 700,
                                                                   2**112 // 700,
                                                                   2**112 // 700,
                                                                   2**112 // 700,
                                                                   2**112 // 700])

    curve_oracle = CurveOracle.deploy(simple_oracle, registry, {'from': admin})
    curve_oracle.registerPool(lp)  # update pool info
    curve_oracle.registerPool(lp_aave)  # update pool info

    core_oracle = CoreOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy(core_oracle, {'from': admin})
    oracle.setWhitelistERC1155([werc20, wgauge], True, {'from': admin})
    core_oracle.setRoute(
        [dai, usdc, usdt, lp,  adai, ausdc, ausdt, lp_aave],
        [simple_oracle, simple_oracle, simple_oracle, curve_oracle,
            simple_oracle, simple_oracle, simple_oracle, curve_oracle],
        {'from': admin},
    )

    oracle.setOracles(
        [dai, usdc, usdt, lp,  adai, ausdc, ausdt, lp_aave],
        [
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
        ],
        {'from': admin},
    )

    # initialize
    homora = HomoraBank.deploy({'from': admin})
    print('donator ether', accounts[5].balance())
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)

    # add bank
    homora.addBank(dai, crdai, {'from': admin})
    homora.addBank(usdc, crusdc, {'from': admin})
    homora.addBank(usdt, crusdt, {'from': admin})
    homora.addBank(adai, cradai, {'from': admin})
    homora.addBank(ausdc, crausdc, {'from': admin})
    homora.addBank(ausdt, crausdt, {'from': admin})

    # setup initial funds 10^6 USDT + 10^6 USDC + 10^6 DAI to alice
    mint_tokens(dai, alice,)
    mint_tokens(usdc, alice)
    mint_tokens(usdt, alice)
    mint_tokens(adai, alice)
    mint_tokens(ausdc, alice)
    mint_tokens(ausdt, alice)

    # check alice's funds
    print(f'Alice dai balance {dai.balanceOf(alice)}')
    print(f'Alice usdc balance {usdc.balanceOf(alice)}')
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')
    print(f'Alice adai balance {adai.balanceOf(alice)}')
    print(f'Alice ausdc balance {ausdc.balanceOf(alice)}')
    print(f'Alice ausdt balance {ausdt.balanceOf(alice)}')

    # steal some LP from the staking pool
    mint_tokens(lp, alice)
    mint_tokens(lp, bob)
    mint_tokens(lp_aave, alice)

    # set approval
    dai.approve(homora, 2**256-1, {'from': alice})
    dai.approve(crdai, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})

    adai.approve(homora, 2**256-1, {'from': alice})
    adai.approve(cradai, 2**256-1, {'from': alice})
    ausdc.approve(homora, 2**256-1, {'from': alice})
    ausdc.approve(crausdc, 2**256-1, {'from': alice})
    ausdt.approve(homora, 2**256-1, {'from': alice})
    ausdt.approve(crausdt, 2**256-1, {'from': alice})

    lp.approve(homora, 2**256-1, {'from': alice})
    lp.approve(gauge, 2**256-1, {'from': bob})
    lp_aave.approve(homora, 2**256-1, {'from': alice})

    curve_spell = CurveSpellV1.deploy(
        homora, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', wgauge, {'from': admin})

    # register gauge
    wgauge.registerGauge(0, 0)
    wgauge.registerGauge(25, 0)

    # set up pools
    curve_spell.getPool(lp)
    curve_spell.getPool(lp_aave)

    # first time call to reduce gas
    curve_spell.ensureApproveN(lp, 3, {'from': admin})
    curve_spell.ensureApproveN(lp_aave, 3, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([curve_spell], [True], {'from': admin})

    # whitelist lp in spell
    curve_spell.setWhitelistLPTokens([lp, lp_aave], [True, True], {'from': admin})

    #####################################################################################

    print('=========================================================================')
    print('Case 1.')

    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevCBal = usdt.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    dai_amt = 200 * 10**18
    usdc_amt = 500 * 10**6
    usdt_amt = 400 * 10**6
    lp_amt = 1 * 10**18
    borrow_dai_amt = 0
    borrow_usdc_amt = 0
    borrow_usdt_amt = 0
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

    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevCrv = crv.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    pid, gid = 0, 0
    gauge, _ = wgauge.gauges(pid, gid)
    tx = interface.ILiquidityGauge(gauge).deposit(collSize, {'from': bob})

    chain.sleep(20000)

    prevAliceCrvBalance = crv.balanceOf(alice)
    print('Alice crv balance', prevAliceCrvBalance)

    # #####################################################################################

    print('=========================================================================')
    print('Case 2. add liquidity (failed tx desired)')

    adai_amt = 200 * 10**18
    ausdc_amt = 500 * 10**6
    ausdt_amt = 400 * 10**6
    lp_amt = 0
    borrow_adai_amt = 0
    borrow_ausdc_amt = 0
    borrow_ausdt_amt = 0
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 0
    gid = 0

    try:
        tx = homora.execute(
            1,
            curve_spell,
            curve_spell.addLiquidity3.encode_input(
                lp_aave,  # LP_aave
                [adai_amt, ausdc_amt, ausdt_amt],  # supply tokens
                lp_amt,  # supply LP
                [borrow_adai_amt, borrow_ausdc_amt, borrow_ausdt_amt],  # borrow tokens
                borrow_lp_amt,  # borrow LP
                minLPMint,  # min LP mint
                pid,
                gid
            ),
            {'from': alice}
        )
        assert False, 'tx should fail'
    except VirtualMachineError:
        pass

    # #####################################################################################

    print('=========================================================================')
    print('Case 3. add liquidity (failed tx desired)')

    adai_amt = 200 * 10**18
    ausdc_amt = 500 * 10**6
    ausdt_amt = 400 * 10**6
    lp_amt = 0
    borrow_adai_amt = 0
    borrow_ausdc_amt = 0
    borrow_ausdt_amt = 0
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 25
    gid = 0

    try:
        tx = homora.execute(
            1,
            curve_spell,
            curve_spell.addLiquidity3.encode_input(
                lp_aave,  # LP_aave
                [adai_amt, ausdc_amt, ausdt_amt],  # supply tokens
                lp_amt,  # supply LP
                [borrow_adai_amt, borrow_ausdc_amt, borrow_ausdt_amt],  # borrow tokens
                borrow_lp_amt,  # borrow LP
                minLPMint,  # min LP mint
                pid,
                gid
            ),
            {'from': alice}
        )
        assert False, 'tx should fail'
    except VirtualMachineError:
        pass

    # #####################################################################################

    print('=========================================================================')
    print('Case 4. remove liquidity (failed tx desired)')

    lp_take_amt = 2**256-1  # max
    lp_want = 1 * 10**17
    adai_repay = 2**256-1  # max
    ausdc_repay = 2**256-1  # max
    ausdt_repay = 2**256-1  # max
    lp_repay = 0

    try:
        tx = homora.execute(
            1,
            curve_spell,
            curve_spell.removeLiquidity3.encode_input(
                lp_aave,  # LP_aave token
                lp_take_amt,  # LP amount to take out
                lp_want,  # LP amount to withdraw to wallet
                [adai_repay, ausdc_repay, ausdt_repay],  # repay amounts
                lp_repay,  # repay LP amount
                [0, 0, 0]  # min amounts
            ),
            {'from': alice}
        )
        assert False, 'tx should revert'
    except VirtualMachineError:
        pass

    # #####################################################################################

    print('=========================================================================')
    print('Case 5. remove liqudiity')

    # remove liquidity from the same position
    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevCBal = usdt.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    _, _, _, collSize = homora.getPositionInfo(1)

    lp_take_amt = 2**256-1  # max
    lp_want = 1 * 10**17
    dai_repay = 2**256-1  # max
    usdc_repay = 2**256-1  # max
    usdt_repay = 2**256-1  # max
    lp_repay = 0

    tx = homora.execute(
        1,
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

    curAliceCrvBalance = crv.balanceOf(alice)
    print('Alice crv balance', curAliceCrvBalance)
    receivedCrv = curAliceCrvBalance - prevAliceCrvBalance
    print('received crv', receivedCrv)

    # check with staking directly
    minter = interface.ILiquidityGaugeMinter(interface.ILiquidityGauge(gauge).minter())
    print('minter', minter)
    tx = minter.mint(gauge, {'from': bob})
    print('tx status', tx.status)
    tx = interface.ILiquidityGauge(gauge).withdraw(collSize, {'from': bob})
    receivedCrvFromGauge = crv.balanceOf(bob) - prevCrv
    print('receivedCrvFromGauge', receivedCrvFromGauge)
    assert almostEqual(receivedCrv, receivedCrvFromGauge)

    return tx
