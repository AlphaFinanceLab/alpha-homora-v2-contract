from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, CoreOracle, SimpleOracle, BalancerPairOracle, WERC20
)


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

    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    dai = interface.IERC20Ex('0x6B175474E89094C44Da98b954EedeAC495271d0F')

    lp = interface.IERC20Ex('0x8b6e6e7b5b3801fed2cafd4b22b8a16c2f2db21a')
    # pool is lp for balancer
    pool = interface.ICurvePool('0x8b6e6e7b5b3801fed2cafd4b22b8a16c2f2db21a')

    werc20 = WERC20.deploy({'from': admin})

    uni_pair = interface.IUniswapV2Pair('0xa478c2975ab1ea89e8196811f51a7b7ade33eb11')
    resA, resB, _ = uni_pair.getReserves()
    if uni_pair.token0() == weth:
        weth_dai_price = resB * 10**18 // resA
    else:
        weth_dai_price = resA * 10**18 // resB
    print('weth dai price', weth_dai_price)

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([weth, dai], [2**112, 2**112 * 10 ** 18 // weth_dai_price])

    balancer_oracle = BalancerPairOracle.deploy(simple_oracle, {'from': admin})

    core_oracle = CoreOracle.deploy({'from': admin})
    oracle = ProxyOracle.deploy(core_oracle, {'from': admin})
    oracle.setWhitelistERC1155([werc20], True, {'from': admin})
    oracle.setOracles(
        [weth, dai, lp],
        [
            [10000, 10000, 10000],
            [10000, 10000, 10000],
            [10000, 10000, 10000],
        ],
        {'from': admin},
    )
    core_oracle.setRoute(
        [weth, dai, lp],
        [simple_oracle, simple_oracle, balancer_oracle],
        {'from': admin},
    )

    #####################################################################################

    print('=========================================================================')
    print('Case 1.')

    lp_price = balancer_oracle.getETHPx(lp)
    dai_price = simple_oracle.getETHPx(dai)
    weth_price = simple_oracle.getETHPx(weth)

    print('lp price', lp_price)
    print('dai price', dai_price)
    print('weth price', weth_price)

    assert almostEqual(lp_price, weth.balanceOf(
        lp) * 5 // 4 * 2**112 // lp.totalSupply())
