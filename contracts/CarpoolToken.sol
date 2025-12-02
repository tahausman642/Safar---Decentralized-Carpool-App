// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract CarpoolToken is ERC20, Ownable {
    
    constructor() ERC20("CarpoolToken", "CPT") {
        // Mint 1,000,000 tokens to contract deployer
        _mint(msg.sender, 1000000 * 10**decimals());
    }
    
    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }
    
    function burn(uint256 amount) public {
        _burn(_msgSender(), amount);
    }
    
    // Transfer function is inherited from ERC20
    // function transfer(address recipient, uint256 amount) public override returns (bool)
}