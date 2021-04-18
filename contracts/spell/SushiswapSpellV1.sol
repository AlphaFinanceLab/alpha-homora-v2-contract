// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import './WhitelistSpell.sol';
import '../utils/HomoraMath.sol';
import '../../interfaces/IUniswapV2Factory.sol';
import '../../interfaces/IUniswapV2Router02.sol';
import '../../interfaces/IUniswapV2Pair.sol';
import '../../interfaces/IWMasterChef.sol';

contract SushiswapSpellV1 is WhitelistSpell {
  using SafeMath for uint;
  using HomoraMath for uint;

  IUniswapV2Factory public immutable factory; // Sushiswap factory
  IUniswapV2Router02 public immutable router; // Sushiswap router

  mapping(address => mapping(address => address)) public pairs; // Mapping from tokenA to (mapping from tokenB to LP token)

  IWMasterChef public immutable wmasterchef; // Wrapped masterChef

  address public immutable sushi; // Sushi token address

  constructor(
    IBank _bank,
    address _werc20,
    IUniswapV2Router02 _router,
    address _wmasterchef
  ) public WhitelistSpell(_bank, _werc20, _router.WETH()) {
    router = _router;
    factory = IUniswapV2Factory(_router.factory());
    wmasterchef = IWMasterChef(_wmasterchef);
    IWMasterChef(_wmasterchef).setApprovalForAll(address(_bank), true);
    sushi = address(IWMasterChef(_wmasterchef).sushi());
  }

  /// @dev Return the LP token for the token pairs (can be in any order)
  /// @param tokenA Token A to get LP token
  /// @param tokenB Token B to get LP token
  function getAndApprovePair(address tokenA, address tokenB) public returns (address) {
    address lp = pairs[tokenA][tokenB];
    if (lp == address(0)) {
      lp = factory.getPair(tokenA, tokenB);
      require(lp != address(0), 'no lp token');
      ensureApprove(tokenA, address(router));
      ensureApprove(tokenB, address(router));
      ensureApprove(lp, address(router));
      pairs[tokenA][tokenB] = lp;
      pairs[tokenB][tokenA] = lp;
    }
    return lp;
  }

  /// @dev Compute optimal deposit amount
  /// @param amtA amount of token A desired to deposit
  /// @param amtB amount of token B desired to deposit
  /// @param resA amount of token A in reserve
  /// @param resB amount of token B in reserve
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

  /// @dev Compute optimal deposit amount helper.
  /// @param amtA amount of token A desired to deposit
  /// @param amtB amount of token B desired to deposit
  /// @param resA amount of token A in reserve
  /// @param resB amount of token B in reserve
  /// Formula: https://blog.alphafinance.io/byot/
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

  struct Amounts {
    uint amtAUser; // Supplied tokenA amount
    uint amtBUser; // Supplied tokenB amount
    uint amtLPUser; // Supplied LP token amount
    uint amtABorrow; // Borrow tokenA amount
    uint amtBBorrow; // Borrow tokenB amount
    uint amtLPBorrow; // Borrow LP token amount
    uint amtAMin; // Desired tokenA amount (slippage control)
    uint amtBMin; // Desired tokenB amount (slippage control)
  }

  /// @dev Add liquidity to Sushiswap pool
  /// @param tokenA Token A for the pair
  /// @param tokenB Token B for the pair
  /// @param amt Amounts of tokens to supply, borrow, and get.
  function addLiquidityInternal(
    address tokenA,
    address tokenB,
    Amounts calldata amt,
    address lp
  ) internal {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');

    // 1. Get user input amounts
    doTransmitETH();
    doTransmit(tokenA, amt.amtAUser);
    doTransmit(tokenB, amt.amtBUser);
    doTransmit(lp, amt.amtLPUser);

    // 2. Borrow specified amounts
    doBorrow(tokenA, amt.amtABorrow);
    doBorrow(tokenB, amt.amtBBorrow);
    doBorrow(lp, amt.amtLPBorrow);

    // 3. Calculate optimal swap amount
    uint swapAmt;
    bool isReversed;
    {
      uint amtA = IERC20(tokenA).balanceOf(address(this));
      uint amtB = IERC20(tokenB).balanceOf(address(this));
      uint resA;
      uint resB;
      if (IUniswapV2Pair(lp).token0() == tokenA) {
        (resA, resB, ) = IUniswapV2Pair(lp).getReserves();
      } else {
        (resB, resA, ) = IUniswapV2Pair(lp).getReserves();
      }
      (swapAmt, isReversed) = optimalDeposit(amtA, amtB, resA, resB);
    }

    // 4. Swap optimal amount
    if (swapAmt > 0) {
      address[] memory path = new address[](2);
      (path[0], path[1]) = isReversed ? (tokenB, tokenA) : (tokenA, tokenB);
      router.swapExactTokensForTokens(swapAmt, 0, path, address(this), block.timestamp);
    }

    // 5. Add liquidity
    uint balA = IERC20(tokenA).balanceOf(address(this));
    uint balB = IERC20(tokenB).balanceOf(address(this));
    if (balA > 0 || balB > 0) {
      router.addLiquidity(
        tokenA,
        tokenB,
        balA,
        balB,
        amt.amtAMin,
        amt.amtBMin,
        address(this),
        block.timestamp
      );
    }
  }

  /// @dev Add liquidity to Sushiswap pool, with no staking rewards (use WERC20 wrapper)
  /// @param tokenA Token A for the pair
  /// @param tokenB Token B for the pair
  /// @param amt Amounts of tokens to supply, borrow, and get.
  function addLiquidityWERC20(
    address tokenA,
    address tokenB,
    Amounts calldata amt
  ) external payable {
    address lp = getAndApprovePair(tokenA, tokenB);
    // 1-5. add liquidity
    addLiquidityInternal(tokenA, tokenB, amt, lp);

    // 6. Put collateral
    doPutCollateral(lp, IERC20(lp).balanceOf(address(this)));

    // 7. Refund leftovers to users
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);
  }

  /// @dev Add liquidity to Sushiswap pool, with staking to masterChef
  /// @param tokenA Token A for the pair
  /// @param tokenB Token B for the pair
  /// @param amt Amounts of tokens to supply, borrow, and get.
  /// @param pid Pool id
  function addLiquidityWMasterChef(
    address tokenA,
    address tokenB,
    Amounts calldata amt,
    uint pid
  ) external payable {
    address lp = getAndApprovePair(tokenA, tokenB);
    (address lpToken, , , ) = wmasterchef.chef().poolInfo(pid);
    require(lpToken == lp, 'incorrect lp token');

    // 1-5. add liquidity
    addLiquidityInternal(tokenA, tokenB, amt, lp);

    // 6. Take out collateral
    (, address collToken, uint collId, uint collSize) = bank.getCurrentPositionInfo();
    if (collSize > 0) {
      (uint decodedPid, ) = wmasterchef.decodeId(collId);
      require(pid == decodedPid, 'incorrect pid');
      require(collToken == address(wmasterchef), 'collateral token & wmasterchef mismatched');
      bank.takeCollateral(address(wmasterchef), collId, collSize);
      wmasterchef.burn(collId, collSize);
    }

    // 7. Put collateral
    ensureApprove(lp, address(wmasterchef));
    uint amount = IERC20(lp).balanceOf(address(this));
    uint id = wmasterchef.mint(pid, amount);
    bank.putCollateral(address(wmasterchef), id, amount);

    // 8. Refund leftovers to users
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);

    // 9. Refund sushi
    doRefund(sushi);
  }

  struct RepayAmounts {
    uint amtLPTake; // Take out LP token amount (from Homora)
    uint amtLPWithdraw; // Withdraw LP token amount (back to caller)
    uint amtARepay; // Repay tokenA amount
    uint amtBRepay; // Repay tokenB amount
    uint amtLPRepay; // Repay LP token amount
    uint amtAMin; // Desired tokenA amount
    uint amtBMin; // Desired tokenB amount
  }

  /// @dev Remove liquidity from Sushiswap pool
  /// @param tokenA Token A for the pair
  /// @param tokenB Token B for the pair
  /// @param amt Amounts of tokens to take out, withdraw, repay, and get.
  function removeLiquidityInternal(
    address tokenA,
    address tokenB,
    RepayAmounts calldata amt,
    address lp
  ) internal {
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    uint positionId = bank.POSITION_ID();

    uint amtARepay = amt.amtARepay;
    uint amtBRepay = amt.amtBRepay;
    uint amtLPRepay = amt.amtLPRepay;

    // 2. Compute repay amount if MAX_INT is supplied (max debt)
    if (amtARepay == uint(-1)) {
      amtARepay = bank.borrowBalanceCurrent(positionId, tokenA);
    }
    if (amtBRepay == uint(-1)) {
      amtBRepay = bank.borrowBalanceCurrent(positionId, tokenB);
    }
    if (amtLPRepay == uint(-1)) {
      amtLPRepay = bank.borrowBalanceCurrent(positionId, lp);
    }

    // 3. Compute amount to actually remove
    uint amtLPToRemove = IERC20(lp).balanceOf(address(this)).sub(amt.amtLPWithdraw);

    // 4. Remove liquidity
    uint amtA;
    uint amtB;
    if (amtLPToRemove > 0) {
      (amtA, amtB) = router.removeLiquidity(
        tokenA,
        tokenB,
        amtLPToRemove,
        0,
        0,
        address(this),
        block.timestamp
      );
    }

    // 5. MinimizeTrading
    uint amtADesired = amtARepay.add(amt.amtAMin);
    uint amtBDesired = amtBRepay.add(amt.amtBMin);

    if (amtA < amtADesired && amtB > amtBDesired) {
      address[] memory path = new address[](2);
      (path[0], path[1]) = (tokenB, tokenA);
      router.swapTokensForExactTokens(
        amtADesired.sub(amtA),
        amtB.sub(amtBDesired),
        path,
        address(this),
        block.timestamp
      );
    } else if (amtA > amtADesired && amtB < amtBDesired) {
      address[] memory path = new address[](2);
      (path[0], path[1]) = (tokenA, tokenB);
      router.swapTokensForExactTokens(
        amtBDesired.sub(amtB),
        amtA.sub(amtADesired),
        path,
        address(this),
        block.timestamp
      );
    }

    // 6. Repay
    doRepay(tokenA, amtARepay);
    doRepay(tokenB, amtBRepay);
    doRepay(lp, amtLPRepay);

    // 7. Slippage control
    require(IERC20(tokenA).balanceOf(address(this)) >= amt.amtAMin);
    require(IERC20(tokenB).balanceOf(address(this)) >= amt.amtBMin);
    require(IERC20(lp).balanceOf(address(this)) >= amt.amtLPWithdraw);

    // 8. Refund leftover
    doRefundETH();
    doRefund(tokenA);
    doRefund(tokenB);
    doRefund(lp);
  }

  /// @dev Remove liquidity from Sushiswap pool, with no staking rewards (use WERC20 wrapper)
  /// @param tokenA Token A for the pair
  /// @param tokenB Token B for the pair
  /// @param amt Amounts of tokens to take out, withdraw, repay, and get.
  function removeLiquidityWERC20(
    address tokenA,
    address tokenB,
    RepayAmounts calldata amt
  ) external {
    address lp = getAndApprovePair(tokenA, tokenB);

    // 1. Take out collateral
    doTakeCollateral(lp, amt.amtLPTake);

    // 2-8. remove liquidity
    removeLiquidityInternal(tokenA, tokenB, amt, lp);
  }

  /// @dev Remove liquidity from Sushiswap pool, from masterChef staking
  /// @param tokenA Token A for the pair
  /// @param tokenB Token B for the pair
  /// @param amt Amounts of tokens to take out, withdraw, repay, and get.
  function removeLiquidityWMasterChef(
    address tokenA,
    address tokenB,
    RepayAmounts calldata amt
  ) external {
    address lp = getAndApprovePair(tokenA, tokenB);
    (, address collToken, uint collId, ) = bank.getCurrentPositionInfo();
    require(IWMasterChef(collToken).getUnderlyingToken(collId) == lp, 'incorrect underlying');
    require(collToken == address(wmasterchef), 'collateral token & wmasterchef mismatched');

    // 1. Take out collateral
    bank.takeCollateral(address(wmasterchef), collId, amt.amtLPTake);
    wmasterchef.burn(collId, amt.amtLPTake);

    // 2-8. remove liquidity
    removeLiquidityInternal(tokenA, tokenB, amt, lp);

    // 9. Refund sushi
    doRefund(sushi);
  }

  /// @dev Harvest SUSHI reward tokens to in-exec position's owner
  function harvestWMasterChef() external {
    (, address collToken, uint collId, ) = bank.getCurrentPositionInfo();
    (uint pid, ) = wmasterchef.decodeId(collId);
    address lp = wmasterchef.getUnderlyingToken(collId);
    require(whitelistedLpTokens[lp], 'lp token not whitelisted');
    require(collToken == address(wmasterchef), 'collateral token & wmasterchef mismatched');

    // 1. Take out collateral
    bank.takeCollateral(address(wmasterchef), collId, uint(-1));
    wmasterchef.burn(collId, uint(-1));

    // 2. put collateral
    uint amount = IERC20(lp).balanceOf(address(this));
    ensureApprove(lp, address(wmasterchef));
    uint id = wmasterchef.mint(pid, amount);
    bank.putCollateral(address(wmasterchef), id, amount);

    // 3. Refund sushi
    doRefund(sushi);
  }
}
