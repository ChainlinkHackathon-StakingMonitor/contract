//SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;
pragma abicoder v2;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "@chainlink/contracts/src/v0.8/interfaces/KeeperCompatibleInterface.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../interfaces/IUniswapV2.sol";
import "./ABDKMath64x64.sol";

error StakingMonitor__UpkeepNotNeeded();
error StakingMonitor__TransferFailed();
error StakingMonitor__UserHasntDepositedETH();
error StakingMonitor__NotEnoughETHInUsersBalance();
error StakingMonitor_NotEnoughDAIInUsersBalance();
error StakingMonitor_UserDoesntHaveAccount();

struct userData {
    bool created;
    bool enoughDepositForSwap;
    uint256 depositBalance;
    uint256 DAIBalance;
    uint256 priceLimit;
    uint256 percentageToSwap;
    uint256 balanceToSwap;
    uint256 previousBalance;
}

/**
 * @title Staking Monitor
 * @author Pascal Belouin
 * @notice This contract watches addresses stored in s_watchlist using Chainlink Keepers and, using Uniswap V2, swaps a deposited, "mirrored" version of the
 * balance change for DAI (stored in s_users), which it interprets as a staking reward. After each swap, it distributes the DAI among the users' DAI Balances
 * within the contract. The users can then withdraw their DAI balance at any point if they wish. Please note that the balances changes are used in lieu of
 * listening to actual staking reward events being emitted, which we plan to implement in the future when Chainlink and Chainlink Keeper is available on Moonbeam.
 */
