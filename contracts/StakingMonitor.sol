//SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;
pragma abicoder v2;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "@chainlink/contracts/src/v0.8/interfaces/KeeperCompatibleInterface.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../interfaces/IUniswapV2.sol";
import "./ABDKMath64x64.sol";

error StakeMonitor__UpkeepNotNeeded();
error StakeMonitor__TransferFailed();
error StakeMonitor__UserHasntDepositedETH();
error StakeMonitor_NotEnoughDAIInBalance();

struct userData {
    bool created;
    uint256 depositBalance;
    uint256 DAIBalance;
    uint256 priceLimit;
    uint256 percentageToSwap;
    uint256 balanceToSwap;
    uint256 latestBalance;
}

contract StakingMonitor is KeeperCompatibleInterface {
    event Deposited(address indexed user);
    // we only stored the following in the event, the rest is calculated in the front end
    event Swapped(
        address indexed _address,
        uint256 _timestamp,
        uint256 _totalReward,
        uint256 _setPriceLimit,
        uint256 _percentageSwapped,
        uint256 _DAIReceived,
        uint256 _ETHPrice
    );

    event NotEnoughDepositedEthForSwap(
        address indexed _address,
        uint256 _requiredDepositAmount
    );

    AggregatorV3Interface public priceFeed;
    IERC20 public DAIToken;
    IUniswapV2 public uniswap;

    uint256 public lastTimeStamp;
    uint256 public immutable interval;

    mapping(address => userData) public s_users;
    address[] public s_watchList;

    // these storage variables are used to store values needed to perform
    // and distribute the results of the swap.
    address[] public addressesForSwap;
    uint256 public totalAmountToSwap;
    uint256 public totalDAIFromSwap;

    constructor(
        address _priceFeed,
        address _DAIToken,
        address _uniswap,
        uint256 _interval
    ) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        DAIToken = IERC20(_DAIToken);
        interval = _interval;
        lastTimeStamp = block.timestamp;
        uniswap = IUniswapV2(_uniswap);
    }

    function getPrice() public view returns (uint256) {
        (, int256 answer, , , ) = priceFeed.latestRoundData();
        return uint256(answer);
    }

    function deposit() external payable {
        // when user deposits the first time, we set last balance to their current balance...
        // not sure that's the best logic but let's see
        if (s_users[msg.sender].depositBalance == 0) {
            s_users[msg.sender].latestBalance = msg.sender.balance;
        }

        //TODO: somehow check if address is already watched
        if (!s_users[msg.sender].created) {
            s_watchList.push(msg.sender);
        }
        s_users[msg.sender].created = true;
        s_users[msg.sender].depositBalance =
            s_users[msg.sender].depositBalance +
            msg.value;
        emit Deposited(msg.sender);
    }

    function withdrawETH(uint256 _amount) external {
        s_users[msg.sender].depositBalance =
            s_users[msg.sender].depositBalance -
            _amount;
    }

    function withdrawDAI(uint256 _amount) external {
        if (_amount <= s_users[msg.sender].DAIBalance) {
            s_users[msg.sender].DAIBalance -= _amount;
            DAIToken.transfer(msg.sender, _amount);
        } else {
            revert StakeMonitor_NotEnoughDAIInBalance();
        }
    }

    function getDepositBalance() external view returns (uint256) {
        return s_users[msg.sender].depositBalance;
    }

    function getDAIBalance() external view returns (uint256) {
        return s_users[msg.sender].DAIBalance;
    }

    function setOrder(uint256 _priceLimit, uint256 _percentageToSwap) external {
        // a user cannot set a price limit if they haven't deposited some eth
        if (s_users[msg.sender].depositBalance == 0) {
            revert StakeMonitor__UserHasntDepositedETH();
        }
        s_users[msg.sender].percentageToSwap = _percentageToSwap;
        // priceLimit needs to have same units as what is returned by getPrice
        s_users[msg.sender].priceLimit = _priceLimit * 100000000;
    }

    function swapEthForDAI(uint256 amount) public returns (uint256) {
        address[] memory path = new address[](2);
        path[0] = uniswap.WETH();
        path[1] = address(DAIToken);
        uint[] memory tokenAmount_;

        // make the swap
        tokenAmount_ = uniswap.swapExactETHForTokens{value: amount}(
            0,
            path,
            address(this), // The contract
            block.timestamp
        );
        uint256 outputTokenCount = uint256(
            tokenAmount_[tokenAmount_.length - 1]
        );
        return outputTokenCount;
    }

    function setBalancesToSwap() public {
        for (uint256 idx = 0; idx < s_watchList.length; idx++) {
            // for each address in the watchlist, on each keeper tick, we check if the balance of their actual address has increased.
            // if so, we are allowed to spend their percentage (set in the order) of the difference between the new balance and the old one.
            // this is a placeholder until we get the real staking reward distribution event.
            if (
                s_watchList[idx].balance >
                s_users[s_watchList[idx]].latestBalance
            ) {
                s_users[s_watchList[idx]].balanceToSwap +=
                    ((s_watchList[idx].balance -
                        s_users[s_watchList[idx]].latestBalance) *
                        s_users[s_watchList[idx]].percentageToSwap) /
                    100;
                // if their balanceToSwap is larger than their depositBalance, we need to emit
                // an event that warns them and tells them they have to deposit more eth into
                // the contract
                if (
                    s_users[s_watchList[idx]].balanceToSwap >
                    s_users[s_watchList[idx]].depositBalance
                ) {
                    emit NotEnoughDepositedEthForSwap(
                        s_watchList[idx],
                        s_users[s_watchList[idx]].balanceToSwap -
                            s_users[s_watchList[idx]].depositBalance
                    );
                }
            }
            // we set latestBalance to the current balance
            s_users[s_watchList[idx]].latestBalance = s_watchList[idx].balance;
        }
    }

    function checkConditionsAndPerformSwap() public {
        uint256 currentPrice = getPrice();

        // on each tick, we start from an empty list
        // of addresses that will be part of this swap,
        // and we reinitialise the totalAmountToSwap.
        delete addressesForSwap;
        totalAmountToSwap = 0;

        // we build a list of the addresses that will be part of the swap
        // (the ones where conditions for swap are satisfied). We store that list in the array below.
        for (uint256 idx = 0; idx < s_watchList.length; idx++) {
            // check the order conditions for each user in watchlist and trigger a swap if conditions are satisfied
            if (
                s_users[s_watchList[idx]].balanceToSwap > 0 &&
                currentPrice > s_users[s_watchList[idx]].priceLimit
            ) {
                //we count that user in for this swap
                addressesForSwap.push(payable(s_watchList[idx]));
                totalAmountToSwap += s_users[s_watchList[idx]].balanceToSwap;
            }
        }
        // we perform the swap
        if (totalAmountToSwap > 0) {
            totalDAIFromSwap = swapEthForDAI(totalAmountToSwap);
            //totalDAIFromSwap = 500000000000000;
        }
        // we distribute the DAI balances among participants
        for (uint256 idx = 0; idx < addressesForSwap.length; idx++) {
            // the new DAIBalance of each swap participant
            // increases by their share of the totalAmountToSwap
            s_users[addressesForSwap[idx]].DAIBalance +=
                (totalDAIFromSwap *
                    s_users[addressesForSwap[idx]].balanceToSwap) /
                totalAmountToSwap;
            emit Swapped(
                addressesForSwap[idx],
                block.timestamp,
                s_users[addressesForSwap[idx]].balanceToSwap,
                s_users[addressesForSwap[idx]].priceLimit,
                s_users[addressesForSwap[idx]].percentageToSwap,
                s_users[addressesForSwap[idx]].DAIBalance,
                currentPrice
            );
            // we substract the balanceToSwap from the user's
            // depositBalance
            s_users[addressesForSwap[idx]].depositBalance -= s_users[
                addressesForSwap[idx]
            ].balanceToSwap;

            // we reinitialise the balanceToSwap for the user
            s_users[addressesForSwap[idx]].balanceToSwap = 0;
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
