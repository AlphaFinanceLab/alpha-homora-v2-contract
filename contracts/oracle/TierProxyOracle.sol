pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.4.0/contracts/math/SafeMath.sol';

import '../Governable.sol';
import '../../interfaces/IOracle.sol';
import '../../interfaces/IBaseOracle.sol';
import '../../interfaces/IAlphaTier.sol';
import '../../interfaces/IERC20Wrapper.sol';

contract TierProxyOracle is IOracle, Governable {
  using SafeMath for uint;

  /// The governor sets oracle token factor for a token for a tier
  event SetTierTokenFactor(address token, uint tier, TokenFactor factor);
  /// The governor unsets oracle token factor for a token.
  event UnsetTokenFactor(address indexed token);
  /// The governor sets token whitelist for an ERC1155 token.
  event SetWhitelist(address indexed token, bool ok);

  struct TokenFactor {
    uint16 borrowFactor; // The borrow factor for this token, multiplied by 1e4.
    uint16 collateralFactor; // The collateral factor for this token, multiplied by 1e4.
  }

  IBaseOracle public immutable source; // Main oracle source
  IAlphaTier public immutable alphaTier; // alpha tier contract address
  uint public tierCount; // number of tiers
  mapping(address => TokenFactor[]) public tierTokenFactors; // Mapping from token to mapping tier to token factor.
  mapping(address => uint) public liqIncentives; // Mapping from token to liquidation incentive, multiplied by 1e4.
  mapping(address => bool) public whitelistERC1155; // Mapping from token address to whitelist status

  constructor(IBaseOracle _source, IAlphaTier _alphaTier) public {
    __Governable__init();
    source = _source;
    alphaTier = _alphaTier;
  }

  /// @dev Set token factors and liq incentives for the given list of token addresses in each tier
  /// @param _tokens List of token addresses
  /// @param _tokenFactors List of list of token factors in each tier for each token.
  function setTierTokenFactors(
    address[] calldata _tokens,
    TokenFactor[][] memory _tokenFactors,
    uint[] calldata _liqIncentives
  ) external onlyGov {
    uint tierCount_ = alphaTier.tierCount(); // to save gas
    tierCount = tierCount_; // set to storage var
    require(_tokenFactors.length == _tokens.length, 'token factors & tokens length mismatched');
    require(_liqIncentives.length == _tokens.length, 'liq incentive & tokens length mismatched');
    for (uint idx = 0; idx < _tokens.length; idx++) {
      // clear old values
      delete tierTokenFactors[_tokens[idx]];
      // push new values
      for (uint i = 0; i < _tokenFactors[idx].length; i++) {
        // check values
        if (i > 0) {
          require(
            _tokenFactors[idx][i - 1].borrowFactor > _tokenFactors[idx][i].borrowFactor,
            'borrow factor should be strictly decreasing'
          );
          require(
            _tokenFactors[idx][i - 1].collateralFactor < _tokenFactors[idx][i].collateralFactor,
            'collateral factor should be strictly increasing'
          );
        }
        // push
        tierTokenFactors[_tokens[idx]].push(_tokenFactors[idx][i]);
        emit SetTierTokenFactor(_tokens[idx], i, _tokenFactors[idx][i]);
      }
      // set liq incentive
      require(_liqIncentives[idx] != 0, 'liq incentive should != 0');
      liqIncentives[_tokens[idx]] = _liqIncentives[idx];
    }
  }

  /// @dev Unset token factors and liq incentives for the given list of token addresses
  /// @param _tokens List of token addresses
  function unsetTierTokenFactors(address[] calldata _tokens) external onlyGov {
    for (uint idx = 0; idx < _tokens.length; idx++) {
      delete liqIncentives[_tokens[idx]];
      delete tierTokenFactors[_tokens[idx]];
    }
  }

  /// @dev Set whitelist status for the given list of token addresses.
  /// @param tokens List of tokens to set whitelist status
  /// @param ok Whitelist status
  function setWhitelistERC1155(address[] calldata tokens, bool ok) external onlyGov {
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
    return liqIncentives[tokenUnderlying] != 0;
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
    uint liqIncentiveIn = liqIncentives[tokenIn];
    uint liqIncentiveOut = liqIncentives[tokenOutUnderlying];
    require(liqIncentiveIn != 0, 'bad underlying in');
    require(liqIncentiveOut != 0, 'bad underlying out');
    uint pxIn = source.getETHPx(tokenIn);
    uint pxOut = source.getETHPx(tokenOutUnderlying);
    uint amountOut = amountIn.mul(pxIn).div(pxOut);
    amountOut = amountOut.mul(2**112).div(rateUnderlying);
    return amountOut.mul(liqIncentiveIn).mul(liqIncentiveOut).div(10000 * 10000);
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
    uint tier = alphaTier.getAlphaTier(owner);
    uint collFactor = tierTokenFactors[tokenUnderlying][tier].collateralFactor;
    require(liqIncentives[token] != 0, 'bad underlying collateral');
    uint ethValue = source.getETHPx(tokenUnderlying).mul(amountUnderlying).div(2**112);
    return ethValue.mul(collFactor).div(10000);
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
    uint tier = alphaTier.getAlphaTier(owner);
    uint borrFactor = tierTokenFactors[token][tier].borrowFactor;
    require(liqIncentives[token] != 0, 'bad underlying borrow');
    uint ethValue = source.getETHPx(token).mul(amount).div(2**112);
    return ethValue.mul(borrFactor).div(10000);
  }

  /// @dev Return whether the ERC20 token is supported
  /// @param token The ERC20 token to check for support
  function support(address token) external view override returns (bool) {
    try source.getETHPx(token) returns (uint px) {
      return px != 0 && liqIncentives[token] != 0;
    } catch {
      return false;
    }
  }
}
