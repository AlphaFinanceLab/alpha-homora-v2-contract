from brownie import accounts, HomoraBank, UniswapV2SpellV1
from brownie import interface
from .utils import *


def main():
    a = accounts.at('0xb593d82d53e2c187dc49673709a6e9f806cdc835', force=True)
    h = HomoraBank.deploy({'from': a})
    h.initialize('0xffffffffffffffffffffffffffffffffffffffff', 0, {'from': a})
    p = interface.IProxyAdmin('0x090eCE252cEc5998Db765073D07fac77b8e60CB2')
    p.upgrade('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb', h, {'from': a})

    bank = HomoraBank.at('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    positionId = 834
    owner = '0xABCdeaBbaDbabDd2A6be743099fe2EC8773F682f'
    uniswap_spell = UniswapV2SpellV1.at('0xc671B7251a789de0835a2fa33c83c8D4afB39092')
    uni = '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984'
    weth = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    print(interface.IERC20Ex(uni).balanceOf(owner))
    bank.execute(positionId, uniswap_spell,
                 uniswap_spell.removeLiquidityWERC20.encode_input(
                     uni,
                     weth,
                     [2**256-1, 0, 0, 2**256-1, 0, 0, 0]
                 ),
                 {'from': owner})
    print(interface.IERC20Ex(uni).balanceOf(owner))
