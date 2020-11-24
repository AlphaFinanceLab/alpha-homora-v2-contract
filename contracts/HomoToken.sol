pragma solidity 0.6.12;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/token/ERC20/ERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/access/Ownable.sol';

interface ERC20Detailed {
  /// @dev Return the token name.
  function name() external view returns (string memory);

  /// @dev Return the token symbol.
  function symbol() external view returns (string memory);

  /// @dev Return the token decimals.
  function decimals() external view returns (uint8);
}

library ERC20DetailedSafe {
  /// @dev Return the name of the given token, but fallback to safeSymbol on error.
  /// @param token The token to query for the name.
  function safeName(address token) internal view returns (string memory) {
    try ERC20Detailed(token).name() returns (string memory name) {
      return name;
    } catch (bytes memory) {
      return safeSymbol(token);
    }
  }

  /// @dev Return the symbol of the given token, or '???' if not available.
  /// @param token The token to query for the symbol.
  function safeSymbol(address token) internal view returns (string memory) {
    try ERC20Detailed(token).symbol() returns (string memory symbol) {
      return symbol;
    } catch (bytes memory) {
      return '???';
    }
  }

  /// @dev Return the decimals of the given token, or 18 if not available.
  /// @param token The token to query for the decimals.
  function safeDecimals(address token) internal view returns (uint8) {
    try ERC20Detailed(token).decimals() returns (uint8 decimals) {
      return decimals;
    } catch (bytes memory) {
      return 18;
    }
  }
}

contract HomoToken is ERC20, Ownable {
  using ERC20DetailedSafe for address;
  address public base; /// The address of the base token.

  /// @dev Create a new interest-bearing token instance and assign the creator as owner.
  /// @param _base The base token used for token details.
  constructor(address _base)
    public
    ERC20(
      string(abi.encodePacked('Interest Bearing ', _base.safeName())),
      string(abi.encodePacked('ib', _base.safeSymbol()))
    )
  {
    _setupDecimals(_base.safeDecimals());
    base = _base;
  }

  /// @dev Mint more interest-bearing tokens to the given user.
  /// @param usr The beneficiary to receive the tokens.
  /// @param amt The amount of tokens to mint.
  function mint(address usr, uint amt) public onlyOwner {
    _mint(usr, amt);
  }

  /// @dev Burn some interest-bearing tokens from the given user.
  /// @param usr The user to have their tokens burned.
  /// @param amt The amount of tokens to burn.
  function burn(address usr, uint amt) public onlyOwner {
    _burn(usr, amt);
  }
}
