// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IOracle.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IERC20Wrapper.sol';

contract ProxyOracle is IOracle, Governable {
  using SafeMath for uint;

  /// The governor sets oracle token factor for a token.
  event SetTokenFactor(address indexed token, TokenFactors tokenFactor);
  /// The governor unsets oracle token factor for a token.
  event UnsetTokenFactor(address indexed token);
  /// The governor sets token whitelist for an ERC1155 token.
  event SetWhitelist(address indexed token, bool ok);

  struct TokenFactors {
    uint16 borrowFactor; // The borrow factor for this token, multiplied by 1e4.
    uint16 collateralFactor; // The collateral factor for this token, multiplied by 1e4.
    uint16 liqIncentive; // The liquidation incentive, multiplied by 1e4.
  }

  IBaseOracle public immutable source; // Main oracle source
  mapping(address => TokenFactors) public tokenFactors; // Mapping from token address to oracle info.
  mapping(address => bool) public whitelistERC1155; // Mapping from token address to whitelist status

  /// @dev Create the contract and initialize the first governor.
  constructor(IBaseOracle _source) public {
    source = _source;
    __Governable__init();
  }

  /// @dev Set oracle token factors for the given list of token addresses.
  /// @param tokens List of tokens to set info
  /// @param _tokenFactors List of oracle token factors
  function setTokenFactors(address[] memory tokens, TokenFactors[] memory _tokenFactors)
    external
    onlyGov
  {
    require(tokens.length == _tokenFactors.length, 'inconsistent length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      require(_tokenFactors[idx].borrowFactor >= 10000, 'borrow factor must be at least 100%');
      require(
        _tokenFactors[idx].collateralFactor <= 10000,
        'collateral factor must be at most 100%'
      );
      require(_tokenFactors[idx].liqIncentive >= 10000, 'incentive must be at least 100%');
      require(_tokenFactors[idx].liqIncentive <= 20000, 'incentive must be at most 200%');
      tokenFactors[tokens[idx]] = _tokenFactors[idx];
      emit SetTokenFactor(tokens[idx], _tokenFactors[idx]);
    }
  }

  /// @dev Unset token factors for the given list of token addresses
  /// @param tokens List of tokens to unset info
  function unsetTokenFactors(address[] memory tokens) external onlyGov {
    for (uint idx = 0; idx < tokens.length; idx++) {
      delete tokenFactors[tokens[idx]];
      emit UnsetTokenFactor(tokens[idx]);
    }
  }

  /// @dev Set whitelist status for the given list of token addresses.
  /// @param tokens List of tokens to set whitelist status
  /// @param ok Whitelist status
  function setWhitelistERC1155(address[] memory tokens, bool ok) external onlyGov {
    for (uint idx = 0; idx < tokens.length; idx++) {
      whitelistERC1155[tokens[idx]] = ok;
      emit SetWhitelist(tokens[idx], ok);
    }
  }

  /// @dev Return whether the oracle supports evaluating collateral value of the given token.
  /// @param token ERC1155 token address to check for support
  /// @param id ERC1155 token id to check for support
  function supportWrappedToken(address token, uint id) external view override returns (bool) {
    if (!whitelistERC1155[token]) return false;
    address tokenUnderlying = IERC20Wrapper(token).getUnderlyingToken(id);
    return tokenFactors[tokenUnderlying].liqIncentive != 0;
  }

  /// @dev Return the amount of token out as liquidation reward for liquidating token in.
  /// @param tokenIn Input ERC20 token
  /// @param tokenOut Output ERC1155 token
  /// @param tokenOutId Output ERC1155 token id
  /// @param amountIn Input ERC20 token amount
  function convertForLiquidation(
    address tokenIn,
    address tokenOut,
    uint tokenOutId,
    uint amountIn
  ) external view override returns (uint) {
    require(whitelistERC1155[tokenOut], 'bad token');
    address tokenOutUnderlying = IERC20Wrapper(tokenOut).getUnderlyingToken(tokenOutId);
    uint rateUnderlying = IERC20Wrapper(tokenOut).getUnderlyingRate(tokenOutId);
    TokenFactors memory tokenFactorIn = tokenFactors[tokenIn];
    TokenFactors memory tokenFactorOut = tokenFactors[tokenOutUnderlying];
    require(tokenFactorIn.liqIncentive != 0, 'bad underlying in');
    require(tokenFactorOut.liqIncentive != 0, 'bad underlying out');
    uint pxIn = source.getETHPx(tokenIn);
    uint pxOut = source.getETHPx(tokenOutUnderlying);
    uint amountOut = amountIn.mul(pxIn).div(pxOut);
    amountOut = amountOut.mul(2**112).div(rateUnderlying);
    return
      amountOut.mul(tokenFactorIn.liqIncentive).mul(tokenFactorOut.liqIncentive).div(10000 * 10000);
  }

  /// @dev Return the value of the given input as ETH for collateral purpose.
  /// @param token ERC1155 token address to get collateral value
  /// @param id ERC1155 token id to get collateral value
  /// @param amount Token amount to get collateral value
  /// @param owner Token owner address (currently unused by this implementation)
  function asETHCollateral(
    address token,
    uint id,
    uint amount,
    address owner
  ) external view override returns (uint) {
    require(whitelistERC1155[token], 'bad token');
    address tokenUnderlying = IERC20Wrapper(token).getUnderlyingToken(id);
    uint rateUnderlying = IERC20Wrapper(token).getUnderlyingRate(id);
    uint amountUnderlying = amount.mul(rateUnderlying).div(2**112);
    TokenFactors memory tokenFactor = tokenFactors[tokenUnderlying];
    require(tokenFactor.liqIncentive != 0, 'bad underlying collateral');
    uint ethValue = source.getETHPx(tokenUnderlying).mul(amountUnderlying).div(2**112);
    return ethValue.mul(tokenFactor.collateralFactor).div(10000);
  }

  /// @dev Return the value of the given input as ETH for borrow purpose.
  /// @param token ERC20 token address to get borrow value
  /// @param amount ERC20 token amount to get borrow value
  /// @param owner Token owner address (currently unused by this implementation)
  function asETHBorrow(
    address token,
    uint amount,
    address owner
  ) external view override returns (uint) {
    TokenFactors memory tokenFactor = tokenFactors[token];
    require(tokenFactor.liqIncentive != 0, 'bad underlying borrow');
    uint ethValue = source.getETHPx(token).mul(amount).div(2**112);
    return ethValue.mul(tokenFactor.borrowFactor).div(10000);
  }

  /// @dev Return whether the ERC20 token is supported
  /// @param token The ERC20 token to check for support
  function support(address token) external view override returns (bool) {
    try source.getETHPx(token) returns (uint px) {
      return px != 0 && tokenFactors[token].liqIncentive != 0;
    } catch {
      return false;
    }
  }
}
