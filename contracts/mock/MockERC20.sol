pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/ERC20.sol';

contract MockERC20 is ERC20 {
  constructor(string memory _name, string memory _symbol) public ERC20(_name, _symbol) {}

  function mint(address to, uint amount) public {
    _mint(to, amount);
  }

  function burn(address from, uint amount) public {
    _burn(from, amount);
  }
}
