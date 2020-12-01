import pytest
import brownie
from brownie.network.state import Chain
from enum import IntEnum, auto
from brownie import accounts, interface, Contract

chain = Chain()

MAX_UINT256 = 2**256-1

INIT_PX = 400
INIT_RESERVE = 1000

WETH_ADDRESS = "0xd0a1e359811322d97991e03f863a0c30c2cf029c"


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
def usdt(admin, MockERC20):
    return admin.deploy(MockERC20, "USDT", "USDT")


@pytest.fixture(scope="module")
def weth(admin, WETH9):
    return admin.deploy(WETH9)


@pytest.fixture(scope="module")
def crusdt(admin, usdt, MockCErc20):
    return admin.deploy(MockCErc20, usdt.address)


@pytest.fixture(scope="module")
def mock_oracle(admin, usdt, MockOracle):
    mock_oracle = admin.deploy(MockOracle)
    mock_oracle.setETHPx(usdt.address, 500*10**18)
    return mock_oracle


@pytest.fixture(scope="module")
def oracle(admin, usdt, mock_oracle, ProxyOracle):
    oracle = admin.deploy(ProxyOracle)
    oracle.setOracles([usdt.address], [(mock_oracle, 10000, 10000, 10000)])
    return oracle


@pytest.fixture(scope="module")
def homora(admin, alice, usdt, crusdt, oracle, HomoraBank):
    homora = admin.deploy(HomoraBank)
    homora.initialize(oracle, 1000)
    homora.addBank(usdt.address, crusdt.address)
    return homora


@pytest.fixture(scope="module")
def basic_spell(admin, weth, homora, BasicSpell):
    basic_spell = admin.deploy(BasicSpell, homora.address, weth.address)
    return basic_spell


@pytest.fixture(scope="module")
def household_spell(admin, weth,  homora, HouseHoldSpell):
    household_spell = admin.deploy(
        HouseHoldSpell, homora.address, weth.address)
    return household_spell


def test_homora_oracle(homora, oracle):
    assert homora.oracle() == oracle


def test_add_bank(admin, homora, usdt, crusdt):
    assert homora.banks(usdt.address)[1] == crusdt.address


def test_proxy_oracle_support_usdt(homora, oracle, usdt):
    assert oracle.support(usdt.address)


# def test_execute_ensure_approve(admin, homora, usdt, basic_spell):
#     homora.execute(0, basic_spell, usdt.address,
#                    basic_spell.ensureApprove.encode_input(usdt.address, admin))
#     assert basic_spell.approved(usdt.address, admin)


# def test_proxy_oracle_as_eth_collateral(homora, oracle, usdt):
#     x = oracle.asETHCollateral(usdt.address, '1 ether')
#     print(x)
#     assert 1 == 0


def test_execute_put_collateral(alice, homora, usdt, household_spell):
    usdt.mint(alice.address, '100 ether')
    print('alice start', usdt.balanceOf(alice.address))
    usdt.approve(homora, 2**256-1, {'from': alice})
    tx = homora.execute(0,
                        household_spell.address,
                        usdt.address,
                        household_spell.putCollateral.encode_input(
                            usdt.address, '10 ether'
                        ),
                        {'from': alice})
    print('alice put', usdt.balanceOf(alice.address))
    print('homora put', usdt.balanceOf(homora.address))
    assert usdt.balanceOf(alice.address) == 90*10**18
    position_id = tx.return_value
    print('homora', homora.positions(position_id))
    homora.execute(position_id,
                   household_spell.address,
                   usdt.address,
                   household_spell.borrow.encode_input(
                       "0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852", '200 ether'
                   ),
                   {'from': alice})
    print('alice borrow', usdt.balanceOf(alice.address))
    print('homora put', usdt.balanceOf(homora.address))
    assert 1 == 0
