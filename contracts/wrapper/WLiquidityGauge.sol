pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC1155/ERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/utils/ReentrancyGuard.sol';

import '../utils/HomoraMath.sol';
import '../../interfaces/IERC20Wrapper.sol';
import '../../interfaces/ICurveRegistry.sol';
import '../../interfaces/ILiquidityGauge.sol';

interface ILiquidityGaugeMinter {
  function mint(address gauge) external;
}

contract WLiquidityGauge is ERC1155('WLiquidityGauge'), ReentrancyGuard, IERC20Wrapper {
  using SafeMath for uint;
  using HomoraMath for uint;
  using SafeERC20 for IERC20;

  ICurveRegistry public registry;
  mapping(uint => mapping(uint => ILiquidityGauge)) public gauges;

  constructor(ICurveRegistry _registry) public {
    registry = _registry;
  }

  function encodeId(
    uint pid,
    uint gid,
    uint crvPerShare
  ) public pure returns (uint id) {
    require(pid < (1 << 8), 'bad pid');
    require(gid < (1 << 8), 'bad gid');
    require(crvPerShare < (1 << 240), 'bad crv per share');
    return (pid << 248) | (gid << 240) | crvPerShare;
  }

  function decodeId(uint id)
    public
    pure
    returns (
      uint pid,
      uint gid,
      uint crvPerShare
    )
  {
    pid = id >> 248; // First 8 bits
    gid = (id >> 240) & (255); // Next 8 bits
    crvPerShare = id & ((1 << 240) - 1); // Last 240 bits
  }

  function getUnderlying(uint id) external view override returns (address) {
    (uint pid, uint gid, ) = decodeId(id);
    ILiquidityGauge gauge = gauges[pid][gid];
    require(address(gauge) != address(0), 'no gauge');
    return gauge.lp_token();
  }

  function getCrvPerShare(ILiquidityGauge gauge) public view returns (uint) {
    uint totalCrv = gauge.integrate_fraction(address(this));
    uint totalStake = gauge.balanceOf(address(this));
    return totalCrv.mul(1e18).div(totalStake);
  }

  function mint(
    uint pid,
    uint gid,
    uint amount
  ) external nonReentrant returns (uint) {
    ILiquidityGauge gauge = gauges[pid][gid];
    if (address(gauge) == address(0)) {
      address pool = registry.pool_list(pid);
      require(pool != address(0), 'no pool');
      (address[10] memory _gauges, ) = registry.get_gauges(pool);
      gauge = ILiquidityGauge(_gauges[gid]);
      require(address(gauge) != address(0), 'no gauge');
      gauges[pid][gid] = gauge;
    }
    IERC20 lpToken = IERC20(gauge.lp_token());
    if (lpToken.allowance(address(this), address(gauge)) != 0) {
      // We only need to do this once per gauge, as it's practically impossible to spend MAX_UINT.
      lpToken.approve(address(gauge), uint(-1));
    }
    lpToken.safeTransferFrom(msg.sender, address(this), amount);
    gauge.deposit(amount);
    uint id = encodeId(pid, gid, getCrvPerShare(gauge));
    _mint(msg.sender, id, amount, '');
    return id;
  }

  function burn(uint id, uint amount) external nonReentrant returns (uint) {
    if (amount == uint(-1)) {
      amount = balanceOf(msg.sender, id);
    }
    (uint pid, uint gid, uint stCrvPerShare) = decodeId(id);
    _burn(msg.sender, id, amount);
    ILiquidityGauge gauge = gauges[pid][gid];
    gauge.withdraw(amount);
    uint enCrvPerShare = getCrvPerShare(gauge);
    IERC20(gauge.lp_token()).safeTransfer(msg.sender, amount);
    ILiquidityGaugeMinter(gauge.minter()).mint(address(gauge));
    uint stCrv = stCrvPerShare.mul(amount).divCeil(1e18);
    uint enCrv = enCrvPerShare.mul(amount).div(1e18);
    if (enCrv > stCrv) {
      IERC20(gauge.crv_token()).safeTransfer(msg.sender, enCrv.sub(stCrv));
    }
    return pid;
  }
}
