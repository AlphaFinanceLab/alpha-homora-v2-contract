pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/ERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/cryptography/MerkleProof.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';
import './Governable.sol';
import '../interfaces/ICErc20.sol';

contract SafeBox is Governable, ERC20 {
  using SafeMath for uint;
  using SafeERC20 for IERC20;

  ICErc20 public immutable cToken;
  IERC20 public immutable uToken;

  address public relayer;
  bytes32 public root;
  mapping(address => uint) public claimed;

  constructor(
    ICErc20 _cToken,
    string memory _name,
    string memory _symbol
  ) public ERC20(_name, _symbol) {
    __Governable__init();
    cToken = _cToken;
    uToken = IERC20(_cToken.underlying());
    relayer = msg.sender;
  }

  function setRelayer(address _relayer) external onlyGov {
    relayer = _relayer;
  }

  function updateRoot(bytes32 _root) external {
    require(msg.sender == relayer || msg.sender == governor, '!relayer');
    root = _root;
  }

  function deposit(uint amountCall) external {
    uint uBalanceBefore = uToken.balanceOf(address(this));
    uToken.safeTransferFrom(msg.sender, address(this), amountCall);
    uint uBalanceAfter = uToken.balanceOf(address(this));
    uint cBalanceBefore = cToken.balanceOf(address(this));
    require(cToken.mint(uBalanceAfter.sub(uBalanceBefore)) == 0, '!mint');
    uint cBalanceAfter = cToken.balanceOf(address(this));
    _mint(msg.sender, cBalanceAfter.sub(cBalanceBefore));
  }

  function withdraw(uint amount) public {
    _burn(msg.sender, amount);
    uint uBalanceBefore = uToken.balanceOf(address(this));
    require(cToken.redeem(amount) == 0, '!redeem');
    uint uBalanceAfter = uToken.balanceOf(address(this));
    uToken.safeTransfer(msg.sender, uBalanceAfter.sub(uBalanceBefore));
  }

  function adminWithdraw(uint amount) external onlyGov {
    uToken.safeTransfer(msg.sender, amount);
  }

  function claim(uint totalReward, bytes32[] memory proof) public {
    bytes32 leaf = keccak256(abi.encodePacked(msg.sender, totalReward));
    require(MerkleProof.verify(proof, root, leaf), '!proof');
    uint send = totalReward.sub(claimed[msg.sender]);
    claimed[msg.sender] = totalReward;
    uToken.safeTransfer(msg.sender, send);
  }

  function claimAndWithdraw(
    uint claimAmount,
    bytes32[] memory proof,
    uint withdrawAmount
  ) external {
    claim(claimAmount, proof);
    withdraw(withdrawAmount);
  }
}
