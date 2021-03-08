pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC1155/IERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC1155/ERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import '../interfaces/IBank.sol';
import '../interfaces/IWERC20.sol';
import '../interfaces/IWStakingRewards.sol';
import '../interfaces/IWMasterChef.sol';
import '../interfaces/IWLiquidityGauge.sol';

interface IWrapper {
  function burn(uint, uint) external;
}

contract HomoraBankV2LiquidateRouter {
  using SafeMath for uint;
  using SafeERC20 for IERC20;

  IBank bank;

  mapping(address => mapping(address => bool)) approved;

  constructor(IBank _bank) public {
    bank = _bank;
  }

  function ensureApprove(address token, address spender) public {
    if (!approved[token][spender]) {
      IERC20(token).safeApprove(spender, uint(-1));
      approved[token][spender] = true;
    }
  }

  function liquidate(
    uint positionId,
    address debtToken,
    uint amountCall
  ) external {
    bank.accrue(debtToken);
    (, , , uint totalDebt, uint totalShare) = bank.getBankInfo(debtToken);
    (, address collToken, uint collId, ) = bank.getPositionInfo(positionId);
    uint oldShare = bank.getPositionDebtShareOf(positionId, debtToken);
    uint oldDebt = oldShare.mul(totalDebt).div(totalShare);

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
      IERC20(address(collId)).safeTransfer(
        msg.sender,
        IERC20(address(collId)).balanceOf(address(this))
      );
    } else {
      IWrapper(collToken).burn(collId, IERC1155(collToken).balanceOf(msg.sender, collId));
      address lp = IERC20Wrapper(collToken).getUnderlyingToken(collId);
      IERC20(lp).safeTransfer(msg.sender, IERC20(lp).balanceOf(address(this)));

      IERC20 rewardToken;
      if (target == keccak256(abi.encodePacked('WMasterChef'))) {
        rewardToken = IERC20(IWMasterChef(collToken).sushi());
      } else if (target == keccak256(abi.encodePacked('WLiquidityGuage'))) {
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

  function onERC1155Received(address, address, uint, uint, bytes calldata) external view returns (bytes4) {
    return this.onERC1155Received.selector;
  }
}
