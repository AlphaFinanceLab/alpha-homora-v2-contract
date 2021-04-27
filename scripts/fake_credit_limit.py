from brownie import interface

from .utils import *


def fake_credit_limit(bank):
    comptroller = interface.IAny('0xab1c342c7bf5ec5f02adea1c2270670bca144cbb')
    comptroller_admin = comptroller.admin()
    comptroller._setCreditLimit(bank, 2**256-1, {'from': comptroller_admin})


def main():
    bank = interface.IAny('0x5f5Cd91070960D13ee549C9CC47e7a4Cd00457bb')
    fake_credit_limit(bank)
