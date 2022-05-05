//SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;
pragma abicoder v2;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

error StakeMonitor__UpkeepNotNeeded();
error StakeMonitor__TransferFailed();
error StakingMonitor__UpperBond_SmallerThan_LowerBound();

struct userInfo {
    uint256 balance;
    uint256 tokenSymbol;
    uint256 priceLimit;
}

contract StakingMonitor {
    mapping(address => userInfo) public s_userInfos;
    address[] s_addresses;
    event Deposited(address indexed user);
    AggregatorV3Interface public priceFeed;

    uint256 public s_lowestPriceLimit;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    function getPrice() public view returns (uint256) {
        (, int256 answer, , , ) = priceFeed.latestRoundData();
        return uint256(answer);
    }

    function deposit() external payable {
        s_userInfos[msg.sender].balance =
            s_userInfos[msg.sender].balance +
            msg.value;
        s_addresses.push(msg.sender);
        emit Deposited(msg.sender);
    }

    function setPriceLimit(uint256 _priceLimit) external {
        _priceLimit = _priceLimit * 100000000;

        s_userInfos[msg.sender].priceLimit = _priceLimit;

        // set lowest price limit
        if ((s_lowestPriceLimit == 0) || (s_lowestPriceLimit > _priceLimit)) {
            s_lowestPriceLimit = _priceLimit;
        }
    }

    function calculatePriceRange() public view returns (bool) {
        uint price = getPrice();
        bool upkeepNeeded = (price > s_lowestPriceLimit);
        return upkeepNeeded;
    }

    function checkUpkeep(
        bytes memory /*checkData */
    )
        public
        view
        returns (
            bool upkeepNeeded,
            bytes memory /* performData */
        )
    {
        // upkeepNeeded: if price between one of the brackets
        //uint price = getPrice();
        upkeepNeeded = calculatePriceRange();
        return (upkeepNeeded, "0x0");
    }

    function performUpkeep(
        bytes calldata /* performData */
    ) external {
        (bool upkeepNeeded, ) = checkUpkeep("");
        if (!upkeepNeeded) {
            revert StakeMonitor__UpkeepNotNeeded();
        }
        // perform upkeep
    }
}
