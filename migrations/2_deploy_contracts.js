const Carpool = artifacts.require("Carpool");
const CarpoolToken = artifacts.require("CarpoolToken");

module.exports = function(deployer) {
  deployer.deploy(Carpool);
  deployer.deploy(CarpoolToken);
};