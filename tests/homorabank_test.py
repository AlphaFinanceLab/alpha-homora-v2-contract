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
usdtAddress = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
cusdtAddress = "0x797AAB1ce7c01eB727ab980762bA88e7133d2157"
weth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
keep3rV1Oracle = "0x73353801921417F465377c8d898c6f4C0270282C"


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
def k3pr_oracle(admin, BasicK3PROracle):
    k3pr_oracle = admin.deploy(BasicK3PROracle, keep3rV1Oracle)
    return k3pr_oracle


@pytest.fixture(scope="module")
def proxy_oracle(admin, k3pr_oracle, ProxyOracle):
    proxy_oracle = admin.deploy(ProxyOracle)
    proxy_oracle.setOracles(
        [usdtAddress], [(k3pr_oracle, 10000, 10000, 10000)])
    return proxy_oracle


@pytest.fixture(scope="module")
def homora(admin, alice, proxy_oracle, HomoraBank):
    homora = admin.deploy(HomoraBank)
    homora.initialize(proxy_oracle, 1000)
    homora.addBank(usdtAddress, cusdtAddress, {'from': admin})
    return homora


@pytest.fixture(scope="module")
def basic_spell(admin, homora, BasicSpell):
    basic_spell = admin.deploy(BasicSpell, homora, weth)
    return basic_spell


@pytest.fixture(scope="module")
def household_spell(admin, homora, HouseHoldSpell):
    household_spell = admin.deploy(HouseHoldSpell, homora, weth)
    return household_spell


def test_homora_oracle(homora, proxy_oracle):
    assert homora.oracle() == proxy_oracle


def test_add_bank(admin, homora):
    assert homora.banks(usdtAddress)[1] == cusdtAddress


def test_proxy_oracle_support_usdt(homora, proxy_oracle):
    assert proxy_oracle.support(usdtAddress)


def test_execute_ensure_approve(admin, homora, basic_spell):
    homora.execute(0, basic_spell, usdtAddress,
                   basic_spell.ensureApprove.encode_input(usdtAddress, admin))
    assert basic_spell.approved(usdtAddress, admin)
