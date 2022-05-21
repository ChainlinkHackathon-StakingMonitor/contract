// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "hardhat/console.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";


contract APILiquidWork is ChainlinkClient, ERC721URIStorage {
    using Chainlink for Chainlink.Request;

    uint256 public realTime; 

    address private oracle;
    bytes32 private jobId;
    uint256 private fee;

    // When TimeLeft == 0 emit this Event
    event ExperienceFinished(bytes32 firstName, bytes32 lastName, uint256 TimeLeft);

    /**
     * Network: Kovan
     * Oracle: 0xc57B33452b4F7BB189bB5AfaE9cc4aBa1f7a4FD8 (Chainlink Devrel   
     * Node)
     * Job ID: d5270d1c311941d0b08bead21fea7747
     * Fee: 0.1 LINK
     */
    constructor() ERC721("Experience", "EXP") {
        setPublicChainlinkToken();
        oracle = 0xc57B33452b4F7BB189bB5AfaE9cc4aBa1f7a4FD8;
        jobId = "d5270d1c311941d0b08bead21fea7747";
        fee = 0.1 * 10 ** 18; // (Varies by network and job)
    }
    
    /**
     * Create a Chainlink request to retrieve API response, find the target
     * data, then multiply by 1000000000000000000 (to remove decimal places from data).
     */


    function requesting() public 
    {
        Chainlink.Request memory request = buildChainlinkRequest(jobId, address(this), this.fulfill.selector);
        
        // Set the URL to perform the GET request on
        request.add("get", "http://worldtimeapi.org/api/timezone/America/New_York");
        
        // Set the path to find the desired data in the API response, where the response format is:
    
        request.add("path", "unixtime"); // add a nested path 
        
        // Multiply the result by 1000000000000000000 to remove decimals
        int timesAmount = 10**18;
        request.addInt("times", timesAmount);
        
        // Sends the request
        sendChainlinkRequestTo(oracle, request, fee);
        counter++;
    }


    
     uint256 public newId;
     uint256 public counter;

    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;

    modifier onlyMinted(){
        require(counter == 2 ); 
        _;
    }

    function mintNFT(address recipient, string memory tokenURI) onlyMinted
        public
        returns (uint256)
    {
        _tokenIds.increment();

        uint256 newItemId = _tokenIds.current();
        _mint(recipient, newItemId);
        _setTokenURI(newItemId, tokenURI);

        return newItemId;
    }

    /**
     * Callback function
     */

    function fulfill(bytes32 _requestId, uint256 _realTime) public recordChainlinkFulfillment(_requestId)
    {
        if (counter==1){
            realTime = 0; 
        }else{
            realTime = _realTime;
        }
    
    }

    function getRealTime(uint256 _realTime) public returns(uint256){
        realTime = _realTime ;
    }

    





  
}

