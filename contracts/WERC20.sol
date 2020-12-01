pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC1155/ERC1155.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/utils/ReentrancyGuard.sol';

contract WERC20 is ERC1155(''), ReentrancyGuard {
  using SafeERC20 for IERC20;

  /// @dev Mint ERC1155 token for the given ERC20 token.
  function mint(IERC20 token, uint amount) external nonReentrant {
    uint balanceBefore = token.balanceOf(address(this));
    token.safeTransferFrom(msg.sender, address(this), amount);
    uint balanceAfter = token.balanceOf(address(this));
    _mint(msg.sender, uint(address(token)), balanceAfter.sub(balanceBefore), '');
  }

  /// @dev Burn ERC1155 token to redeem ERC20 token back.
  function burn(IERC20 token, uint amount) external nonReentrant {
    _burn(msg.sender, uint(address(token)), amount);
    token.safeTransfer(msg.sender, amount);
  }
}
