pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import 'OpenZeppelin/openzeppelin-contracts@3.2.0/contracts/math/SafeMath.sol';

import './Governable.sol';
import '../interfaces/IInterestRateModel.sol';

contract TripleSlopeInterestRate is IInterestRateModel, Governable {
  using SafeMath for uint;

  event SetInterestRate(address token, SlopeData slope);
  event RemoveInterestRate(address token);

  /// The triple slope data structure, consisting of 6 small integers. See description below.
  struct SlopeData {
    uint8 exists; // 1 if exists, 0 if not.
    uint32 R0; // The base interest rate basis point per year.
    uint32 R1; // The level 1 slope, growing from 0 to R1 as utilization goes from 0% to U1.
    uint32 R2; // The level 2 slope, growing from 0 to R2 as utilization goes from U1 to U2.
    uint32 R3; // The level 3 slope, growing from 0 to R3 as utilization goes from U2 to 100%.
    uint32 U1; // Utilization stop 1.
    uint32 U2; // Utilization stop 2.
  }

  mapping(address => SlopeData) public slopes; // The slope data points for all tokens.

  /// @dev Create the smart contract and set msg.sender as the initial governor.
  constructor() public {
    Governable.initialize();
  }

  /// @dev Set interest rate slopt for given token address.
  /// @param token The token contract to set interest rate.
  /// @param slope The slope data to set for the token.
  function setInterestRate(address token, SlopeData memory slope) public onlyGov {
    require(slope.exists == 1, 'bad exists');
    require(slope.R0 <= 1000000, 'bad R0 data'); // sanity cap at 10000% per year.
    require(slope.R1 <= 1000000, 'bad R1 data'); // sanity cap at 10000% per year.
    require(slope.R2 <= 1000000, 'bad R2 data'); // sanity cap at 10000% per year.
    require(0 < slope.U1, 'U1 must not be zero');
    require(slope.U1 < slope.U2, 'U1 must be less than U2');
    require(slope.U2 < 10000, 'U2 must be less than 100%');
    slopes[token] = slope;
    emit SetInterestRate(token, slope);
  }

  /// @dev Remove interest rates for all of the given tokens.
  /// @param tokens The tokens to remove interest rates.
  function removeInterestRates(address[] memory tokens) public onlyGov {
    for (uint idx = 0; idx < tokens.length; idx++) {
      address token = tokens[idx];
      require(slopes[token].exists == 1, 'slope does not exist');
      slopes[token].exists = 0;
      emit RemoveInterestRate(token);
    }
  }

  /// @dev Return the interest rate per year in basis point given the parameters.
  /// @param token The token address to query for interest rate.
  /// @param supply The current total supply value from lenders.
  /// @param borrow The current total borrow value from borrowers.
  /// @param reserve The current unwithdrawn reserve funds.
  function getBorrowRate(
    address token,
    uint supply,
    uint borrow,
    uint reserve
  ) public view override returns (uint) {
    SlopeData memory slope = slopes[token];
    require(slope.exists == 1, 'slope does not exist');
    uint utilization = borrow.mul(10000).div(supply.add(reserve));
    if (utilization <= slope.U1) {
      uint extra = (utilization * slope.R1) / slope.U1;
      return slope.R0 + extra;
    } else if (utilization <= slope.U2) {
      uint extra = ((utilization - slope.U1) * slope.R2) / (slope.U2 - slope.U1);
      return slope.R0 + slope.R1 + extra;
    } else if (utilization <= 10000) {
      uint extra = ((utilization - slope.U2) * slope.R3) / (10000 - slope.U2);
      return slope.R0 + slope.R1 + slope.R2 + extra;
    } else {
      return slope.R0 + slope.R1 + slope.R2 + slope.R3;
    }
  }
}
