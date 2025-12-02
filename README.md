# 🚗 Carpool DApp - Decentralized Ride-Sharing Platform

A complete decentralized carpooling application built on Ethereum blockchain with Django backend.

## ✨ Features

### For Passengers
- 🔍 Find nearby rides using location-based search
- 💳 Pay securely with CPT tokens via MetaMask
- ⭐ Rate drivers with on-chain reputation system
- 📱 Real-time ride status updates

### For Drivers
- 🚗 Create and manage ride offers
- 💰 Earn CPT tokens for completed rides
- 📊 Dashboard with earnings analytics
- ⏰ Schedule future rides

### Platform Features
- 🔒 Non-custodial wallet authentication
- 📜 Transparent blockchain transaction history
- 💸 No intermediary fees
- 🌍 Global, permissionless access

## 🏗️ Architecture

### Tech Stack
- **Blockchain**: Solidity, Truffle, Ganache, Web3.js
- **Backend**: Django, Python, Web3.py
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Wallet**: MetaMask Integration

### Smart Contracts
1. **Carpool.sol** - Main application logic (rides, users, payments)
2. **CarpoolToken.sol** - ERC-20 token for payments (CPT)

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- MetaMask browser extension
- Ganache (for local development)

### Installation

1. **Clone the Repository**

git clone https://github.com/yourusername/carpool-dapp.git
cd carpool-dapp
Backend Setup


cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
Blockchain Setup



npm install
# In a separate terminal:
npx ganache-cli -d -p 9545
# In another terminal:
npx truffle compile
npx truffle migrate
MetaMask Configuration

Add Ganache network (localhost:9545, Chain ID: 5777)

Import test accounts from Ganache

Add CPT token using contract address

Usage
Start Ganache local blockchain

Run Django development server

Deploy smart contracts

Open http://localhost:8000 in browser

Connect MetaMask and start using Safar
