from brownie import interface


def print_uni_sushi_data(pos_id, interface):
    bank = interface.IAny('0xba5eBAf3fc1Fcca67147050Bf80462393814E54B')
    _, collToken, collId, collSize = bank.getPositionInfo(pos_id)
    pool = interface.IAny(collToken).getUnderlyingToken(collId)

    r0, r1, _ = interface.IAny(pool).getReserves()
    supply = interface.IAny(pool).totalSupply()

    token0 = interface.IAny(pool).token0()
    token1 = interface.IAny(pool).token1()

    print(f'{interface.IAny(token0).symbol()} amount:', r0 * collSize // supply / 10**interface.IAny(token0).decimals())
    print(f'{interface.IAny(token1).symbol()} amount:', r1 * collSize // supply / 10**interface.IAny(token1).decimals())
