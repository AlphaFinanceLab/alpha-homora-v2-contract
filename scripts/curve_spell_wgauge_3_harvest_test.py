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
    simple_oracle.setETHPx([dai, usdt, usdc, adai, ausdc, ausdt], [2**112 // 700 // 10**12,
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
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)

    # add bank
    homora.addBank(dai, crdai, {'from': admin})
    homora.addBank(usdc, crusdc, {'from': admin})
    homora.addBank(usdt, crusdt, {'from': admin})

    # setup initial funds to alice
    mint_tokens(dai, alice)
    mint_tokens(usdc, alice)
    mint_tokens(usdt, alice)

    # check alice's funds
    print(f'Alice dai balance {dai.balanceOf(alice)}')
    print(f'Alice usdc balance {usdc.balanceOf(alice)}')
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')

    # steal some LP from the staking pool
    mint_tokens(lp, alice)
    mint_tokens(lp, bob)

    # set approval
    dai.approve(homora, 2**256-1, {'from': alice})
    dai.approve(crdai, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    lp.approve(homora, 2**256-1, {'from': alice})
    lp.approve(gauge, 2**256-1, {'from': bob})

    curve_spell = CurveSpellV1.deploy(
        homora, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', wgauge, {'from': admin})

    # register gauge
    wgauge.registerGauge(0, 0)

    # set up pools
    curve_spell.getPool(lp)

    # first time call to reduce gas
    curve_spell.ensureApproveN(lp, 3, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([curve_spell], [True], {'from': admin})

    # whitelist token in bank
    homora.setWhitelistTokens([dai, usdt, usdc], [True, True, True], {'from': admin})

    # whitelist lp in spell
    curve_spell.setWhitelistLPTokens([lp], [True], {'from': admin})

    #####################################################################################

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
    lp_amt = 0  # 1 * 10**18
    borrow_dai_amt = 2000 * 10**18  # 2000 DAI
    borrow_usdc_amt = 200 * 10**6  # 200 USDC
    borrow_usdt_amt = 1000 * 10**6  # 1000 USDT
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

    # #####################################################################################

    print('=========================================================================')
    print('Case 2. harvest first time')

    prevCRVBalance = crv.balanceOf(alice)
    print('Alice CRV balance before harvest', prevCRVBalance)
    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevCrv = crv.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    pid, gid = 0, 0
    gauge, _ = wgauge.gauges(pid, gid)
    tx = interface.ILiquidityGauge(gauge).deposit(collSize, {'from': bob})

    chain.sleep(20000)

    tx = homora.execute(
        1,
        curve_spell,
        curve_spell.harvest.encode_input(),
        {'from': alice}
    )

    print('tx gas used', tx.gas_used)

    curCRVBalance = crv.balanceOf(alice)
    print('Alice CRV balance after harvest', curCRVBalance)
    receivedCrv = curCRVBalance - prevCRVBalance

    # check with staking directly
    minter = interface.ILiquidityGaugeMinter(interface.ILiquidityGauge(gauge).minter())
    print('minter', minter)
    tx = minter.mint(gauge, {'from': bob})
    print('tx status', tx.status)
    tx = interface.ILiquidityGauge(gauge).withdraw(collSize, {'from': bob})
    receivedCrvFromGauge = crv.balanceOf(bob) - prevCrv
    print('receivedCrvFromGauge', receivedCrvFromGauge)
    assert almostEqual(receivedCrv, receivedCrvFromGauge)

    # #####################################################################################

    print('=========================================================================')
    print('Case 3. harvest second time')

    prevCRVBalance = crv.balanceOf(alice)
    print('Alice CRV balance before harvest', prevCRVBalance)
    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevCrv = crv.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    pid, gid = 0, 0
    gauge, _ = wgauge.gauges(pid, gid)
    tx = interface.ILiquidityGauge(gauge).deposit(collSize, {'from': bob})

    chain.sleep(20000)

    tx = homora.execute(
        1,
        curve_spell,
        curve_spell.harvest.encode_input(),
        {'from': alice}
    )

    print('tx gas used', tx.gas_used)

    curCRVBalance = crv.balanceOf(alice)
    print('Alice CRV balance after harvest', curCRVBalance)
    receivedCrv = curCRVBalance - prevCRVBalance

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
