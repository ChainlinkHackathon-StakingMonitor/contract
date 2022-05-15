//SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;
pragma abicoder v2;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "@chainlink/contracts/src/v0.8/interfaces/KeeperCompatibleInterface.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../interfaces/UniswapV2RouterInterface.sol";

error StakeMonitor__UpkeepNotNeeded();
error StakeMonitor__TransferFailed();
error StakingMonitor__UpperBond_SmallerThan_LowerBound();
error StakeMonitor__UserHasntDepositedETH();

struct userInfo {
    uint256 depositBalance;
    uint256 DAIBalance;
    uint256 priceLimit;
    uint256 percentageToSwap;
    uint256 balanceToSwap;
    uint256 latestBalance;
}

contract StakingMonitor is KeeperCompatibleInterface {
    mapping(address => userInfo) public s_userInfos;
    event Deposited(address indexed user);
    AggregatorV3Interface public priceFeed;

    uint256 public s_lowestPriceLimit;
    uint256 public lastTimeStamp;
    uint256 public immutable interval;
    address[] public s_watchList;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        interval = 3 hours;
        lastTimeStamp = block.timestamp;
    }

    function getPrice() public view returns (uint256) {
        (, int256 answer, , , ) = priceFeed.latestRoundData();
        return uint256(answer);
    }

    function deposit() external payable {
        // when user deposits the first time, we set last balance to their current balance...
        // not sure that's the best logic but let's see
        if (s_userInfos[msg.sender].depositBalance == 0) {
            s_userInfos[msg.sender].latestBalance = msg.sender.balance;
        }

        //TODO: somehow check if address is already watched
        s_watchList.push(msg.sender);
        s_userInfos[msg.sender].depositBalance =
            s_userInfos[msg.sender].depositBalance +
            msg.value;
        emit Deposited(msg.sender);
    }

    function withdrawETH(uint256 _amount) external {
        s_userInfos[msg.sender].depositBalance =
            s_userInfos[msg.sender].depositBalance -
            _amount;
        emit Deposited(msg.sender);
    }

    function getDepositBalance() external view returns (uint256) {
        return s_userInfos[msg.sender].depositBalance;
    }

    function setOrder(uint256 _priceLimit, uint256 _percentageToSwap) external {
        // a user cannot set a price limit if they haven't deposited some eth
        if (s_userInfos[msg.sender].depositBalance == 0) {
            revert StakeMonitor__UserHasntDepositedETH();
        }
        s_userInfos[msg.sender].percentageToSwap = _percentageToSwap;
        s_userInfos[msg.sender].priceLimit = _priceLimit;
    }

    function setBalancesToSwap() public {
        for (uint256 idx = 0; idx < s_watchList.length; idx++) {
            // for each address in the watchlist, we check if the balance has increased.
            // if so, we are allowed to spend the difference between the new balance and the old one
            s_userInfos[s_watchList[idx]].balanceToSwap = (s_watchList[idx]
                .balance - s_userInfos[s_watchList[idx]].latestBalance);
        }
    }

    function checkConditionsAndPerformSwap() public {
        uint256 currentPrice = getPrice();
        for (uint256 idx = 0; idx < s_watchList.length; idx++) {
            // check the order conditions for each user in watchlist and trigger a swap if conditions are satisfied
            if (
                s_userInfos[s_watchList[idx]].balanceToSwap > 0 &&
                s_userInfos[s_watchList[idx]].priceLimit > currentPrice
            ) {
                //SWAP s_userInfos[s_watchList[idx]].balanceToSwap * (s_userInfos[s_watchList[idx]].percentageToSwap / 100) amount to DAI
                // update s_userInfos[s_watchList[idx]].DAIBalance
            }
        }
    }

    function checkUpkeep(bytes calldata checkData)
        external
        override
        returns (bool upkeepNeeded, bytes memory performData)
    {
        upkeepNeeded = (block.timestamp - lastTimeStamp) > interval;
        //upkeepNeeded = checkLowestLimitUnderCurrentPrice();

        // We don't use the checkData in this example
        // checkData was defined when the Upkeep was registered
        performData = checkData;
    }

    function performUpkeep(bytes calldata performData) external override {
        lastTimeStamp = block.timestamp;
        setBalancesToSwap();
        checkConditionsAndPerformSwap();
        performData;
    }
}
