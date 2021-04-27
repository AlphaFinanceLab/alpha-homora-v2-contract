pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC1155/IERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/token/ERC1155/ERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import './Governable.sol';
import '../interfaces/IBank.sol';
import '../interfaces/IWERC20.sol';
import '../interfaces/IWStakingRewards.sol';
import '../interfaces/IWMasterChef.sol';
import '../interfaces/IWLiquidityGauge.sol';

interface IWrapper {
  function burn(uint, uint) external;
}

library LiquidateRouterSafeMath {
  using SafeMath for uint;

  /// @dev Return round-up division
  function ceilDiv(uint a, uint b) internal pure returns (uint) {
    return a.add(b).sub(1).div(b);
  }
}

contract HomoraBankV2LiquidateRouter is Governable {
  using SafeMath for uint;
  using LiquidateRouterSafeMath for uint;
  using SafeERC20 for IERC20;

  IBank bank;

  mapping(address => mapping(address => bool)) approved;

  constructor(IBank _bank) public {
    __Governable__init();
    bank = _bank;
  }

  /// @dev Ensure the target is approved
  /// @param token Token to approve
  /// @param spender Target address to approve to
  function ensureApprove(address token, address spender) internal {
    if (!approved[token][spender]) {
      IERC20(token).safeApprove(spender, uint(-1));
      approved[token][spender] = true;
    }
  }

  /// @dev Liquidate Homora Bank's position and unwrap ERC1155 to ERC-20 LP token
  /// @param positionId Position id to liquidate
  /// @param debtToken Debt token to repay on behalf of the position owner
  /// @param amountCall Amount of debt token to repay (uint(-1) to repay all)
  /// @param minLPOut Min LP amount out (slippage control)
  function liquidate(
    uint positionId,
    address debtToken,
    uint amountCall,
    uint minLPOut
  ) external {
    bank.accrue(debtToken);
    (, , , uint totalDebt, uint totalShare) = bank.getBankInfo(debtToken);
    (, address collToken, uint collId, ) = bank.getPositionInfo(positionId);
    uint oldShare = bank.getPositionDebtShareOf(positionId, debtToken);
    uint oldDebt = oldShare.mul(totalDebt).ceilDiv(totalShare);

    if (amountCall == uint(-1)) {
      amountCall = oldDebt;
    }

    IERC20(debtToken).safeTransferFrom(msg.sender, address(this), amountCall);
    ensureApprove(debtToken, address(bank));

    bank.liquidate(positionId, debtToken, amountCall);

    bytes32 target = keccak256(abi.encodePacked(ERC1155(collToken).uri(collId)));
    if (target == keccak256(abi.encodePacked('WERC20'))) {
      IWERC20(collToken).burn(
        address(collId),
        IERC1155(collToken).balanceOf(address(this), collId)
      );
      uint lpBalance = IERC20(address(collId)).balanceOf(address(this));
      require(lpBalance >= minLPOut, 'Actual LP amount out too low!');
      IERC20(address(collId)).safeTransfer(msg.sender, lpBalance);
    } else {
      IWrapper(collToken).burn(collId, IERC1155(collToken).balanceOf(address(this), collId));
      address lp = IERC20Wrapper(collToken).getUnderlyingToken(collId);
      uint lpBalance = IERC20(lp).balanceOf(address(this));
      require(lpBalance >= minLPOut, 'Actual LP amount out too low!');
      IERC20(lp).safeTransfer(msg.sender, lpBalance);

      IERC20 rewardToken;
      if (target == keccak256(abi.encodePacked('WMasterChef'))) {
        rewardToken = IERC20(IWMasterChef(collToken).sushi());
      } else if (target == keccak256(abi.encodePacked('WLiquidityGauge'))) {
        rewardToken = IERC20(IWLiquidityGauge(collToken).crv());
      } else if (target == keccak256(abi.encodePacked('WStakingRewards'))) {
        rewardToken = IERC20(IWStakingRewards(collToken).reward());
      }

      uint reward = rewardToken.balanceOf(address(this));
      if (reward > 0) {
        rewardToken.safeTransfer(msg.sender, reward);
      }
    }
  }

  /// @dev Withdraw stuck ERC20 token
  /// @param token Token to withdraw
  function withdrawERC20(address token) external onlyGov {
    require(msg.sender == governor, 'not gov');
    uint balance = IERC20(token).balanceOf(address(this));
    if (balance > 0) {
      IERC20(token).safeTransfer(msg.sender, balance);
    }
  }

  /// @dev Withdraw stuck ERC1155 token
  /// @param token ERC1155 token
  /// @param id ERC1155 token id
  function withdrawERC1155(address token, uint id) external onlyGov {
    require(msg.sender == governor, 'not gov');
    uint balance = IERC1155(token).balanceOf(address(this), id);
    if (balance > 0) {
      IERC1155(token).safeTransferFrom(address(this), msg.sender, id, balance, new bytes(0));
    }
  }

  function onERC1155Received(
    address,
    address,
    uint,
    uint,
    bytes calldata
  ) external view returns (bytes4) {
    return this.onERC1155Received.selector;
  }
}
