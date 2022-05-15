//SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;
pragma abicoder v2;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "@chainlink/contracts/src/v0.8/interfaces/KeeperCompatibleInterface.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../interfaces/UniswapV2RouterInterface.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";


error StakeMonitor__UpkeepNotNeeded();
error StakeMonitor__TransferFailed();
error StakingMonitor__UpperBond_SmallerThan_LowerBound();
error StakeMonitor__UserHasntDepositedETH();



contract StakingMonitor is KeeperCompatibleInterface, ReEntrancyGuard {

    struct userInfo {
    uint256 depositBalance;
    uint256 DAIBalance;
    uint256 priceLimit;
    uint256 balanceToSpend;
    uint256 latestBalance; 
    }

    mapping(address => userInfo) public userInfos; // 
    event Deposited(address indexed user);
    AggregatorV3Interface public priceFeed;

    uint256 public s_lowestPriceLimit;
    uint256 public lastTimeStamp;
    address[] public s_watchList;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    function getPrice() public view returns (uint256) {
        (, int256 answer, , , ) = priceFeed.latestRoundData();
        return uint256(answer);
    }

  
    /**************************************************************************
     * Accountability of Staking Monitor Logic 
    *************************************************************************/

    function deposit() external payable {
        // when user deposits the first time, we set last balance to their current balance...
        // not sure that's the best logic but let's see
        if (userInfos[msg.sender].depositBalance == 0) {
            userInfos[msg.sender].latestBalance = msg.sender.balance;
        }

        //TODO: somehow check if address is already watched
        s_watchList.push(msg.sender);
        userInfos[msg.sender].depositBalance =
            userInfos[msg.sender].depositBalance +
            msg.value;
        emit Deposited(msg.sender);
    }

    function withdraw() public {
        userInfos[msg.sender].depositBalance = userInfos[msg.sender].depositBalance + msg.value;
        (bool success, ) = msg.sender.call.value()
        
        emit Deposited(msg.sender);
    }

    function getBalance() external view returns (uint256) {
        return userInfos[msg.sender].depositBalance;
    }

    function setPriceLimit(uint256 _priceLimit) external {
        // a user cannot set a price limit if they haven't deposited some eth
        if (userInfos[msg.sender].depositBalance == 0) {
            revert StakeMonitor__UserHasntDepositedETH();
        }

        userInfos[msg.sender].priceLimit = _priceLimit;

        // set lowest price limit across all users, to trigger upkeep if the lowest price limit is reached
        if ((s_lowestPriceLimit == 0) || (s_lowestPriceLimit > _priceLimit)) {
            s_lowestPriceLimit = _priceLimit;
        }
    }

    function setBalancesToSpend() external {
        for (uint256 idx = 0; idx < s_watchList.length; idx++) {
            // for each address in the watchlist, we check if the balance has increased.
            // if so, we are allowed to spend the difference between the new balance and the old one
            userInfos[s_watchList[idx]].balanceToSpend = (s_watchList[idx]
                .balance - userInfos[s_watchList[idx]].latestBalance);
        }
    }

    function checkLowestLimitUnderCurrentPrice() public view returns (bool) {
        uint price = getPrice();
        bool upkeepNeeded = (s_lowestPriceLimit < price);
        return upkeepNeeded;
    }

    function checkUpkeep(bytes calldata checkData)
        external
        override
        returns (bool upkeepNeeded, bytes memory performData)
    {
        upkeepNeeded = checkLowestLimitUnderCurrentPrice();

        // We don't use the checkData in this example
        // checkData was defined when the Upkeep was registered
        performData = checkData;
    }

    function performUpkeep(bytes calldata performData) external override {
        // iterate over users price limits
        // trigger the sale if current ether price is above price limit for user

        // We don't use the performData in this example
        // performData is generated by the Keeper's call to your `checkUpkeep` function
        performData;
    }
}
