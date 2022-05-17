// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "../../interfaces/IUniswapV2.sol";

contract MockUniswapV2 is IUniswapV2 {
    function swapExactETHForTokens(
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external payable returns (uint[] memory amounts) {}

    function WETH() external pure returns (address) {}
}