contract StakingMonitor is KeeperCompatibleInterface {
    using ABDKMath64x64 for int128;

    event Deposited(address indexed user, uint256 _amount);
    event OrderSet(address indexed user);
    event WithdrawnETH(address indexed user, uint256 _amount);
    event WithdrawnDAI(address indexed user, uint256 _amount);
    event Swapped(
        address indexed _address,
        uint256 _timestamp,
        uint256 _totalReward,
        uint256 _setPriceLimit,
        uint256 _DAIReceived,
        uint256 _ETHPrice
    );
    event NotEnoughDepositedEthForSwap(
        address indexed _address,
        uint256 _requiredDepositAmount
    );

    AggregatorV3Interface public priceFeed;
    IERC20 public immutable DAIToken;
    IUniswapV2 public immutable uniswap;

    uint256 public lastTimeStamp;
    uint256 public immutable interval;

    mapping(address => userData) public s_users;
    address[] public s_watchList;

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

    /**
     * @notice Gets the price of network currency in USD
     * @dev the price is returned with 8 decimal values
     */
    function getPrice() public view returns (uint256) {
        (, int256 answer, , , ) = priceFeed.latestRoundData();
        return uint256(answer);
    }

    /**
     * @notice Allows users to deposit some network currency.
     * @dev  It creates data for user in the s_users map of structs if it doesn't exist yet, and adds the user's address to the watchlist.
     * Finally, it adds the amount deposited to the contract's user's balance.
     */
    function deposit() external payable {
        // we check if we already have user data for this user
        if (!s_users[msg.sender].created) {
            s_watchList.push(msg.sender);
        }
        s_users[msg.sender].created = true;
        s_users[msg.sender].depositBalance =
            s_users[msg.sender].depositBalance +
            msg.value;
        // we update previousBalance for the user.
        s_users[msg.sender].previousBalance = msg.sender.balance;
        s_users[msg.sender].enoughDepositForSwap = true;
        emit Deposited(msg.sender, msg.value);
    }

    /**
     * @notice Allows users to withdraw an amount of their main network currency balance.
     * @dev  _amount is removed from their internal contract balance.
     */
    function withdrawETH(uint256 _amount) external {
        if (!s_users[msg.sender].created) {
            revert StakingMonitor_UserDoesntHaveAccount();
        }

        if (_amount > s_users[msg.sender].depositBalance) {
            revert StakingMonitor__NotEnoughETHInUsersBalance();
        }
        s_users[msg.sender].depositBalance =
            s_users[msg.sender].depositBalance -
            _amount;
        payable(msg.sender).transfer(_amount);
        // we update previousBalance for the user.
        s_users[msg.sender].previousBalance = msg.sender.balance;
        emit WithdrawnETH(msg.sender, _amount);
    }

    /**
     * @notice Allows users to withdraw an amount of their DAI balance.
     * @dev  _amount is removed from their internal contract balance.
     */
    function withdrawDAI(uint256 _amount) external {
        if (!s_users[msg.sender].created) {
            revert StakingMonitor_UserDoesntHaveAccount();
        }

        if (_amount > s_users[msg.sender].DAIBalance) {
            revert StakingMonitor_NotEnoughDAIInUsersBalance();
        }

        s_users[msg.sender].DAIBalance -= _amount;
        DAIToken.transfer(msg.sender, _amount);
        emit WithdrawnDAI(msg.sender, _amount);
    }

    /**
     * @notice Gets the calling user's main network currency balance
     */
    function getDepositBalance() external view returns (uint256) {
        return s_users[msg.sender].depositBalance;
    }

    /**
     * @notice Gets the calling user's DAI balance
     */
    function getDAIBalance() external view returns (uint256) {
        return s_users[msg.sender].DAIBalance;
    }

    /// @notice Gets the calling user's data
    function getUserData() external view returns (userData memory) {
        return s_users[msg.sender];
    }

    /**
     * @notice Allows users to set the minimum price at which a swap of a portion of their deposit main network currency should take place.
     * They can also set the percentage of their staking rewards that should be swapped for DAI on their behalf.
     * @dev We add 8 decimals to the priceLimit they enter, to match the decimals returned by getPrice.
     */
    function setOrder(uint256 _priceLimit, uint256 _percentageToSwap) external {
        // a user cannot set a price limit if they haven't deposited some eth
        if (s_users[msg.sender].depositBalance == 0) {
            revert StakingMonitor__UserHasntDepositedETH();
        }
        s_users[msg.sender].percentageToSwap = _percentageToSwap;
        // priceLimit needs to have same units as what is returned by getPrice
        s_users[msg.sender].priceLimit = _priceLimit * 100000000;
        emit OrderSet(msg.sender);
    }

    /**
     * @notice Utility pure function that calculates the balance we should swap for a user
     * @dev makes use of the ABDKMath64x64 library
     */
    function calculateUserBalanceToSwap(
        uint256 currentBalance,
        uint256 previousBalance,
        uint256 orderPercentageToSwap
    ) public pure returns (uint256) {
        return (
            ABDKMath64x64.toUInt(
                ABDKMath64x64.divu(
                    (currentBalance - previousBalance) * orderPercentageToSwap,
                    100
                )
            )
        );
    }

    /**
     * @notice Utility pure function that calculates the share of a swap a user should receive
     * @dev makes use of the ABDKMath64x64 library
     */
    function calculateUserSwapShare(
        uint256 totalToken,
        uint256 userBalanceToSwap,
        uint256 totalAmount
    ) public pure returns (uint256) {
        //return (
        //    ABDKMath64x64.toUInt(
        //        ABDKMath64x64.divu(totalToken * userBalanceToSwap, totalAmount)
        //    )
        //);
        return ((totalToken * userBalanceToSwap) / totalAmount);
    }

    /**
     * @notice The first function called by the upkeep, which compares the current balance of each user's address with the previous one,
     * which we either got when they deposited or withdrew main network currency from the contract, or at the last upkeep. It interprets
     * this difference as the user having received a staking reward on their address. We then calculate the portion of this reward that should be
     * swapped for DAI, by dividing it by the percentageToSwap value they have set in their order.
     * @dev For each address in the watchlist, on each upkeep, we check if the balance of their actual address has increased.
     * if so, we add the percentage (set in the order) of the difference between the new balance and the old one to their
     * balanceToSwap, which will be swapped the next time the price of the main network currency is above the price limit
     * set in their order. This is a workaround until we get the actual staking reward distribution event.
     */
    function setBalancesToSwap() public {
        for (uint256 idx = 0; idx < s_watchList.length; idx++) {
            if (
                s_watchList[idx].balance >
                s_users[s_watchList[idx]].previousBalance
            ) {
                s_users[s_watchList[idx]]
                    .balanceToSwap += calculateUserBalanceToSwap(
                    s_watchList[idx].balance,
                    s_users[s_watchList[idx]].previousBalance,
                    s_users[s_watchList[idx]].percentageToSwap
                );
                // if a user's balanceToSwap is larger than their depositBalance, we need to emit
                // an event that warns them that they have to deposit more eth into
                // the contract for their swap to take place.
                // otherwise, we set the flag "enoughDepositForSwap" to true
            }
            if (
                s_users[s_watchList[idx]].balanceToSwap >
                s_users[s_watchList[idx]].depositBalance
            ) {
                s_users[s_watchList[idx]].enoughDepositForSwap = false;
                emit NotEnoughDepositedEthForSwap(
                    s_watchList[idx],
                    s_users[s_watchList[idx]].balanceToSwap -
                        s_users[s_watchList[idx]].depositBalance
                );
            } else {
                s_users[s_watchList[idx]].enoughDepositForSwap = true;
            }

            // we set previousBalance to the current balance
            s_users[s_watchList[idx]].previousBalance = s_watchList[idx]
                .balance;
        }
    }

    /**
     * @notice Swaps ETH for DAI using Uniswap V2, and returns the amount of DAI that resulted from the swap.
     */
    function swapEthForDAI(uint256 amount) public returns (uint256) {
        address[] memory path = new address[](2);
        path[0] = uniswap.WETH();
        path[1] = address(DAIToken);
        uint[] memory tokenAmount_;

        // make the swap
        tokenAmount_ = uniswap.swapExactETHForTokens{value: amount}(
            0,
            path,
            address(this),
            block.timestamp
        );
        uint256 outputTokenCount = uint256(
            tokenAmount_[tokenAmount_.length - 1]
        );
        return outputTokenCount;
    }

    /**
     * @notice The second function called by the upkeep, which checks which users have required balances,
     * as well as an order where the conditions for a swap are met.
     *
     * @dev emits a "Swapped" event for each user, which is used in the dapp frontend to display the history for each user
     */
    function checkConditionsAndPerformSwap() public {
        uint256 currentPrice = getPrice();

        address[] memory addressesForSwap = new address[](s_watchList.length);
        uint256[] memory totalAmountToSwap_TotalDAIFromSwap = new uint256[](2);
        uint256[] memory totalDAIFromSwap = new uint256[](1);

        // we build a list of the addresses that will be part of the swap
        // (the ones where conditions for swap are satisfied). We store that list in the array below.
        for (uint256 idx = 0; idx < s_watchList.length; idx++) {
            // check the order conditions for each user in watchlist and trigger a swap if conditions are satisfied
            if (
                s_users[s_watchList[idx]].enoughDepositForSwap &&
                s_users[s_watchList[idx]].balanceToSwap > 0 &&
                currentPrice > s_users[s_watchList[idx]].priceLimit
            ) {
                //we count that user in for this swap
                addressesForSwap[idx] = (payable(s_watchList[idx]));
                totalAmountToSwap_TotalDAIFromSwap[0] += s_users[
                    s_watchList[idx]
                ].balanceToSwap;
            } else {
                // if the address can't swap, we set it to the null address in addressesForSwap
                addressesForSwap[
                    idx
                ] = 0x000000000000000000000000000000000000dEaD;
            }
        }

        uint[] memory receivedDAIFromSwapPerUser = new uint[](
            addressesForSwap.length
        );

        if (totalAmountToSwap_TotalDAIFromSwap[0] > 0) {
            // we perform the swap
            totalAmountToSwap_TotalDAIFromSwap[1] = swapEthForDAI(
                totalAmountToSwap_TotalDAIFromSwap[0]
            );
            // we distribute the DAI balances among participants
            for (uint256 idx = 0; idx < addressesForSwap.length; idx++) {
                if (
                    addressesForSwap[idx] !=
                    0x000000000000000000000000000000000000dEaD
                ) {
                    // the new DAIBalance of each swap participant
                    // increases by their share of the totalAmountToSwap
                    receivedDAIFromSwapPerUser[idx] = calculateUserSwapShare(
                        totalAmountToSwap_TotalDAIFromSwap[1],
                        s_users[addressesForSwap[idx]].balanceToSwap,
                        totalAmountToSwap_TotalDAIFromSwap[0]
                    );
                    s_users[addressesForSwap[idx]]
                        .DAIBalance += receivedDAIFromSwapPerUser[idx];
                    emit Swapped(
                        addressesForSwap[idx],
                        block.timestamp,
                        s_users[addressesForSwap[idx]].balanceToSwap,
                        s_users[addressesForSwap[idx]].priceLimit,
                        receivedDAIFromSwapPerUser[idx],
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
        }
    }

    /**
     * @notice This function is used by the upkeep network to check if performUpkeep should be executed.
     * Pretty simple at the moment, it just triggers at regular intervals. Once we can listen to the staking reward distribution events, we will
     * be able to implement a more efficient and gas-effective condition that will only trigger when reward distribution events take place for the addresses
     * in s_watchlist
     */
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

    /**
     * @notice On each upkeep, we check if each user in the watchlist has received a staking reward, set the balances that should be swapped,
     * and perform the swap.
     */
    function performUpkeep(bytes calldata performData) external override {
        lastTimeStamp = block.timestamp;
        setBalancesToSwap();
        checkConditionsAndPerformSwap();
        performData;
    }
}
