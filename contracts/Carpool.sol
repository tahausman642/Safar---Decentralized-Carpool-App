// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Carpool {
    address public owner;
    string public users;
    string public rides;
    string public passengers;
    string public ratings;
    
    constructor() {
        owner = msg.sender;
        users = "";
        rides = "";
        passengers = "";
        ratings = "";
    }
    
    function addUser(string memory _userData) public {
        users = string(abi.encodePacked(users, _userData));
    }
    
    function getUser() public view returns (string memory) {
        return users;
    }
    
    // ADD THIS FUNCTION - was missing
    function setUser(string memory _userData) public {
        users = _userData;
    }
    
    function setRide(string memory _rideData) public {
        rides = _rideData;
    }
    
    function getRide() public view returns (string memory) {
        return rides;
    }
    
    function setPassengers(string memory _passengerData) public {
        passengers = _passengerData;
    }
    
    function getPassengers() public view returns (string memory) {
        return passengers;
    }
    
    function setRatings(string memory _ratingData) public {
        ratings = _ratingData;  // CHANGED: Replace instead of append
    }
    
    function getRatings() public view returns (string memory) {
        return ratings;
    }
    
    // Helper function to clear data (for testing)
    function clearAllData() public {
        require(msg.sender == owner, "Only owner can clear data");
        users = "";
        rides = "";
        passengers = "";
        ratings = "";
    }
}