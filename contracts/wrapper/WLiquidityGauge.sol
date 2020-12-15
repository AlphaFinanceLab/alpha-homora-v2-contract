pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC1155/ERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/utils/ReentrancyGuard.sol';

import '../Governable.sol';
import '../utils/HomoraMath.sol';
import '../../interfaces/IERC20Wrapper.sol';
import '../../interfaces/ICurveRegistry.sol';
import '../../interfaces/ILiquidityGauge.sol';

interface ILiquidityGaugeMinter {
  function mint(address gauge) external;
}

contract WLiquidityGauge is ERC1155('WLiquidityGauge'), ReentrancyGuard, IERC20Wrapper, Governable {
  using SafeMath for uint;
  using HomoraMath for uint;
  using SafeERC20 for IERC20;

  struct GaugeInfo {
    ILiquidityGauge impl;
    uint accCrvPerShare;
  }

  ICurveRegistry public immutable registry;
  mapping(uint => mapping(uint => GaugeInfo)) public gauges;

  constructor(ICurveRegistry _registry) public {
    __Governable__init();
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
    ILiquidityGauge impl = gauges[pid][gid].impl;
    require(address(impl) != address(0), 'no gauge');
    return impl.lp_token();
  }

  function registerGauge(uint pid, uint gid) external onlyGov {
    require(address(gauges[pid][gid].impl) == address(0), 'gauge already exists');
    address pool = registry.pool_list(pid);
    require(pool != address(0), 'no pool');
    (address[10] memory _gauges, ) = registry.get_gauges(pool);
    address gauge = _gauges[gid];
    require(gauge != address(0), 'no gauge');
    gauges[pid][gid] = GaugeInfo({impl: ILiquidityGauge(gauge), accCrvPerShare: 0});
  }

  function mint(
    uint pid,
    uint gid,
    uint amount
  ) external nonReentrant returns (uint) {
    GaugeInfo storage gauge = gauges[pid][gid];
    ILiquidityGauge impl = gauge.impl;
    require(address(impl) != address(0), 'gauge not registered');
    mintCrv(gauge);
    IERC20 lpToken = IERC20(impl.lp_token());
    if (lpToken.allowance(address(this), address(impl)) == 0) {
      // We only need to do this once per gauge, as it's practically impossible to spend MAX_UINT.
      lpToken.approve(address(impl), uint(-1));
    }
    lpToken.safeTransferFrom(msg.sender, address(this), amount);
    impl.deposit(amount);
    uint id = encodeId(pid, gid, gauge.accCrvPerShare);
    _mint(msg.sender, id, amount, '');
    return id;
  }

  function burn(uint id, uint amount) external nonReentrant returns (uint) {
    if (amount == uint(-1)) {
      amount = balanceOf(msg.sender, id);
    }
    (uint pid, uint gid, uint stCrvPerShare) = decodeId(id);
    _burn(msg.sender, id, amount);
    GaugeInfo storage gauge = gauges[pid][gid];
    ILiquidityGauge impl = gauge.impl;
    require(address(impl) != address(0), 'gauge not registered');
    mintCrv(gauge);
    impl.withdraw(amount);
    IERC20(impl.lp_token()).safeTransfer(msg.sender, amount);
    uint stCrv = stCrvPerShare.mul(amount).divCeil(1e18);
    uint enCrv = gauge.accCrvPerShare.mul(amount).div(1e18);
    if (enCrv > stCrv) {
      IERC20(impl.crv_token()).safeTransfer(msg.sender, enCrv.sub(stCrv));
    }
    return pid;
  }

  function mintCrv(GaugeInfo storage gauge) internal {
    ILiquidityGauge impl = gauge.impl;
    address crv = impl.crv_token();
    uint balanceBefore = IERC20(crv).balanceOf(address(this));
    ILiquidityGaugeMinter(impl.minter()).mint(address(impl));
    uint balanceAfter = IERC20(crv).balanceOf(address(this));
    uint gain = balanceAfter.sub(balanceBefore);
    uint supply = impl.balanceOf(address(this));
    if (gain > 0 && supply > 0) {
      gauge.accCrvPerShare = gauge.accCrvPerShare.add(gain.mul(1e18).div(supply));
    }
  }
}
