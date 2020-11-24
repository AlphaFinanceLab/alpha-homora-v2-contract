pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';

import '../interfaces/IBank.sol';
import '../interfaces/IWETH.sol';

contract HomoraETHRouter {
  IBank public bank;
  IWETH public weth;
  IERC20 public homo;

  constructor(IBank _bank, IWETH _weth) public {
    bank = _bank;
    weth = _weth;
    // TODO: homo = ...
    weth.approve(address(_bank), uint(-1));
  }

  // TODO
  function deposit() public payable {
    weth.deposit{value: msg.value}();
    bank.deposit(address(weth), msg.value);
    homo.transfer(msg.sender, homo.balanceOf(address(this)));
  }

  function withdraw(uint share) public {
    bank.withdraw(address(weth), share);
    uint value = weth.balanceOf(address(this));
    weth.withdraw(value);
    (bool success, ) = msg.sender.call{value: value}(new bytes(0));
    require(success, 'withdraw transfer failed');
  }

  receive() external payable {
    require(msg.sender == address(weth));
  }
}
