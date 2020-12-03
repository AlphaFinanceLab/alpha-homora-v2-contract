from brownie import accounts, interface, Contract
from brownie import (
    WMasterChef
)


def almostEqual(a, b):
    thresh = 0.01
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)


def setup_transfer(asset, fro, to, amt):
    print(f'sending from {fro} {amt} {asset.name()} to {to}')
    asset.transfer(to, amt, {'from': fro})


def main():
    admin = accounts[0]

    alice = accounts[1]
    usdt = interface.IERC20Ex('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    usdc = interface.IERC20Ex('0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
    weth = interface.IERC20Ex('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
    sushi = interface.IERC20Ex('0x6b3595068778dd592e39a122f4f5a5cf09c90fe2')

    lpusdc = interface.IERC20Ex('0x397ff1542f962076d0bfe58ea045ffa2d347aca0')  # pid 1
    lpusdt = interface.IERC20Ex('0x06da0fd433c1a5d7a4faa01111c044910a184553')  # pid 0

    chef = accounts.at('0xc2edad668740f1aa35e4d8f227fb8e17dca888cd', force=True)
    wchef = WMasterChef.deploy(chef, {'from': admin})

    # set approval
    usdt.approve(wchef, 2**256-1, {'from': alice})
    usdc.approve(wchef, 2**256-1, {'from': alice})
    weth.approve(wchef, 2**256-1, {'from': alice})
    lpusdt.approve(wchef, 2**256-1, {'from': alice})
    lpusdc.approve(wchef, 2**256-1, {'from': alice})
    lpusdt.approve(chef, 2**256-1, {'from': alice})
    lpusdc.approve(chef, 2**256-1, {'from': alice})

    # setup initial funds 10^6 USDT + 10^6 USDC + 10^4 WETH to alice
    setup_transfer(usdt, accounts.at('0xbe0eb53f46cd790cd13851d5eff43d12404d33e8',
                                     force=True), alice, 10**6 * 10**6)
    setup_transfer(usdc, accounts.at('0xa191e578a6736167326d05c119ce0c90849e84b7',
                                     force=True), alice, 10**6 * 10**6)
    setup_transfer(weth, accounts.at('0xceff51756c56ceffca006cd410b03ffc46dd3a58',
                                     force=True), alice, 10**6 * 10**6)
    setup_transfer(lpusdt, accounts.at(
        '0x6b4e746fa3c8fd5ec1861833c883360c11c4c5b3', force=True), alice, 10**10)
    setup_transfer(lpusdc, accounts.at(
        '0x43d3e86ca8a9a46c19473d7ec83cc328b881648c', force=True), alice, 10**10)

    ######################################################################
    # Check encoding and decoding ids
    print('######################################################################')
    print('Case 1.')

    pid = 10
    sushiPerShare = 210
    encoded_id = wchef.encodeId(pid, sushiPerShare)
    print('encoded id', encoded_id)
    assert (encoded_id >> 240) == pid
    assert (encoded_id & ((1 << 240) - 1)) == sushiPerShare

    d_pid, d_sushiPerShare = wchef.decodeId(encoded_id)
    print('decoded pid', d_pid)
    print('decoded sushiPerShare', d_sushiPerShare)
    assert d_pid == pid
    assert d_sushiPerShare == sushiPerShare

    ######################################################################
    # check getUnderlying

    pid = 10
    sushiPerShare = 210
    id_num = wchef.encodeId(pid, sushiPerShare)
    lpToken = wchef.getUnderlying(id_num)
    print('lpToken', lpToken)
    assert lpToken == '0xCb2286d9471cc185281c4f763d34A962ED212962'

    ######################################################################
    # check mint & burn
    print('######################################################################')
    print('Case 2.')

    pid = 0
    amt = 10**10

    print('alice lpusdt balance', lpusdt.balanceOf(alice))

    # mint
    tx = wchef.mint(pid, amt, {'from': alice})

    encoded_id = tx.return_value
    print('tx status', tx.status)
    print('encoded id', encoded_id)
    _, _, _, prevAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('prevAccSushiPerShare', prevAccSushiPerShare)
    print('alice wlpusdt balance', wchef.balanceOf(alice, encoded_id))
    assert tx.status == 1
    assert wchef.balanceOf(alice, encoded_id) == amt

    # burn exact
    prevSushiBalance = sushi.balanceOf(alice)
    tx = wchef.burn(encoded_id, amt, {'from': alice})
    _, _, _, newAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('tx status', tx.status)
    print('newAccSushiPerShare', newAccSushiPerShare)
    print('alice wlpusdt balance', wchef.balanceOf(alice, encoded_id))

    print('alice sushi balance', sushi.balanceOf(alice))
    receivedSushi = sushi.balanceOf(alice) - prevSushiBalance

    assert tx.status == 1
    assert wchef.balanceOf(alice, encoded_id) == 0  # remove all
    assert almostEqual(receivedSushi, (newAccSushiPerShare-prevAccSushiPerShare)*amt//10**12)

    # check reward same as staking directly
    prevSushi = sushi.balanceOf(alice)
    print('alice lpusdt balance', interface.IERC20Ex(lpusdt).balanceOf(alice))
    tx = interface.IMasterChef(chef).deposit(pid, amt, {'from': alice})
    tx = interface.IMasterChef(chef).withdraw(pid, amt, {'from': alice})
    receivedSushiFromChef = sushi.balanceOf(alice) - prevSushi
    print('receivedSushiFromChef', receivedSushiFromChef)
    assert almostEqual(receivedSushi, receivedSushiFromChef)

    ######################################################################
    # check mint & burn max_int

    print('######################################################################')
    print('Case 3.')

    pid = 0
    amt = 10**10

    print('alice lpusdt balance', lpusdt.balanceOf(alice))

    # mint
    tx = wchef.mint(pid, amt, {'from': alice})

    encoded_id = tx.return_value
    print('tx status', tx.status)
    print('encoded id', encoded_id)
    _, _, _, prevAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('prevAccSushiPerShare', prevAccSushiPerShare)
    print('alice wlpusdt balance', wchef.balanceOf(alice, encoded_id))
    assert tx.status == 1
    assert wchef.balanceOf(alice, encoded_id) == amt

    # burn all
    prevSushiBalance = sushi.balanceOf(alice)
    tx = wchef.burn(encoded_id, 2**256-1, {'from': alice})
    _, _, _, newAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('tx status', tx.status)
    print('newAccSushiPerShare', newAccSushiPerShare)
    print('alice wlpusdt balance', wchef.balanceOf(alice, encoded_id))

    print('alice sushi balance', sushi.balanceOf(alice))
    receivedSushi = sushi.balanceOf(alice) - prevSushiBalance

    assert tx.status == 1
    assert wchef.balanceOf(alice, encoded_id) == 0  # remove all
    assert almostEqual(sushi.balanceOf(
        alice) - prevSushiBalance, (newAccSushiPerShare-prevAccSushiPerShare)*amt//10**12)

    # check reward same as staking directly
    prevSushi = sushi.balanceOf(alice)
    print('alice lpusdt balance', interface.IERC20Ex(lpusdt).balanceOf(alice))
    tx = interface.IMasterChef(chef).deposit(pid, amt, {'from': alice})
    tx = interface.IMasterChef(chef).withdraw(pid, amt, {'from': alice})
    receivedSushiFromChef = sushi.balanceOf(alice) - prevSushi
    print('receivedSushiFromChef', receivedSushiFromChef)
    assert almostEqual(receivedSushi, receivedSushiFromChef)

    ######################################################################
    # check mint & burn (try more than available--revert, half, then remaining)
    print('######################################################################')
    print('Case 4.')

    pid = 0
    amt = 10**10

    print('alice lpusdt balance', lpusdt.balanceOf(alice))

    # mint
    startSushiBalance = sushi.balanceOf(alice)
    tx = wchef.mint(pid, amt, {'from': alice})

    encoded_id = tx.return_value
    print('encoded id', encoded_id)
    _, _, _, prevAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('accSushiPerShare', prevAccSushiPerShare)
    assert tx.status == 1
    assert wchef.balanceOf(alice, encoded_id) == amt

    # burn too much (expected failed)
    prevSushiBalance = sushi.balanceOf(alice)
    _, _, _, prevAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    try:
        tx = wchef.burn(encoded_id, amt + 1, {'from': alice})
        assert tx.status == 0
    except:
        pass

    _, _, _, newAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('accSushiPerShare', newAccSushiPerShare)

    print('alice wlpusdt balance', wchef.balanceOf(alice, encoded_id))
    print('alice sushi balance', sushi.balanceOf(alice))
    assert prevSushiBalance == sushi.balanceOf(alice)
    assert wchef.balanceOf(alice, encoded_id) == amt

    # burn half
    prevSushiBalance = sushi.balanceOf(alice)
    _, _, _, prevAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)

    tx = wchef.burn(encoded_id, amt // 2, {'from': alice})
    _, _, _, newAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('accSushiPerShare', newAccSushiPerShare)

    print('alice wlpusdt balance', wchef.balanceOf(alice, encoded_id))
    print('alice sushi balance', sushi.balanceOf(alice))

    assert tx.status == 1
    assert almostEqual(sushi.balanceOf(
        alice) - prevSushiBalance, (newAccSushiPerShare-prevAccSushiPerShare)*amt//2//10**12)
    assert almostEqual(wchef.balanceOf(alice, encoded_id), amt - amt//2)

    # burn remaining
    prevSushiBalance = sushi.balanceOf(alice)

    tx = wchef.burn(encoded_id, 2**256-1, {'from': alice})
    _, _, _, newAccSushiPerShare = interface.IMasterChef(chef).poolInfo(0)
    print('accSushiPerShare', newAccSushiPerShare)

    print('alice wlpusdt balance', wchef.balanceOf(alice, encoded_id))
    print('alice sushi balance', sushi.balanceOf(alice))

    receivedSushi = sushi.balanceOf(alice) - prevSushiBalance

    assert tx.status == 1
    assert almostEqual(sushi.balanceOf(
        alice) - prevSushiBalance, (newAccSushiPerShare-prevAccSushiPerShare)*amt//2//10**12)
    assert wchef.balanceOf(alice, encoded_id) == 0

    # check reward same as staking directly
    prevSushi = sushi.balanceOf(alice)
    print('alice lpusdt balance', interface.IERC20Ex(lpusdt).balanceOf(alice))
    tx = interface.IMasterChef(chef).deposit(pid, amt, {'from': alice})  # stake all
    tx = interface.IMasterChef(chef).withdraw(pid, amt//2, {'from': alice})  # redeem half
    tx = interface.IMasterChef(chef).withdraw(pid, amt-amt//2, {'from': alice})  # redeem remaining
    receivedSushiFromChef = sushi.balanceOf(alice) - prevSushi
    print('receivedSushiFromChef', receivedSushiFromChef)
    assert almostEqual(receivedSushi, receivedSushiFromChef)
