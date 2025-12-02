// static/js/dapp.js
// Requires ethers.js included in templates via CDN
async function connectMetaMask() {
  if (!window.ethereum) {
    alert('MetaMask not detected. Install MetaMask and try again.');
    return null;
  }
  await ethereum.request({ method: 'eth_requestAccounts' });
  const provider = new ethers.providers.Web3Provider(window.ethereum);
  const signer = provider.getSigner();
  const address = await signer.getAddress();
  return { provider, signer, address };
}

// fetch token info from backend
async function getTokenInfo() {
  const res = await fetch('/provide_token_info/');
  return await res.json();
}

// fetch carpool contract info
async function getCarpoolInfo() {
  const res = await fetch('/api/contract_info/');
  return await res.json();
}

// pay driver with token and then call backend verify endpoint
async function payDriverAndBook(rideId, driverAddress, amountHuman) {
  const connect = await connectMetaMask();
  if (!connect) return;
  const { provider, signer, address: passengerAddress } = connect;

  const tokenInfo = await getTokenInfo();
  if (tokenInfo.error) { alert('Token info error: ' + tokenInfo.error); return; }

  const tokenAbi = tokenInfo.abi;
  const tokenAddress = tokenInfo.address;
  const decimals = tokenInfo.decimals || 18;

  const tokenContract = new ethers.Contract(tokenAddress, tokenAbi, signer);
  // compute amount in base units
  const amountUnits = ethers.BigNumber.from(10).pow(decimals).mul(ethers.BigNumber.from(Math.floor(amountHuman)));

  // perform transfer to driver
  try {
    const tx = await tokenContract.transfer(driverAddress, amountUnits);
    const receipt = await tx.wait();
    console.log('Transfer receipt', receipt);

    // notify backend to verify (supply expected_amount as integer string)
    const payload = {
      tx_hash: receipt.transactionHash,
      expected_to: driverAddress,
      expected_amount: amountUnits.toString(),
      passenger: passengerAddress,
      rid: rideId
    };
    const verifyRes = await fetch('/verify_token_payment/', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });

    const verifyJson = await verifyRes.json();
    if (verifyJson.status === 'ok') {
      alert('Payment verified. Please call bookRide on the contract now (optional).');
      // Optionally call bookRide on Carpool contract from passenger's wallet to register booking
      const carpoolInfo = await getCarpoolInfo();
      if (!carpoolInfo.error) {
        const carpoolContract = new ethers.Contract(carpoolInfo.address, carpoolInfo.abi, signer);
        const tx2 = await carpoolContract.bookRide(rideId, passengerAddress);
        await tx2.wait();
        alert('Booking transaction mined. You are booked!');
        location.reload();
      } else {
        alert('Carpool info not available to auto-book. Reload list.');
      }
    } else {
      alert('Verification failed: ' + (verifyJson.error || JSON.stringify(verifyJson)));
    }
  } catch (err) {
    console.error(err);
    alert('Payment or booking failed: ' + err.message);
  }
}
