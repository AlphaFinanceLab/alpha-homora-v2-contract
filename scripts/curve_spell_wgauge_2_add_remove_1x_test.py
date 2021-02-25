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
    renbtc = interface.IERC20Ex('0xeb4c2781e4eba804ce9a9803c67d0893436bb27d')
    wbtc = interface.IERC20Ex('0x2260fac5e5542a773aa44fbcfedf7c193bc2c599')
    eurs = interface.IERC20Ex('0xdB25f211AB05b1c97D595516F45794528a807ad8')
    seur = interface.IERC20Ex('0xD71eCFF9342A5Ced620049e616c5035F1dB98620')

    lp = interface.IERC20Ex('0x49849C98ae39Fff122806C06791Fa73784FB3675')
    pool = interface.ICurvePool('0x93054188d876f558f4a66B2EF1d97d16eDf0895B')
    lp_eurs = interface.IERC20Ex('0x194eBd173F6cDacE046C53eACcE9B953F28411d1')
    pool_eurs = interface.ICurvePool('0x0Ce6a5fF5217e38315f87032CF90686C96627CAA')
    registry = interface.ICurveRegistry(
        '0x7d86446ddb609ed0f5f8684acf30380a356b2b4c')

    crrenbtc = MockCErc20.deploy(renbtc, {'from': admin})
    crwbtc = MockCErc20.deploy(wbtc, {'from': admin})
    creurs = MockCErc20.deploy(eurs, {'from': admin})
    crseur = MockCErc20.deploy(seur, {'from': admin})

    gauge = accounts.at(
        '0xB1F2cdeC61db658F091671F5f199635aEF202CAC', force=True)
    wgauge = WLiquidityGauge.deploy(
        registry, '0xD533a949740bb3306d119CC777fa900bA034cd52', {'from': admin})
    crv = interface.IERC20Ex(wgauge.crv())

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([renbtc, wbtc, eurs, seur], [2**112 * 30,
                                                        2**112 * 30,
                                                        2**112 // 700,
                                                        2**112 // 700])

    curve_oracle = CurveOracle.deploy(simple_oracle, registry, {'from': admin})
    curve_oracle.registerPool(lp)  # update pool info
    curve_oracle.registerPool(lp_eurs)  # update pool info

    core_oracle = CoreOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy(core_oracle, {'from': admin})
    oracle.setWhitelistERC1155([werc20, wgauge], True, {'from': admin})
    core_oracle.setRoute(
        [renbtc,  wbtc, lp, eurs, seur,  lp_eurs],
        [simple_oracle, simple_oracle, curve_oracle, simple_oracle, simple_oracle, curve_oracle],
        {'from': admin},
    )
    oracle.setOracles(
        [renbtc,  wbtc, lp, eurs, seur, lp_eurs],
        [
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
    homora.addBank(renbtc, crrenbtc, {'from': admin})
    homora.addBank(wbtc, crwbtc, {'from': admin})
    homora.addBank(eurs, creurs, {'from': admin})
    homora.addBank(seur, crseur, {'from': admin})

    # setup initial funds to alice
    mint_tokens(renbtc, alice)
    mint_tokens(wbtc, alice)
    mint_tokens(eurs, alice)
    mint_tokens(seur, alice)

    mint_tokens(wbtc, crwbtc)

    # check alice's funds
    print(f'Alice renbtc balance {renbtc.balanceOf(alice)}')
    print(f'Alice wbtc balance {wbtc.balanceOf(alice)}')
    print(f'Alice eurs balance {eurs.balanceOf(alice)}')
    print(f'Alice seur balance {seur.balanceOf(alice)}')

    # steal some LP from the staking pool
    mint_tokens(lp, alice)
    mint_tokens(lp, bob)
    mint_tokens(lp_eurs, alice)

    # set approval
    renbtc.approve(homora, 2**256-1, {'from': alice})
    renbtc.approve(crrenbtc, 2**256-1, {'from': alice})
    wbtc.approve(homora, 2**256-1, {'from': alice})
    wbtc.approve(crwbtc, 2**256-1, {'from': alice})

    eurs.approve(homora, 2**256-1, {'from': alice})
    eurs.approve(creurs, 2**256-1, {'from': alice})
    seur.approve(homora, 2**256-1, {'from': alice})
    seur.approve(crseur, 2**256-1, {'from': alice})

    lp.approve(homora, 2**256-1, {'from': alice})
    lp.approve(gauge, 2**256-1, {'from': bob})
    lp_eurs.approve(homora, 2**256-1, {'from': alice})

    curve_spell = CurveSpellV1.deploy(
        homora, werc20, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', wgauge, {'from': admin})

    # register gauge
    wgauge.registerGauge(9, 0)
    wgauge.registerGauge(23, 0)

    # set up pools
    curve_spell.getPool(lp)
    curve_spell.getPool(lp_eurs)

    # first time call to reduce gas
    curve_spell.ensureApproveN(lp, 2, {'from': admin})
    curve_spell.ensureApproveN(lp_eurs, 2, {'from': admin})

    # whitelist spell in bank
    homora.setWhitelistSpells([curve_spell], [True], {'from': admin})

    # whitelist lp in spell
    curve_spell.setWhitelistLPTokens([lp, lp_eurs], [True, True], {'from': admin})

    #####################################################################################

    print('=========================================================================')
    print('Case 1.')

    prevABal = renbtc.balanceOf(alice)
    prevBBal = wbtc.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    renbtc_amt = 1 * 10**7
    wbtc_amt = 1 * 10**7
    lp_amt = 10**13
    borrow_renbtc_amt = 0
    borrow_wbtc_amt = 0
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 9
    gid = 0

    tx = homora.execute(
        0,
        curve_spell,
        curve_spell.addLiquidity2.encode_input(
            lp,  # LP
            [renbtc_amt, wbtc_amt],  # supply tokens
            lp_amt,  # supply LP
            [borrow_renbtc_amt, borrow_wbtc_amt],  # borrow tokens
            borrow_lp_amt,  # borrow LP
            minLPMint,  # min LP mint
            pid,
            gid
        ),
        {'from': alice}
    )

    curABal = renbtc.balanceOf(alice)
    curBBal = wbtc.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_gauge = lp.balanceOf(gauge)

    print('spell lp balance', lp.balanceOf(curve_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', curLPBal_bank)

    _, _, _, renbtcDebt, renbtcDebtShare = homora.getBankInfo(renbtc)
    _, _, _, wbtcDebt, wbtcDebtShare = homora.getBankInfo(wbtc)

    print('bank renbtc totalDebt', renbtcDebt)
    print('bank renbtc totalShare', renbtcDebtShare)

    print('bank wbtc totalDebt', wbtcDebt)
    print('bank wbtc totalShare', wbtcDebtShare)

    print('bank prev LP balance', prevLPBal_bank)
    print('bank cur LP balance', curLPBal_bank)

    print('gauge prev LP balance', prevLPBal_gauge)
    print('gauge cur LP balance', curLPBal_gauge)

    # alice
    assert almostEqual(curABal - prevABal, -renbtc_amt), 'incorrect renbtc amt'
    assert almostEqual(curBBal - prevBBal, -wbtc_amt), 'incorrect wbtc amt'
    assert almostEqual(curLPBal - prevLPBal, -lp_amt), 'incorrect LP amt'

    # spell
    assert renbtc.balanceOf(curve_spell) == 0, 'non-zero spell renbtc balance'
    assert wbtc.balanceOf(curve_spell) == 0, 'non-zero spell wbtc balance'
    assert lp.balanceOf(curve_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert renbtcDebt == borrow_renbtc_amt
    assert wbtcDebt == borrow_wbtc_amt

    _, _, collId, collSize = homora.getPositionInfo(1)
    print('collSize', collSize)

    # staking directly
    prevCrv = crv.balanceOf(bob)
    print('bob lp balance', interface.IERC20Ex(lp).balanceOf(bob))
    pid, gid = 9, 0
    gauge, _ = wgauge.gauges(pid, gid)
    print('gauge address', gauge)
    tx = interface.ILiquidityGauge(gauge).deposit(collSize, {'from': bob})

    chain.sleep(20000)

    prevAliceCrvBalance = crv.balanceOf(alice)
    print('Alice crv balance', prevAliceCrvBalance)

    # #####################################################################################

    print('=========================================================================')
    print('Case 2. add liquidity (failed tx desired)')

    eurs_amt = 1 * 10**3
    seur_amt = 1 * 10**3
    lp_amt = 0
    borrow_eurs_amt = 0
    borrow_seur_amt = 0
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 9
    gid = 0

    try:
        tx = homora.execute(
            1,
            curve_spell,
            curve_spell.addLiquidity2.encode_input(
                lp_eurs,  # lp_eurs
                [eurs_amt, seur_amt],  # supply tokens
                lp_amt,  # supply LP
                [borrow_eurs_amt, borrow_seur_amt],  # borrow tokens
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

    eurs_amt = 1 * 10**3
    seur_amt = 1 * 10**3
    lp_amt = 0
    borrow_eurs_amt = 0
    borrow_seur_amt = 0
    borrow_lp_amt = 0
    minLPMint = 0

    pid = 23
    gid = 0

    try:
        tx = homora.execute(
            1,
            curve_spell,
            curve_spell.addLiquidity2.encode_input(
                lp_eurs,  # lp_eurs
                [eurs_amt, seur_amt],  # supply tokens
                lp_amt,  # supply LP
                [borrow_eurs_amt, borrow_seur_amt],  # borrow tokens
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
    eurs_repay = 2**256-1  # max
    seur_repay = 2**256-1  # max
    lp_repay = 0

    try:
        tx = homora.execute(
            1,
            curve_spell,
            curve_spell.removeLiquidity2.encode_input(
                lp_eurs,  # lp_eurs token
                lp_take_amt,  # LP amount to take out
                lp_want,  # LP amount to withdraw to wallet
                [eurs_repay, seur_repay],  # repay amounts
                lp_repay,  # repay LP amount
                [0, 0]  # min amounts
            ),
            {'from': alice}
        )
        assert False, 'tx should revert'
    except VirtualMachineError:
        pass

    # #####################################################################################

    print('=========================================================================')
    print('Case 5. remove liquidity')

    # remove liquidity from the same position
    prevABal = renbtc.balanceOf(alice)
    prevBBal = wbtc.balanceOf(alice)
    prevLPBal = lp.balanceOf(alice)
    prevLPBal_bank = lp.balanceOf(homora)
    prevLPBal_gauge = lp.balanceOf(gauge)

    _, _, _, collSize = homora.getPositionInfo(1)

    lp_take_amt = 2**256-1  # max
    lp_want = 1 * 10**12
    renbtc_repay = 2**256-1  # max
    wbtc_repay = 2**256-1  # max
    lp_repay = 0

    tx = homora.execute(
        1,
        curve_spell,
        curve_spell.removeLiquidity2.encode_input(
            lp,  # LP token
            lp_take_amt,  # LP amount to take out
            lp_want,  # LP amount to withdraw to wallet
            [renbtc_repay, wbtc_repay],  # repay amounts
            lp_repay,  # repay LP amount
            [0, 0]  # min amounts
        ),
        {'from': alice}
    )

    curABal = renbtc.balanceOf(alice)
    curBBal = wbtc.balanceOf(alice)
    curLPBal = lp.balanceOf(alice)
    curLPBal_bank = lp.balanceOf(homora)
    curLPBal_gauge = lp.balanceOf(gauge)

    print('spell lp balance', lp.balanceOf(curve_spell))
    print('spell renbtc balance', renbtc.balanceOf(curve_spell))
    print('spell wbtc balance', wbtc.balanceOf(curve_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('Alice delta LP balance', curLPBal - prevLPBal)
    print('remove liquidity gas', tx.gas_used)
    print('bank delta lp balance', curLPBal_bank - prevLPBal_bank)
    print('bank total lp balance', curLPBal_bank)

    _, _, _, renbtcDebt, renbtcDebtShare = homora.getBankInfo(renbtc)
    _, _, _, wbtcDebt, wbtcDebtShare = homora.getBankInfo(wbtc)
    print('bank renbtc totalDebt', renbtcDebt)
    print('bank renbtc totalDebt', renbtcDebt)

    print('bank wbtc totalShare', wbtcDebtShare)
    print('bank wbtc totalShare', wbtcDebtShare)

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
    assert renbtc.balanceOf(curve_spell) == 0, 'non-zero spell renbtc balance'
    assert wbtc.balanceOf(curve_spell) == 0, 'non-zero spell wbtc balance'
    assert lp.balanceOf(curve_spell) == 0, 'non-zero spell LP balance'

    # debt
    assert wbtcDebt == 0, 'wbtcDebt should be 0'
    assert renbtcDebt == 0, 'renbtcDebt should be 0'

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
