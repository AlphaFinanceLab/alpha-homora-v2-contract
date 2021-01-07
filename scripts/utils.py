from brownie import accounts, interface, Contract, chain

USDT = '0xdac17f958d2ee523a2206206994597c13d831ec7'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
DAI = '0x6b175474e89094c44da98b954eedeac495271d0f'
ADAI = '0x028171bCA77440897B824Ca71D1c56caC55b68A3'
AUSDC = '0xBcca60bB61934080951369a648Fb03DF4F96263C'
AUSDT = '0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
SUSD = '0x57ab1ec28d129707052df4df418d58a2d46d5f51'
HUSD = '0xdf574c24545e5ffecb9a659c229253d4111d87e1'
BUSD = '0x4fabb145d64652a948d72533023f6e7a623c7c53'
DPI = '0x1494ca1f11d487c2bbe4543e90080aeba4ba3c2b'
YDAI = '0x16de59092dae5ccf4a1e6439d611fd0653f0bd01'
YUSDT = '0xa1787206d5b1be0f432c4c4f96dc4d1257a1dd14'
YUSDC = '0x597ad1e0c13bfe8025993d9e79c69e1c0233522e'
YBUSD = '0x04bc0ab673d88ae9dbc9da2380cb6b79c4bca9ae'
WBTC = '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599'
RENBTC = '0xeb4c2781e4eba804ce9a9803c67d0893436bb27d'
PERP = '0xbC396689893D065F41bc2C6EcbeE5e0085233447'

CRV_LP_SUSD = '0xC25a3A3b969415c80451098fa907EC722572917F'
CRV_LP_3POOL = '0x6c3f90f043a72fa612cbac8115ee7e52bde6e490'
CRV_LP_AAVE = '0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900'


def mint_tokens(token, to, amount=None):
    if amount is None:
        # default is 1m tokens
        amount = 10**6 * 10**token.decimals()

    if token == USDT:
        owner = token.owner()
        token.issue(amount, {'from': owner})
        token.transfer(to, amount, {'from': owner})
    elif token == USDC:
        master_minter = token.masterMinter()
        token.configureMinter(master_minter, 2**256-1, {'from': master_minter})
        token.mint(to, amount, {'from': master_minter})
    elif token == DAI:
        auth = '0x9759a6ac90977b93b58547b4a71c78317f391a28'
        token.mint(to, amount, {'from': auth})
    elif token == AUSDT:
        pool = '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9'
        token.mint(to, amount, 10**18, {'from': pool})
    elif token == AUSDC:
        pool = '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9'
        token.mint(to, amount, 10**18, {'from': pool})
    elif token == ADAI:
        pool = '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9'
        token.mint(to, amount, 10**18, {'from': pool})
    elif token == WETH:
        token.deposit({'from': to, 'value': amount})
    elif token == SUSD:
        target = interface.IERC20Ex(token.target())
        issuer = '0x611Abc0e066A01AFf63910fC8935D164267eC6CF'
        target.issue(to, amount, {'from': issuer})
    elif token == HUSD:
        issuer = '0xc2fbf9b9084e92f9649ca4cec9043daac9092539'
        token.issue(to, amount, {'from': issuer})
    elif token == BUSD:
        supply_controller = token.supplyController()
        token.increaseSupply(amount, {'from': supply_controller})
        token.transfer(to, amount, {'from': supply_controller})
    elif token == YDAI:
        mint_tokens(interface.IERC20Ex(DAI), to, amount)
        interface.IERC20Ex(DAI).approve(token, 2**256-1, {'from': to})
        token.deposit(amount, {'from': to})
    elif token == YUSDT:
        mint_tokens(interface.IERC20Ex(USDT), to, amount)
        interface.IERC20Ex(USDT).approve(token, 2**256-1, {'from': to})
        token.invest(amount, {'from': to})
    elif token == YBUSD:
        mint_tokens(interface.IERC20Ex(BUSD), to, amount)
        interface.IERC20Ex(BUSD).approve(token, 2**256-1, {'from': to})
        token.deposit(amount, {'from': to})
    elif token == YUSDC:
        mint_tokens(interface.IERC20Ex(USDC), to, amount)
        interface.IERC20Ex(USDC).approve(token, 2**256-1, {'from': to})
        token.deposit(amount, {'from': to})
    elif token == DPI:
        module = token.getModules()[0]
        token.mint(to, amount, {'from': module})
    elif token == WBTC:
        owner = token.owner()
        token.mint(to, amount, {'from': owner})
    elif token == RENBTC:
        owner = token.owner()
        token.mint(to, amount, {'from': owner})
    elif token == PERP:
        owner = token.owner()
        token.addMinter(owner, {'from': owner})
        token.mint(to, amount, {'from': owner})
