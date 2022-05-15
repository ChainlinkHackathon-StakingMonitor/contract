// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract DAIToken is ERC20 {
    constructor() public ERC20("Mock DAI", "DAI") {
        _mint(msg.sender, 1000000000000000000000000);
    }
}
