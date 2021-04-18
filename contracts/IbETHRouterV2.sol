// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/SafeERC20.sol';
import './utils/HomoraMath.sol';

interface IbETHRouterV2IbETHv2 is IERC20 {
  function deposit() external payable;

  function withdraw(uint amount) external;
}

interface IbETHRouterV2UniswapPair is IERC20 {
  function token0() external view returns (address);

  function getReserves()
    external
    view
    returns (
      uint,
      uint,
      uint
    );
}

interface IbETHRouterV2UniswapRouter {
  function factory() external view returns (address);

  function addLiquidity(
    address tokenA,
    address tokenB,
    uint amountADesired,
    uint amountBDesired,
    uint amountAMin,
    uint amountBMin,
    address to,
    uint deadline
  )
    external
    returns (
      uint amountA,
      uint amountB,
      uint liquidity
    );

  function removeLiquidity(
    address tokenA,
    address tokenB,
    uint liquidity,
    uint amountAMin,
    uint amountBMin,
    address to,
    uint deadline
  ) external returns (uint amountA, uint amountB);

  function swapExactTokensForTokens(
    uint amountIn,
    uint amountOutMin,
    address[] calldata path,
    address to,
    uint deadline
  ) external returns (uint[] memory amounts);
}

interface IbETHRouterV2UniswapFactory {
  function getPair(address tokenA, address tokenB) external view returns (address);
}

