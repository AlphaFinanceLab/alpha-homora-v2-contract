import pytest
import brownie
from brownie.network.state import Chain
from enum import IntEnum, auto
from brownie import accounts, interface, Contract

chain = Chain()

MAX_UINT256 = 2**256-1

INIT_PX = 400
INIT_RESERVE = 1000

dai = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
USDT_ETH_ADDRESS = "0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852"
CUSDT_ADDRESS = "0x797AAB1ce7c01eB727ab980762bA88e7133d2157"
WETH_ADDRESS = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
KP3R_ADDRESS = "0x73353801921417F465377c8d898c6f4C0270282C"


def almostEqual(a, b):
    threshold = 0.01
    return a < b + threshold * abs(b) and a > b - threshold * abs(b)


def ether(amount):
    return amount*10**18


def fromEther(amount):
    return amount/1e18


@pytest.fixture(scope="module")
def admin(a):
    return a[0]


@pytest.fixture(scope="module")
def alice(a):
    return a[1]


@pytest.fixture(scope="module")
def bob(a):
    return a[2]


@pytest.fixture(scope="module")
def charlie(a):
    return a[3]


@pytest.fixture(scope="module")
def usdt():
    return interface.IERC20Ex(USDT_ADDRESS)


@pytest.fixture(scope="module")
def lpusdt():
    return interface.IERC20Ex(USDT_ETH_ADDRESS)


@pytest.fixture(scope="module")
def crusdt():
    return interface.IERC20Ex(CUSDT_ADDRESS)


@pytest.fixture(scope="module")
def erc20_oracle(admin, ERC20KP3ROracle):
    return admin.deploy(ERC20KP3ROracle, KP3R_ADDRESS)


@pytest.fixture(scope="module")
def lp_oracle(admin, UniswapV2LPK3PROracle):
    return admin.deploy(UniswapV2LPK3PROracle, KP3R_ADDRESS)


@pytest.fixture(scope="module")
def oracle(admin, erc20_oracle, lp_oracle, ProxyOracle):
    oracle = admin.deploy(ProxyOracle)
    oracle.setOracles(
        [USDT_ADDRESS, USDT_ETH_ADDRESS], [(erc20_oracle, 10000, 10000, 10000), (lp_oracle, 10000, 10000, 10000)])
    return oracle


@pytest.fixture(scope="module")
def homora(admin, alice, oracle, lpusdt, HomoraBank):
    homora = admin.deploy(HomoraBank)
    homora.initialize(oracle, 1000)
    homora.addBank(USDT_ADDRESS, CUSDT_ADDRESS, {'from': admin})
    donator = accounts[5]
    fake = accounts.at(homora.address, force=True)
    controller = interface.IComptroller(
        '0x3d5BC3c8d13dcB8bF317092d84783c2697AE9258')
    creth = interface.ICEtherEx('0xD06527D5e56A3495252A528C4987003b712860eE')
    creth.mint({'value': '9 ether', 'from': donator})
    creth.transfer(fake, creth.balanceOf(donator), {'from': donator})
    controller.enterMarkets([creth], {'from': fake})
    lpusdt.approve(homora, 2**256-1, {'from': alice})
    lpusdt.transfer(alice, 1*10**17, {'from': accounts.at(
        '0x6C3e4cb2E96B01F4b866965A91ed4437839A121a', force=True)})
    return homora


@pytest.fixture(scope="module")
def basic_spell(admin, homora, BasicSpell):
    basic_spell = admin.deploy(BasicSpell, homora, WETH_ADDRESS)
    return basic_spell


@pytest.fixture(scope="module")
def household_spell(admin, homora, HouseHoldSpell):
    household_spell = admin.deploy(HouseHoldSpell, homora, WETH_ADDRESS)
    return household_spell


def test_homora_oracle(homora, oracle):
    assert homora.oracle() == oracle


def test_add_bank(admin, homora):
    assert homora.banks(USDT_ADDRESS)[1] == CUSDT_ADDRESS


def test_proxy_oracle_support_usdt(homora, oracle):
    assert oracle.support(USDT_ADDRESS)


def test_execute_ensure_approve(admin, homora, basic_spell):
    homora.execute(0, basic_spell, USDT_ADDRESS,
                   basic_spell.ensureApprove.encode_input(USDT_ADDRESS, admin))
    assert basic_spell.approved(USDT_ADDRESS, admin)


def test_execute_put_collateral(alice, homora, usdt, household_spell):
    tx = homora.execute(0,
                        household_spell,
                        USDT_ETH_ADDRESS,
                        household_spell.putCollateral.encode_input(
                            USDT_ETH_ADDRESS, '0.00001 ether'
                        ),
                        {'from': alice})
    position_id = tx.return_value
    print(homora.getCollateralETHValue(position_id),
          homora.getBorrowETHValue(position_id))
    tx = homora.execute(
        position_id,  # position id
        household_spell,
        '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',  # USDT-ETH
        household_spell.borrow.encode_input(
            '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
            '500000000',  # $500
        ),
        {'from': alice},
    )
    print('bal', usdt.balanceOf(alice))
    assert 0 == 1
