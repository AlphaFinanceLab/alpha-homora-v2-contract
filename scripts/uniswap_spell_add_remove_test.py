from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, ERC20KP3ROracle, UniswapV2LPKP3ROracle, UniswapV2SpellV1,
)


KP3R_ADDRESS = '0x73353801921417F465377c8d898c6f4C0270282C'
WETH_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'


def setup_bank_hack(homora):
    donator = accounts[5]
    fake = accounts.at(homora.address, force=True)
    controller = interface.IComptroller('0x3d5BC3c8d13dcB8bF317092d84783c2697AE9258')
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
    lpusdt = interface.IERC20Ex('0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    weth = interface.IERC20Ex(WETH_ADDRESS)
    router = interface.IUniswapV2Router02('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')
    erc20_oracle = ERC20KP3ROracle.deploy(KP3R_ADDRESS, {'from': admin})
    lp_oracle = UniswapV2LPKP3ROracle.deploy(KP3R_ADDRESS, {'from': admin})
    oracle = ProxyOracle.deploy({'from': admin})
    oracle.setOracles(
        [
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # USDT-ETH
        ],
        [
            [erc20_oracle, 10000, 10000, 10000],
            [lp_oracle, 10000, 10000, 10000],
        ],
        {'from': admin},
    )
    homora = HomoraBank.deploy({'from': admin})
    homora.initialize(oracle, 1000, {'from': admin})  # 10% fee
    setup_bank_hack(homora)
    homora.addBank(usdt, crusdt, {'from': admin})

    # setup initial funds 10^5 USDT + 10^4 WETH to alice
    setup_transfer(usdt, accounts.at('0xbe0eb53f46cd790cd13851d5eff43d12404d33e8', force=True), alice, 10**5 * 10**6)
    setup_transfer(weth, accounts.at('0x397ff1542f962076d0bfe58ea045ffa2d347aca0', force=True), alice, 10**4 * 10**18)

    # setup initial funds 10^6 USDT + 10^5 WETH to homora bank
    setup_transfer(usdt, accounts.at('0xbe0eb53f46cd790cd13851d5eff43d12404d33e8', force=True), homora, 10**6 * 10**6)
    setup_transfer(weth, accounts.at('0x397ff1542f962076d0bfe58ea045ffa2d347aca0', force=True), homora, 10**4 * 10**18)

    # check alice's funds
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')
    print(f'Alice weth balance {weth.balanceOf(alice)}')

    # Steal some LP from the staking pool
    lpusdt.transfer(alice, 1*10**17, {'from': accounts.at('0x767ecb395def19ab8d1b2fcc89b3ddfbed28fd6b', force=True)})
    lpusdt.transfer(homora, 2*10**17, {'from': accounts.at('0x767ecb395def19ab8d1b2fcc89b3ddfbed28fd6b', force=True)})

    # set approval
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    weth.approve(homora, 2**256-1, {'from': alice})
    lpusdt.approve(homora, 2**256-1, {'from': alice})

    uniswap_spell = UniswapV2SpellV1.deploy(homora, router, {'from': admin})
    uniswap_spell.getPair(weth, usdt, {'from': admin})  # first time call to reduce gas

    #####################################################################################

    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)

    tx = homora.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidity.encode_input(
            usdt,
            weth,  # WETH
            [400 * 10 ** 6,  # 400 USDT
             10 ** 18,   # 1 WETH
             1*10**16,  # 0 LP
             1000 * 10 ** 6,  # borrow 0 USDT
             0,  # 10 * 10**18,  # borrow 0 WETH
             0,  # 2*10**16,  # borrow 0 LP tokens
             0,  # min 0 USDT
             0],  # min 0 WETH
        ),
        {'from': alice}
    )

    position_id = tx.return_value
    print('position_id', position_id)

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)

    print('spell lp balance', lpusdt.balanceOf(uniswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', lpusdt.balanceOf(homora))

    _, _, _, totalDebt, totalShare = homora.getBankInfo(usdt)
    print('bank usdt totalDebt', totalDebt)
    print('bank usdt totalShare', totalShare)
    assert(lpusdt.balanceOf(uniswap_spell) == 0)
    assert(usdt.balanceOf(uniswap_spell) == 0)
    assert(weth.balanceOf(uniswap_spell) == 0)
    assert(totalDebt == 1000 * 10 ** 6)

    #####################################################################################

    # remove liquidity from the same position
    prevABal = usdt.balanceOf(alice)
    prevBBal = weth.balanceOf(alice)
    prevLPBal = lpusdt.balanceOf(homora)

    tx = homora.execute(
        position_id,
        uniswap_spell,
        uniswap_spell.removeLiquidity.encode_input(
            usdt,
            weth,  # WETH
            [1 * 10 ** 16,  # take out 1e16 LP tokens
             1 * 10 ** 15,   # withdraw 1e15 LP tokens to wallet
             2**256-1,  # repay 500 USDT
             0,   # repay 0 WETH
             0,   # repay 0 LP
             0,   # min 0 USDT
             0],  # min 0 WETH
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = weth.balanceOf(alice)
    curLPBal = lpusdt.balanceOf(homora)

    print('spell lp balance', lpusdt.balanceOf(uniswap_spell))
    print('spell usdt balance', usdt.balanceOf(uniswap_spell))
    print('spell weth balance', weth.balanceOf(uniswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('remove liquidity gas', tx.gas_used)
    print('bank delta lp balance', curLPBal - prevLPBal)
    print('bank total lp balance', curLPBal)

    _, _, _, totalDebt, totalShare = homora.getBankInfo(usdt)
    print('bank usdt totalDebt', totalDebt)
    print('bank usdt totalShare', totalShare)

    assert(lpusdt.balanceOf(uniswap_spell) == 0)
    assert(usdt.balanceOf(uniswap_spell) == 0)
    assert(weth.balanceOf(uniswap_spell) == 0)

    return tx
