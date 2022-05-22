// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "../../interfaces/IUniswapV2.sol";

contract MockUniswapV2 is IUniswapV2 {
    function swapExactETHForTokens(
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external payable override returns (uint[] memory amounts) {
        amounts[0] = amountOutMin;
        amounts[1] = 2000000000000000000000000000;
        return amounts;
    }

    function WETH() external pure override returns (address) {
        return 0xc0ffee254729296a45a3885639AC7E10F9d54979;
    }
}