contract IbETHRouterV2 {
  using SafeMath for uint;
  using SafeERC20 for IERC20;

  IERC20 public immutable alpha;
  IbETHRouterV2IbETHv2 public immutable ibETHv2;
  IbETHRouterV2UniswapPair public immutable lpToken;
  IbETHRouterV2UniswapRouter public immutable router;

  constructor(
    IERC20 _alpha,
    IbETHRouterV2IbETHv2 _ibETHv2,
    IbETHRouterV2UniswapRouter _router
  ) public {
    IbETHRouterV2UniswapPair _lpToken =
      IbETHRouterV2UniswapPair(
        IbETHRouterV2UniswapFactory(_router.factory()).getPair(address(_alpha), address(_ibETHv2))
      );
    alpha = _alpha;
    ibETHv2 = _ibETHv2;
    lpToken = _lpToken;
    router = _router;
    IERC20(_alpha).safeApprove(address(_router), uint(-1));
    IERC20(_ibETHv2).safeApprove(address(_router), uint(-1));
    IERC20(_lpToken).safeApprove(address(_router), uint(-1));
  }

  function optimalDeposit(
    uint amtA,
    uint amtB,
    uint resA,
    uint resB
  ) internal pure returns (uint swapAmt, bool isReversed) {
    if (amtA.mul(resB) >= amtB.mul(resA)) {
      swapAmt = _optimalDepositA(amtA, amtB, resA, resB);
      isReversed = false;
    } else {
      swapAmt = _optimalDepositA(amtB, amtA, resB, resA);
      isReversed = true;
    }
  }

  function _optimalDepositA(
    uint amtA,
    uint amtB,
    uint resA,
    uint resB
  ) internal pure returns (uint) {
    require(amtA.mul(resB) >= amtB.mul(resA), 'Reversed');
    uint a = 997;
    uint b = uint(1997).mul(resA);
    uint _c = (amtA.mul(resB)).sub(amtB.mul(resA));
    uint c = _c.mul(1000).div(amtB.add(resB)).mul(resA);
    uint d = a.mul(c).mul(4);
    uint e = HomoraMath.sqrt(b.mul(b).add(d));
    uint numerator = e.sub(b);
    uint denominator = a.mul(2);
    return numerator.div(denominator);
  }

  function swapExactETHToAlpha(
    uint amountOutMin,
    address to,
    uint deadline
  ) external payable {
    ibETHv2.deposit{value: msg.value}();
    address[] memory path = new address[](2);
    path[0] = address(ibETHv2);
    path[1] = address(alpha);
    router.swapExactTokensForTokens(
      ibETHv2.balanceOf(address(this)),
      amountOutMin,
      path,
      to,
      deadline
    );
  }

  function swapExactAlphaToETH(
    uint amountIn,
    uint amountOutMin,
    address to,
    uint deadline
  ) external {
    alpha.transferFrom(msg.sender, address(this), amountIn);
    address[] memory path = new address[](2);
    path[0] = address(alpha);
    path[1] = address(ibETHv2);
    router.swapExactTokensForTokens(amountIn, 0, path, address(this), deadline);
    ibETHv2.withdraw(ibETHv2.balanceOf(address(this)));
    uint ethBalance = address(this).balance;
    require(ethBalance >= amountOutMin, '!amountOutMin');
    (bool success, ) = to.call{value: ethBalance}(new bytes(0));
    require(success, '!eth');
  }

  function addLiquidityETHAlphaOptimal(
    uint amountAlpha,
    uint minLp,
    address to,
    uint deadline
  ) external payable {
    if (amountAlpha > 0) alpha.transferFrom(msg.sender, address(this), amountAlpha);
    ibETHv2.deposit{value: msg.value}();
    uint amountIbETHv2 = ibETHv2.balanceOf(address(this));
    uint swapAmt;
    bool isReversed;
    {
      (uint r0, uint r1, ) = lpToken.getReserves();
      (uint ibETHv2Reserve, uint alphaReserve) =
        lpToken.token0() == address(ibETHv2) ? (r0, r1) : (r1, r0);
      (swapAmt, isReversed) = optimalDeposit(
        amountIbETHv2,
        amountAlpha,
        ibETHv2Reserve,
        alphaReserve
      );
    }
    if (swapAmt > 0) {
      address[] memory path = new address[](2);
      (path[0], path[1]) = isReversed
        ? (address(alpha), address(ibETHv2))
        : (address(ibETHv2), address(alpha));
      router.swapExactTokensForTokens(swapAmt, 0, path, address(this), deadline);
    }
    (, , uint liquidity) =
      router.addLiquidity(
        address(alpha),
        address(ibETHv2),
        alpha.balanceOf(address(this)),
        ibETHv2.balanceOf(address(this)),
        0,
        0,
        to,
        deadline
      );
    require(liquidity >= minLp, '!minLP');
  }

  function addLiquidityIbETHv2AlphaOptimal(
    uint amountIbETHv2,
    uint amountAlpha,
    uint minLp,
    address to,
    uint deadline
  ) external {
    if (amountAlpha > 0) alpha.transferFrom(msg.sender, address(this), amountAlpha);
    if (amountIbETHv2 > 0) ibETHv2.transferFrom(msg.sender, address(this), amountIbETHv2);
    uint swapAmt;
    bool isReversed;
    {
      (uint r0, uint r1, ) = lpToken.getReserves();
      (uint ibETHv2Reserve, uint alphaReserve) =
        lpToken.token0() == address(ibETHv2) ? (r0, r1) : (r1, r0);
      (swapAmt, isReversed) = optimalDeposit(
        amountIbETHv2,
        amountAlpha,
        ibETHv2Reserve,
        alphaReserve
      );
    }
    if (swapAmt > 0) {
      address[] memory path = new address[](2);
      (path[0], path[1]) = isReversed
        ? (address(alpha), address(ibETHv2))
        : (address(ibETHv2), address(alpha));
      router.swapExactTokensForTokens(swapAmt, 0, path, address(this), deadline);
    }
    (, , uint liquidity) =
      router.addLiquidity(
        address(alpha),
        address(ibETHv2),
        alpha.balanceOf(address(this)),
        ibETHv2.balanceOf(address(this)),
        0,
        0,
        to,
        deadline
      );
    require(liquidity >= minLp, '!minLP');
  }

  function removeLiquidityETHAlpha(
    uint liquidity,
    uint minETH,
    uint minAlpha,
    address to,
    uint deadline
  ) external {
    lpToken.transferFrom(msg.sender, address(this), liquidity);
    router.removeLiquidity(
      address(alpha),
      address(ibETHv2),
      liquidity,
      minAlpha,
      0,
      address(this),
      deadline
    );
    alpha.transfer(msg.sender, alpha.balanceOf(address(this)));
    ibETHv2.withdraw(ibETHv2.balanceOf(address(this)));
    uint ethBalance = address(this).balance;
    require(ethBalance >= minETH, '!minETH');
    (bool success, ) = to.call{value: ethBalance}(new bytes(0));
    require(success, '!eth');
  }

  function removeLiquidityAlphaOnly(
    uint liquidity,
    uint minAlpha,
    address to,
    uint deadline
  ) external {
    lpToken.transferFrom(msg.sender, address(this), liquidity);
    router.removeLiquidity(
      address(alpha),
      address(ibETHv2),
      liquidity,
      0,
      0,
      address(this),
      deadline
    );
    address[] memory path = new address[](2);
    path[0] = address(ibETHv2);
    path[1] = address(alpha);
    router.swapExactTokensForTokens(
      ibETHv2.balanceOf(address(this)),
      0,
      path,
      address(this),
      deadline
    );
    uint alphaBalance = alpha.balanceOf(address(this));
    require(alphaBalance >= minAlpha, '!minAlpha');
    alpha.transfer(to, alphaBalance);
  }

  receive() external payable {
    require(msg.sender == address(ibETHv2), '!ibETHv2');
  }
}
