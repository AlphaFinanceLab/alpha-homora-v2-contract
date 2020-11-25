pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';

import '../../interfaces/IBank.sol';
import '../../interfaces/IWETH.sol';

library ERC20ApproveInfinite {
  using SafeERC20 for IERC20;

  /// @dev Convenient function to safe approve infinite spending.
  /// @param token The token to call approve action on.
  /// @param spender The spender to authorize infinite spending.
  function approveInfinite(IERC20 token, address spender) internal {
    token.safeApprove(spender, 0);
    token.safeApprove(spender, uint(-1));
  }
}

contract BasicSpell {
  using ERC20ApproveInfinite for IERC20;

  IBank public bank;
  address public weth;

  constructor(IBank _bank, address _weth) public {
    bank = _bank;
    weth = _weth;
  }

  /// @dev Internal call to convert msg.value ETH to WETH inside the contract.
  function doTransmitETH() internal {
    if (msg.value > 0) {
      IWETH(weth).deposit{value: msg.value}();
    }
  }

  /// @dev Internal call to transmit tokens from the bank if amount is positive.
  /// @param token The token to perform the transmit action.
  /// @param amount The amount to transmit.
  function doTransmit(address token, uint amount) internal {
    if (amount > 0) {
      bank.transmit(token, amount);
    }
  }

  /// @dev Internal call to refund tokens to the current bank executor.
  /// @param token The token to perform the refund action.
  function doRefund(address token) internal {
    uint balance = IERC20(token).balanceOf(address(this));
    if (balance > 0) {
      IERC20(token).transfer(bank.EXECUTOR(), balance);
    }
  }

  /// @dev Internal call to refund all WETH to the current executor as native ETH.
  function doRefundETH() internal {
    uint balance = IWETH(weth).balanceOf(address(this));
    if (balance > 0) {
      IWETH(weth).withdraw(balance);
      (bool success, ) = bank.EXECUTOR().call{value: balance}(new bytes(0));
      require(success, 'refund ETH failed');
    }
  }

  /// @dev Internal call to borrow tokens from the bank on behalf of the current executor.
  /// @param token The token to borrow from the bank.
  /// @param amount The amount to borrow.
  function doBorrow(address token, uint amount) internal {
    if (amount > 0) {
      bank.borrow(token, amount);
    }
  }

  /// @dev Internal call to repay tokens to the bank on behalf of the current executor.
  /// @param token The token to repay to the bank.
  /// @param amount The amount to repay.
  function doRepay(address token, uint amount) internal {
    if (amount > 0) {
      bank.repay(token, amount);
    }
  }

  /// @dev Internal call to put collateral tokens to the bank.
  /// @param token The collateral token to put to the bank.
  /// @param amount The amount to put to the bank.
  function doPutCollateral(address token, uint amount) internal {
    if (amount > 0) {
      bank.putCollateral(token, amount);
    }
  }

  /// @dev Internal call to take collateral tokens bank from the bank.
  /// @param token The collateral token to take back.
  /// @param amount The amount to take back.
  function doTakeCollateral(address token, uint amount) internal {
    if (amount > 0) {
      bank.takeCollateral(token, amount);
    }
  }
}
