pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';

import '../interfaces/IBank.sol';
import '../interfaces/IWETH.sol';

contract HomoraETHRouter {
  IBank public bank;
  IWETH public weth;
  IERC20 public ib;

  /// @dev Create a new Homora ETH router smart contract.
  /// @param _bank The Homora bank smart contract.
  /// @param _weth The wrapped ETH smart contract.
  constructor(IBank _bank, IWETH _weth) public {
    bank = _bank;
    weth = _weth;
    ib = IERC20(bank.ibTokenOf(address(weth)));
    weth.approve(address(_bank), uint(-1));
    ib.approve(address(_bank), uint(-1));
  }

  /// @dev Deposit ETH into Homora Bank and return back ibETH to the caller.
  function deposit() public payable {
    weth.deposit{value: msg.value}();
    bank.deposit(address(weth), msg.value);
    ib.transfer(msg.sender, ib.balanceOf(address(this)));
  }

  /// @dev Withdraw ibETH for the caller and return back the ETH.
  function withdraw(uint share) public {
    ib.transferFrom(msg.sender, address(this), share);
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
