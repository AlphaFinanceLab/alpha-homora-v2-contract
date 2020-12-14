from brownie import accounts, interface, Contract
from brownie import (
    HomoraBank, ProxyOracle, SimpleOracle, Balancer2TokensOracle, WERC20
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

    simple_oracle = SimpleOracle.deploy({'from': admin})
    simple_oracle.setETHPx([weth, dai], [
                           5192296858534827628530496329220096, 8887571220661441971398610676149])

    balancer_oracle = Balancer2TokensOracle.deploy(simple_oracle, {'from': admin})

    oracle = ProxyOracle.deploy({'from': admin})
    oracle.setWhitelistERC1155([werc20], True, {'from': admin})
    oracle.setOracles(
        [
            '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # WETH
            '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
            '0x6c3f90f043a72fa612cbac8115ee7e52bde6e490',  # lp
        ],
        [
            [simple_oracle, 10000, 10000, 10000],
            [simple_oracle, 10000, 10000, 10000],
            [balancer_oracle, 10000, 10000, 10000],
        ],
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
