from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, ERC20KP3ROracle, UniswapV2LPKP3ROracle, UniswapV2SpellV1, SimpleOracle, WERC20
)


KP3R_ADDRESS = '0x73353801921417F465377c8d898c6f4C0270282C'
WETH_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'

# add collateral for the bank


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
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')

    lp = interface.IERC20Ex('0x3041cbd36888becc7bbcbc0045e3b1f144466f5f')
    crusdt = interface.ICErc20('0x797AAB1ce7c01eB727ab980762bA88e7133d2157')
    crusdc = interface.ICErc20('0x44fbebd2f576670a6c33f6fc0b00aa8c5753b322')

    router = interface.IUniswapV2Router02('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')

    werc20 = WERC20.deploy({'from': admin})

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([usdt, usdc, lp], [8343331721347310729683379470025550036595362,
                                              8344470555541464992529317899641128796042472, 18454502573009087919612273470304975922 * 10**6])

    oracle = ProxyOracle.deploy({'from': admin})
    oracle.setWhitelistERC1155([werc20], True, {'from': admin})
    oracle.setOracles(
        [
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',  # USDC
            '0x3041cbd36888becc7bbcbc0045e3b1f144466f5f',  # USDT-USDC
        ],
        [
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
    homora.addBank(usdt, crusdt, {'from': admin})
    homora.addBank(usdc, crusdc, {'from': admin})

    # setup initial funds 10^5 USDT + 10^5 USDC to alice
    setup_transfer(usdt, accounts.at('0xbe0eb53f46cd790cd13851d5eff43d12404d33e8',
                                     force=True), alice, 10**6 * 10**6)
    setup_transfer(usdc, accounts.at('0xa191e578a6736167326d05c119ce0c90849e84b7',
                                     force=True), alice, 10**6 * 10**6)

    # setup initial funds 10^6 USDT + 10^6 USDC to homora bank
    setup_transfer(usdt, accounts.at('0xbe0eb53f46cd790cd13851d5eff43d12404d33e8',
                                     force=True), homora, 10**6 * 10**6)
    setup_transfer(usdc, accounts.at('0x397ff1542f962076d0bfe58ea045ffa2d347aca0',
                                     force=True), homora, 10**6 * 10**6)

    # check alice's funds
    print(f'Alice usdt balance {usdt.balanceOf(alice)}')
    print(f'Alice usdc balance {usdc.balanceOf(alice)}')

    # steal some LP from the staking pool
    lp.transfer(alice, 1*10**8,
                {'from': accounts.at('0x85af1678527f63eb6492ab158ed5d2a94b8732c0', force=True)})

    # set approval
    usdt.approve(homora, 2**256-1, {'from': alice})
    usdt.approve(crusdt, 2**256-1, {'from': alice})
    usdc.approve(homora, 2**256-1, {'from': alice})
    usdc.approve(crusdc, 2**256-1, {'from': alice})
    lp.approve(homora, 2**256-1, {'from': alice})

    uniswap_spell = UniswapV2SpellV1.deploy(homora, werc20, router, {'from': admin})
    # first time call to reduce gas
    uniswap_spell.getPair(usdt, usdc, {'from': admin})

    #####################################################################################

    prevABal = usdt.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)

    tx = homora.execute(
        0,
        uniswap_spell,
        uniswap_spell.addLiquidity.encode_input(
            usdt,
            usdc,
            [40000 * 10**6,  # 40000 USDT
             50000 * 10**6,   # 50000 USDC
             1*10**7,  # some LP
             1000 * 10**6,  # borrow 1000 USDT
             200 * 10**6,  # borrow 200 USDC
             0,  # 2*10**16,  # borrow 0 LP tokens
             0,  # min 0 USDT
             0],  # min 0 USDC
        ),
        {'from': alice}
    )

    position_id = tx.return_value
    print('position_id', position_id)

    curABal = usdt.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)

    print('spell lp balance', lp.balanceOf(uniswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('add liquidity gas', tx.gas_used)
    print('bank lp balance', werc20.balanceOfERC20(lp, homora))

    _, _, _, totalDebt, totalShare = homora.getBankInfo(usdt)
    print('bank usdt totalDebt', totalDebt)
    print('bank usdt totalShare', totalShare)
    assert(lp.balanceOf(uniswap_spell) == 0)
    assert(usdt.balanceOf(uniswap_spell) == 0)
    assert(usdc.balanceOf(uniswap_spell) == 0)

    #####################################################################################

    # remove liquidity from the same position
    prevABal = usdt.balanceOf(alice)
    prevBBal = usdc.balanceOf(alice)
    prevLPBal = werc20.balanceOfERC20(lp, homora)

    tx = homora.execute(
        position_id,
        uniswap_spell,
        uniswap_spell.removeLiquidity.encode_input(
            usdt,
            usdc,
            [2**256-1,  # take out all LP tokens
             1 * 10 ** 5,   # withdraw 1e5 LP tokens to wallet
             2**256-1,  # repay max USDT
             2**256-1,   # repay max USDC
             0,   # repay 0 LP
             0,   # min 0 USDT
             0],  # min 0 USDC
        ),
        {'from': alice}
    )

    curABal = usdt.balanceOf(alice)
    curBBal = usdc.balanceOf(alice)
    curLPBal = werc20.balanceOfERC20(lp, homora)

    print('spell lp balance', lp.balanceOf(uniswap_spell))
    print('spell usdt balance', usdt.balanceOf(uniswap_spell))
    print('spell usdc balance', usdc.balanceOf(uniswap_spell))
    print('Alice delta A balance', curABal - prevABal)
    print('Alice delta B balance', curBBal - prevBBal)
    print('remove liquidity gas', tx.gas_used)
    print('bank delta lp balance', curLPBal - prevLPBal)
    print('bank total lp balance', curLPBal)

    _, _, _, totalDebt, totalShare = homora.getBankInfo(usdt)
    print('bank usdt totalDebt', totalDebt)
    print('bank usdt totalShare', totalShare)

    assert(lp.balanceOf(uniswap_spell) == 0)
    assert(usdt.balanceOf(uniswap_spell) == 0)
    assert(usdc.balanceOf(uniswap_spell) == 0)

    return tx
