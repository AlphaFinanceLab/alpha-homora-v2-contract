pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';

import '../../interfaces/IBank.sol';
import '../../interfaces/IWETH.sol';

library ERC20ApproveInfinite {
  using SafeERC20 for IERC20;

  function approveInfinite(IERC20 token, address spender) internal {
    token.safeApprove(spender, 0);
    token.safeApprove(spender, uint(-1));
  }
}

contract BasicWizard {
  using ERC20ApproveInfinite for IERC20;

  IBank public bank;
  address public weth;

  constructor(IBank _bank, address _weth) public {
    bank = _bank;
    weth = _weth;
  }

  function doTransmitETH() internal {
    if (msg.value > 0) {
      IWETH(weth).deposit{value: msg.value}();
    }
  }

  function doTransmit(address token, uint amount) internal {
    if (amount > 0) {
      bank.transmit(token, amount);
    }
  }

  function doRefund(address token) internal {
    uint balance = IERC20(token).balanceOf(address(this));
    if (balance > 0) {
      IERC20(token).transfer(bank.EXECUTOR(), balance);
    }
  }

  function doRefundETH() internal {
    uint balance = IWETH(weth).balanceOf(address(this));
    if (balance > 0) {
      IWETH(weth).withdraw(balance);
      (bool success, ) = bank.EXECUTOR().call{value: balance}(new bytes(0));
      require(success, 'refund ETH failed');
    }
  }

  function doBorrow(address token, uint amount) internal {
    if (amount > 0) {
      bank.borrow(token, amount);
    }
  }

  function doRepay(address token, uint amount) internal {
    if (amount > 0) {
      bank.repay(token, amount);
    }
  }

  function doTakeCollateral(address token, uint amount) internal {
    if (amount > 0) {
      bank.takeCollateral(token, amount);
    }
  }

  function doPutCollateral(address token, uint amount) internal {
    if (amount > 0) {
      bank.putCollateral(token, amount);
    }
  }
}
