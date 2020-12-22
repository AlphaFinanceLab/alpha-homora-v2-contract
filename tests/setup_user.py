import pytest


@pytest.fixture(scope='module')
def admin(a):
    return a[0]


@pytest.fixture(scope='function')
def alice(a):
    return a[1]


@pytest.fixture(scope='function')
def bob(a):
    return a[2]


@pytest.fixture(scope='function')
def eve(a):
    return a[3]
