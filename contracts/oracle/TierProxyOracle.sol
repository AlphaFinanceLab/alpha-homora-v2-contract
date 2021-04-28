pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IOracle.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IAlphaTier.sol';

contract TierProxyOracle is IOracle, Governable {
  using SafeMath for uint;

  event SetTierTokenFactor(uint tier, address token, TokenFactor factor);

  struct TokenFactor {
    uint16 borrowFactor; // The borrow factor for this token, multiplied by 1e4.
    uint16 collateralFactor; // The collateral factor for this token, multiplied by 1e4.
    uint16 liqIncentive; // The liquidation incentive, multiplied by 1e4.
  }

  IBaseOracle public immutable source; // Main oracle source
  IAlphaTier public immutable alphaTier; // alpha tier contract address
  uint tierCount; // number of tiers
  mapping(uint => mapping(address => TokenFactor)) public tierTokenFactors; // Mapping from tier to mapping from token to token factor.

  constructor(IBaseOracle _source, IAlphaTier _alphaTier) public {
    __Governable__init();
    source = _source;
    alphaTier = _alphaTier;
  }

  /// @dev Set token factors for the given list of token addresses in each tier
  /// @param _tokens List of token addresses
  /// @param _tokenFactors List of list of token factors in each tier for each token
  function setTierTokenFactors(address[] calldata _tokens, TokenFactor[][] calldata _tokenFactors)
    external
    onlyGov
  {
    uint tierCount = alphaTier.tierCount();
    require(_tokens.length == tierCount, 'tokens length != tier count');
    require(_tokenFactors.length == tierCount, 'token factors length != tier count');

    uint tokenFactorsLength = _tokenFactors[0].length;

    for (uint tier = 0; tier < tierCount; tier++) {
      require(_tokenFactors[tier].length == tokenFactorsLength, 'inconsistent token factor length');
      for (uint i = 0; i < tokensLength; i++) {
        if (i > 0) {
          require(
            _tokenFactors[tier][i - 1].borrowFactor > _tokenFactors[tier][i].borrowFactor,
            'borrow factor should be strictly decreasing'
          );
          require(
            _tokenFactors[tier][i - 1].collateralFactor < _tokenFactors[tier][i].collateralFactor,
            'collateral factor should be strictly increasing'
          );
        }
        tierTokenFactors[tier][_tokens[i]] = _tokenFactors[tier][i];
        emit SetTierTokenFactor(tier, _tokens[i], _tokenFactors[tier][i]);
      }
    }
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
