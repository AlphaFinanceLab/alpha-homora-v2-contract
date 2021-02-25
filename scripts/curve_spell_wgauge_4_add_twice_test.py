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
    susd = interface.IERC20Ex('0x57ab1ec28d129707052df4df418d58a2d46d5f51')

    ydai = interface.IERC20Ex('0xC2cB1040220768554cf699b0d863A3cd4324ce32')
    yusdc = interface.IERC20Ex('0x26EA744E5B887E5205727f55dFBE8685e3b21951')
    yusdt = interface.IERC20Ex('0xE6354ed5bC4b393a5Aad09f21c46E101e692d447')
    ybusd = interface.IERC20Ex('0x04bC0Ab673d88aE9dbC9DA2380cB6B79C4BCa9aE')

    lp = interface.IERC20Ex('0xC25a3A3b969415c80451098fa907EC722572917F')
    pool = interface.ICurvePool('0xA5407eAE9Ba41422680e2e00537571bcC53efBfD')
    lp_busd = interface.IERC20Ex('0x3B3Ac5386837Dc563660FB6a0937DFAa5924333B')
    pool_busd = interface.ICurvePool('0x79a8C46DeA5aDa233ABaFFD40F3A0A2B1e5A4F27')
    registry = interface.ICurveRegistry('0x7d86446ddb609ed0f5f8684acf30380a356b2b4c')

    crdai = interface.ICErc20('0x92B767185fB3B04F881e3aC8e5B0662a027A1D9f')
    crusdc = interface.ICErc20('0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    crsusd = MockCErc20.deploy(susd, {'from': admin})
    crydai = MockCErc20.deploy(ydai, {'from': admin})
    cryusdc = MockCErc20.deploy(yusdc, {'from': admin})
    cryusdt = MockCErc20.deploy(yusdt, {'from': admin})
    crybusd = MockCErc20.deploy(ybusd, {'from': admin})

    gauge = accounts.at(
        '0xA90996896660DEcC6E997655E065b23788857849', force=True)
    wgauge = WLiquidityGauge.deploy(
        registry, '0xD533a949740bb3306d119CC777fa900bA034cd52', {'from': admin})
    crv = interface.IERC20Ex(wgauge.crv())

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([dai, usdt, usdc, susd, ydai, yusdc, yusdt, ybusd],
                           [2**112 // 700, 2**112 * 10**12 // 700, 2**112 * 10**12 // 700, 2**112 // 700, 2**112 // 700, 2**112 * 10**12 // 700, 2**112 * 10**12 // 700, 2**112 // 700])

    curve_oracle = CurveOracle.deploy(simple_oracle, registry, {'from': admin})
    curve_oracle.registerPool(lp)  # update pool info
    curve_oracle.registerPool(lp_busd)  # update pool info

    core_oracle = CoreOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy(core_oracle, {'from': admin})
    oracle.setWhitelistERC1155([werc20, wgauge], True, {'from': admin})
    core_oracle.setRoute(
        [dai, usdc, usdt, susd, lp,  ydai, yusdc, yusdt, ybusd,  lp_busd, ],
        [simple_oracle, simple_oracle, simple_oracle, simple_oracle, curve_oracle,
            simple_oracle, simple_oracle, simple_oracle, simple_oracle, curve_oracle],
        {'from': admin},
    )

    oracle.setOracles(
        [dai, usdc, usdt, susd, lp,  ydai, yusdc, yusdt, ybusd,  lp_busd],
        [
            [10000, 10000, 10000],
            [10000, 10000, 10000],
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
    homora.addBank(susd, crsusd, {'from': admin})
    homora.addBank(ydai, crydai, {'from': admin})
    homora.addBank(yusdc, cryusdc, {'from': admin})
    homora.addBank(yusdt, cryusdt, {'from': admin})
    homora.addBank(ybusd, crybusd, {'from': admin})

    # setup initial funds to alice
    mint_tokens(dai, alice,)
    mint_tokens(usdc, alice)
    mint_tokens(usdt, alice)
    mint_tokens(susd, alice)

    mint_tokens(ydai, alice)
    mint_tokens(yusdc, alice)
    mint_tokens(yusdt, alice)
    mint_tokens(ybusd, alice)

    # check alice's funds
    print(f'Alice dai balance {dai.balanceOf(alice)}')
    print(f'Alice usdc balance {usdc.balanceOf(alice)}')
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')
    print(f'Alice susd balance {susd.balanceOf(alice)}')
    print(f'Alice ydai balance {ydai.balanceOf(alice)}')
    print(f'Alice yusdc balance {yusdc.balanceOf(alice)}')
    print(f'Alice yusdt balance {yusdt.balanceOf(alice)}')
    print(f'Alice ybusd balance {ybusd.balanceOf(alice)}')

    # steal some LP from the staking pool
    mint_tokens(lp, alice)
    mint_tokens(lp, bob)
    mint_tokens(lp_busd, alice)

    # set approval
    dai.approve(homora, 2**256-1, {'from': alice})
    dai.approve(crdai, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    susd.approve(homora, 2**256-1, {'from': alice})
    susd.approve(crsusd, 2**256-1, {'from': alice})

    ydai.approve(homora, 2**256-1, {'from': alice})
    ydai.approve(crydai, 2**256-1, {'from': alice})
    yusdc.approve(homora, 2**256-1, {'from': alice})
    yusdc.approve(cryusdc, 2**256-1, {'from': alice})
    yusdt.approve(homora, 2**256-1, {'from': alice})
    yusdt.approve(cryusdt, 2**256-1, {'from': alice})
    ybusd.approve(homora, 2**256-1, {'from': alice})
    ybusd.approve(crybusd, 2**256-1, {'from': alice})

    lp.approve(homora, 2**256-1, {'from': alice})
    lp.approve(gauge, 2**256-1, {'from': bob})
    lp_busd.approve(homora, 2**256-1, {'from': alice})

    curve_spell = CurveSpellV1.deploy(
        homora, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', wgauge, {'from': admin})

    # register gauge
    wgauge.registerGauge(12, 0)
    wgauge.registerGauge(1, 0)

    # set up pools
    curve_spell.getPool(lp)
    curve_spell.getPool(lp_busd)

    # first time call to reduce gas
    curve_spell.ensureApproveN(lp, 4, {'from': admin})
    curve_spell.ensureApproveN(lp_busd, 4, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([curve_spell], [True], {'from': admin})

    # whitelist token in bank
    homora.setWhitelistTokens([dai, usdc], [True, True], {'from': admin})

    # whitelist lp in spell
    curve_spell.setWhitelistLPTokens([lp, lp_busd], [True, True], {'from': admin})

    #####################################################################################

    print('=========================================================================')
    print('Case 1.')

    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevCBal = usdt.balanceOf(alice)
    prevDBal = susd.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    dai_amt = 200 * 10**18
    usdc_amt = 1000 * 10**6
    usdt_amt = 1000 * 10**6
    susd_amt = 1000 * 10**18
    lp_amt = 0
    borrow_dai_amt = 10 * 10**18
    borrow_usdc_amt = 10**6
    borrow_usdt_amt = 0
    borrow_susd_amt = 0
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 12
    gid = 0

    tx = homora.execute(
        0,
        curve_spell,
        curve_spell.addLiquidity4.encode_input(
            lp,  # LP
            [dai_amt, usdc_amt, usdt_amt, susd_amt],  # supply tokens
            lp_amt,  # supply LP
            [borrow_dai_amt, borrow_usdc_amt, borrow_usdt_amt, borrow_susd_amt],  # borrow tokens
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
    curDBal = susd.balanceOf(alice)
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
    _, _, _, susdDebt, susdDebtShare = homora.getBankInfo(susd)

    print('bank dai totalDebt', daiDebt)
    print('bank dai totalShare', daiDebtShare)

    print('bank usdt totalDebt', usdtDebt)
    print('bank usdt totalShare', usdtDebtShare)

    print('bank usdc totalDebt', usdcDebt)
    print('bank usdc totalShare', usdcDebtShare)

    print('bank susd totalDebt', susdDebt)
    print('bank susd totalShare', susdDebtShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('gauge prev LP balance', prevLPBal_gauge)
    print('gauge cur LP balance', curLPBal_gauge)

    # alice
    assert almostEqual(curABal - prevABal, -dai_amt), 'incorrect DAI amt'
    assert almostEqual(curBBal - prevBBal, -usdc_amt), 'incorrect USDC amt'
    assert almostEqual(curCBal - prevCBal, -usdt_amt), 'incorrect USDT amt'
    assert almostEqual(curDBal - prevDBal, -susd_amt), 'incorrect SUSD amt'
    assert almostEqual(curLPBal - prevLPBal, -lp_amt), 'incorrect LP amt'

    # spell
    assert dai.balanceOf(curve_spell) == 0, 'non-zero spell DAI balance'
    assert usdc.balanceOf(curve_spell) == 0, 'non-zero spell USDC balance'
    assert usdt.balanceOf(curve_spell) == 0, 'non-zero spell USDT balance'
    assert susd.balanceOf(curve_spell) == 0, 'non-zero spell SUSD balance'
    assert lp.balanceOf(curve_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert daiDebt == borrow_dai_amt
    assert usdcDebt == borrow_usdc_amt
    assert usdtDebt == borrow_usdt_amt
    assert susdDebt == borrow_susd_amt

    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevCrv = crv.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    pid, gid = 12, 0
    gauge, _ = wgauge.gauges(pid, gid)
    print('gauge', gauge)
    tx = interface.ILiquidityGauge(gauge).deposit(collSize, {'from': bob})

    chain.sleep(20000)

    prevAliceCrvBalance = crv.balanceOf(alice)
    print('Alice crv balance', prevAliceCrvBalance)

    # #####################################################################################

    print('=========================================================================')
    print('Case 2. add liqudiity second time')

    prevABal = dai.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevCBal = usdt.balanceOf(alice)
    prevDBal = susd.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    dai_amt = 200 * 10**18
    usdc_amt = 1000 * 10**6
    usdt_amt = 1000 * 10**6
    susd_amt = 1000 * 10**18
    lp_amt = 0
    borrow_dai_amt = 10 * 10**18
    borrow_usdc_amt = 10**6
    borrow_usdt_amt = 0
    borrow_susd_amt = 0
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 12
    gid = 0

    tx = homora.execute(
        1,
        curve_spell,
        curve_spell.addLiquidity4.encode_input(
            lp,  # LP
            [dai_amt, usdc_amt, usdt_amt, susd_amt],  # supply tokens
            lp_amt,  # supply LP
            [borrow_dai_amt, borrow_usdc_amt, borrow_usdt_amt, borrow_susd_amt],  # borrow tokens
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
    curDBal = susd.balanceOf(alice)
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
    _, _, _, susdDebt, susdDebtShare = homora.getBankInfo(susd)

    print('bank dai totalDebt', daiDebt)
    print('bank dai totalShare', daiDebtShare)

    print('bank usdt totalDebt', usdtDebt)
    print('bank usdt totalShare', usdtDebtShare)

    print('bank usdc totalDebt', usdcDebt)
    print('bank usdc totalShare', usdcDebtShare)

    print('bank susd totalDebt', susdDebt)
    print('bank susd totalShare', susdDebtShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('gauge prev LP balance', prevLPBal_gauge)
    print('gauge cur LP balance', curLPBal_gauge)

    # alice
    assert almostEqual(curABal - prevABal, -dai_amt), 'incorrect DAI amt'
    assert almostEqual(curBBal - prevBBal, -usdc_amt), 'incorrect USDC amt'
    assert almostEqual(curCBal - prevCBal, -usdt_amt), 'incorrect USDT amt'
    assert almostEqual(curDBal - prevDBal, -susd_amt), 'incorrect SUSD amt'
    assert almostEqual(curLPBal - prevLPBal, -lp_amt), 'incorrect LP amt'

    # spell
    assert dai.balanceOf(curve_spell) == 0, 'non-zero spell DAI balance'
    assert usdc.balanceOf(curve_spell) == 0, 'non-zero spell USDC balance'
    assert usdt.balanceOf(curve_spell) == 0, 'non-zero spell USDT balance'
    assert susd.balanceOf(curve_spell) == 0, 'non-zero spell SUSD balance'
    assert lp.balanceOf(curve_spell) == 0, 'non-zero spell LP balance'

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
