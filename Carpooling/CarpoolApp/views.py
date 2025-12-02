from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, os, random, hashlib
from datetime import date, datetime, timedelta
from geopy.distance import geodesic
from web3 import Web3, HTTPProvider
import logging

# Setup logging
logger = logging.getLogger(__name__)

# -------------------- Configuration --------------------
GANACHE_URL = 'http://127.0.0.1:9545'
DEFAULT_ACCOUNT_INDEX = 0
CHAIN_NETWORK_ID = '5777'

# -------------------- Wallet Storage --------------------
# In-memory storage for wallet addresses (for demo - in production use database)
user_wallets = {}

# -------------------- Session Keys --------------------
SESSION_USER = 'current_user'
SESSION_USER_TYPE = 'user_type'

# -------------------- Helpers --------------------

def get_web3():
    """Return a Web3 instance connected to Ganache and set default account."""
    web3 = Web3(HTTPProvider(GANACHE_URL))
    if not web3.is_connected():
        raise ConnectionError(f"Unable to connect to blockchain at {GANACHE_URL}")
    try:
        web3.eth.default_account = web3.eth.accounts[DEFAULT_ACCOUNT_INDEX]
    except Exception as e:
        logger.warning(f"Could not set default account: {e}")
        web3.eth.default_account = None
    return web3

def build_contract_path(name):
    """Return absolute path to build/contracts/<name>.json"""
    root_build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../build/contracts'))
    return os.path.join(root_build_dir, f"{name}.json")

def load_contract(contract_type):
    """Load compiled contract JSON and return (contract, web3)."""
    contract_map = {
        'signup': 'Carpool',
        'ride': 'Carpool', 
        'passengers': 'Carpool',
        'ratings': 'Carpool',
        'token': 'CarpoolToken'
    }
    contract_name = contract_map.get(contract_type)
    if not contract_name:
        raise ValueError(f"Unknown contract type: {contract_type}")

    path = build_contract_path(contract_name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Contract JSON not found: {path}")

    with open(path) as f:
        contract_json = json.load(f)

    abi = contract_json.get('abi')
    networks = contract_json.get('networks', {})
    deployed = networks.get(CHAIN_NETWORK_ID) or (next(iter(networks.values())) if networks else None)
    if not deployed:
        raise ValueError(f"Contract {contract_name} has no deployed address in build JSON")
    address = deployed.get('address')

    web3 = get_web3()
    contract = web3.eth.contract(address=web3.to_checksum_address(address), abi=abi)
    return contract, web3

def send_transaction(contract_type, function_name, data):
    """Send a transaction calling `function_name` with a single string argument `data`."""
    contract, web3 = load_contract(contract_type)
    func = getattr(contract.functions, function_name)
    tx_hash = func(data).transact({'from': web3.eth.default_account})
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

def get_current_user(request):
    """Get current user from session"""
    return request.session.get(SESSION_USER)

def get_user_type(request):
    """Get user type from session"""
    return request.session.get(SESSION_USER_TYPE)

def get_user_wallet_address(username):
    """Get user's wallet address from storage"""
    return user_wallets.get(username)

def store_user_wallet(username, wallet_address):
    """Store user's wallet address"""
    user_wallets[username] = wallet_address
    logger.info(f"Stored wallet for {username}: {wallet_address}")

def set_user_session(request, username, user_type):
    """Set user session data"""
    request.session[SESSION_USER] = username
    request.session[SESSION_USER_TYPE] = user_type
    request.session.modified = True

def clear_user_session(request):
    """Clear user session data"""
    for key in [SESSION_USER, SESSION_USER_TYPE]:
        if key in request.session:
            del request.session[key]

def get_token_balance(wallet_address):
    """Get token balance for a wallet address"""
    if not wallet_address:
        return "0"
    try:
        token_contract, web3 = load_contract('token')
        balance = token_contract.functions.balanceOf(wallet_address).call()
        return web3.utils.fromWei(balance, 'ether')
    except Exception as e:
        logger.error(f"Error getting token balance: {e}")
        return "0"

def checkUser(username):
    """Return True if username exists"""
    contract_signup, web3 = load_contract('signup')
    try:
        stored = contract_signup.functions.getUser().call()
    except Exception as e:
        stored = ""
    rows = [r for r in stored.split('\n') if r.strip()]
    for row in rows:
        arr = row.split('#')
        if arr and arr[0] == username:
            return True
    return False

# -------------------- Core Views --------------------

def index(request):
    return render(request, 'index.html', {})

def Login(request):
    return render(request, 'Login.html', {})

def Register(request):
    return render(request, 'Register.html', {})

def logout_view(request):
    """Logout user"""
    clear_user_session(request)
    return redirect('index')

def Signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        contact = request.POST.get('contact')
        email = request.POST.get('email')
        vehicle = request.POST.get('vehicle')
        user_type = request.POST.get('type')
        wallet_address = request.POST.get('wallet_address')

        if not checkUser(username):
            # Store user data with wallet address
            data = f"{username}#{password}#{contact}#{email}#{vehicle}#{user_type}#{wallet_address}\n"
            send_transaction('signup', 'addUser', data)
            
            # Store wallet address in our storage
            store_user_wallet(username, wallet_address)
            
            # Distribute initial tokens to user's MetaMask wallet
            try:
                token_contract, web3 = load_contract('token')
                amount = web3.to_wei(500, 'ether')  # 500 CPT tokens
                tx_hash = token_contract.functions.transfer(
                    web3.to_checksum_address(wallet_address),
                    amount
                ).transact({'from': web3.eth.default_account})
                logger.info(f"Sent 500 CPT to {wallet_address}")
            except Exception as e:
                logger.error(f"Token distribution failed: {e}")
            
            context = {
                'data': f'Signup Completed! Connected to wallet: {wallet_address[:10]}...',
                'wallet_info': f'You received 500 CPT tokens in your MetaMask wallet!'
            }
        else:
            context = {'data': 'Given username already exists'}
        return render(request, 'Register.html', context)
    return redirect('Register')

def UserLogin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        wallet_address = request.POST.get('wallet_address')
        
        print(f"🔐 LOGIN ATTEMPT: Username: {username}, Wallet: {wallet_address}")
        
        contract, web3 = load_contract('signup')
        try:
            stored = contract.functions.getUser().call()
            print(f"📋 Stored users from blockchain: {stored}")
        except Exception as e:
            print(f"❌ Error reading from blockchain: {e}")
            stored = ""

        rows = stored.split('\n')
        status = 'none'
        user_data = None
        
        for row in rows:
            if not row.strip():
                continue
            arr = row.split('#')
            print(f"🔍 Checking user: {arr}")
            if len(arr) > 1 and arr[0] == username and arr[1] == password:
                status = 'success'
                user_data = arr
                print(f"✅ USER FOUND: {arr}")
                break

        if status == 'success' and user_data:
            # Use wallet from form or stored wallet from blockchain
            user_wallet = wallet_address
            if not user_wallet and len(user_data) > 6:
                user_wallet = user_data[6]
            
            print(f"💰 Using wallet: {user_wallet}")
            
            # Store wallet in our storage
            if user_wallet:
                store_user_wallet(username, user_wallet)
            
            user_type = user_data[5] if len(user_data) > 5 else 'Passenger'
            print(f"👤 User type: {user_type}")
            
            set_user_session(request, username, user_type)
            
            if user_type == 'Driver':
                print("🚗 Redirecting to DriverScreen")
                return redirect('DriverScreen')
            else:
                print("👤 Redirecting to UserScreen")
                return redirect('UserScreen')
        else:
            print("❌ LOGIN FAILED: Invalid credentials")
            context = {'data': 'Invalid login details'}
            return render(request, 'Login.html', context)
    return redirect('Login')

def UserScreen(request):
    """Display the user screen for passengers"""
    user = get_current_user(request)
    if not user:
        return redirect('Login')
    
    # Get wallet from our storage
    wallet_address = get_user_wallet_address(user)
    token_balance = get_token_balance(wallet_address)
    
    context = {
        'user': user,
        'wallet_address': wallet_address,
        'token_balance': token_balance
    }
    return render(request, 'UserScreen.html', context)

def DriverScreen(request):
    """Display the driver screen"""
    user = get_current_user(request)
    user_type = get_user_type(request)
    
    if not user or user_type != 'Driver':
        return redirect('Login')
    
    # Get wallet from our storage
    wallet_address = get_user_wallet_address(user)
    token_balance = get_token_balance(wallet_address)
    
    context = {
        'driver': user,
        'wallet_address': wallet_address,
        'token_balance': token_balance,
        'today': date.today().strftime("%Y-%m-%d")
    }
    return render(request, 'DriverScreen.html', context)

# -------------------- Ride Management --------------------

def AddRide(request):
    user = get_current_user(request)
    if not user or get_user_type(request) != 'Driver':
        return redirect('Login')
        
    if request.method == 'POST':
        location = request.POST.get('t1')
        lat = request.POST.get('t2')
        long = request.POST.get('t3')
        seats = request.POST.get('t4')
        ride_date = request.POST.get('ride_date', date.today().strftime("%Y-%m-%d"))
        ride_time = request.POST.get('ride_time', '12:00')
        recurring = request.POST.get('recurring', 'none')
        
        ride_id = random.randint(1000, 9999)
        data = f"{ride_id}#{user}#{location}#{lat}#{long}#{seats}#{ride_date}#waiting#{ride_time}#{recurring}"
        
        contract_ride, web3 = load_contract('ride')
        try:
            current_rides = contract_ride.functions.getRide().call()
        except Exception as e:
            current_rides = ""

        if current_rides and current_rides.strip():
            updated_rides = current_rides + '\n' + data
        else:
            updated_rides = data
        
        send_transaction('ride', 'setRide', updated_rides)
        
        wallet_address = get_user_wallet_address(user)
        token_balance = get_token_balance(wallet_address)
        
        context = {
            'data': f'Ride created successfully! Ride ID: {ride_id}', 
            'driver': user,
            'wallet_address': wallet_address,
            'token_balance': token_balance
        }
        return render(request, 'DriverScreen.html', context)
    return redirect('DriverScreen')

@csrf_exempt
def schedule_ride(request):
    """Schedule a ride for future"""
    user = get_current_user(request)
    if not user or get_user_type(request) != 'Driver':
        return JsonResponse({'status': 'error', 'message': 'Not authorized'})
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            location = data.get('location')
            lat = data.get('lat')
            lng = data.get('lng')
            seats = data.get('seats')
            ride_date = data.get('ride_date')
            ride_time = data.get('ride_time')
            recurring = data.get('recurring', 'none')
            
            ride_id = random.randint(1000, 9999)
            data_str = f"{ride_id}#{user}#{location}#{lat}#{lng}#{seats}#{ride_date}#waiting#{ride_time}#{recurring}"
            
            contract_ride, web3 = load_contract('ride')
            try:
                current_rides = contract_ride.functions.getRide().call()
            except Exception as e:
                current_rides = ""

            if current_rides and current_rides.strip():
                updated_rides = current_rides + '\n' + data_str
            else:
                updated_rides = data_str
            
            send_transaction('ride', 'setRide', updated_rides)
            
            return JsonResponse({'status': 'success', 'ride_id': ride_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'POST required'})

def get_scheduled_rides(request):
    """Get scheduled rides for a user"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Not logged in'})
        
    contract_ride, web3 = load_contract('ride')
    try:
        current_rides = contract_ride.functions.getRide().call()
    except Exception as e:
        current_rides = ""
    
    scheduled_rides = []
    rows = [r for r in current_rides.split('\n') if r.strip()]
    for row in rows:
        arr = row.split('#')
        if len(arr) > 8:  # Has time info
            scheduled_rides.append({
                'id': arr[0],
                'driver': arr[1],
                'location': arr[2],
                'date': arr[6],
                'time': arr[8],
                'recurring': arr[9] if len(arr) > 9 else 'none',
                'status': arr[7]
            })
    
    return JsonResponse({'scheduled_rides': scheduled_rides})

def RideCompleteAction(request):
    user = get_current_user(request)
    if not user or get_user_type(request) != 'Driver':
        return redirect('Login')
        
    if request.method == 'POST':
        rid = request.POST.get('t1')
        passenger = request.POST.get('t2')
        miles = request.POST.get('t3')
        total_amount = request.POST.get('t4')

        logger.info(f"Driver {user} completing ride {rid} for passenger {passenger}, amount: {total_amount} CPT")

        # Update passenger records
        contract_car, web3 = load_contract('passengers')
        try:
            current = contract_car.functions.getPassengers().call()
        except Exception as e:
            current = ""

        rows = current.split('\n')
        record = ''
        passenger_found = False
        
        for row in rows:
            if not row.strip():
                continue
            arr = row.split('#')
            if arr[0] != passenger or arr[1] != rid:
                record += row + '\n'
            else:
                passenger_found = True
                # Set the amount and status to completed
                new_row = [arr[0], arr[1], arr[2], arr[3], miles, total_amount, '0', '0', 'completed']
                record += '#'.join(new_row) + '\n'
                logger.info(f"Updated passenger record: {new_row}")

        if not passenger_found:
            # Create a new passenger record if not found
            passenger_id = len(rows) + 1 if rows else 1
            new_record = f"{passenger}#{rid}#{user}#{passenger}#{miles}#{total_amount}#0#0#completed\n"
            record += new_record
            logger.info(f"Created new passenger record: {new_record}")

        send_transaction('passengers', 'setPassengers', record)

        # Update ride record status
        contract_ride, web3 = load_contract('ride')
        try:
            current_rides = contract_ride.functions.getRide().call()
        except Exception as e:
            current_rides = ""

        ride_rows = current_rides.split('\n')
        ride_record = ''
        ride_found = False
        
        for row in ride_rows:
            if not row.strip():
                continue
            arr = row.split('#')
            if arr[0] != rid:
                ride_record += row + '\n'
            else:
                ride_found = True
                arr[7] = 'completed'
                ride_record += '#'.join(arr) + '\n'
                logger.info(f"Updated ride record: {arr}")

        if not ride_found:
            logger.warning(f"Warning: Ride {rid} not found in ride records")

        send_transaction('ride', 'setRide', ride_record)

        wallet_address = get_user_wallet_address(user)
        token_balance = get_token_balance(wallet_address)

        context = {
            'data': f'Ride completed successfully! Passenger {passenger} needs to pay {total_amount} CPT.',
            'token_hint': True,
            'driver': user,
            'wallet_address': wallet_address,
            'token_balance': token_balance
        }
        return render(request, 'DriverScreen.html', context)
    return redirect('DriverScreen')

def ViewDrivers(request):
    user = get_current_user(request)
    if not user:
        return redirect('Login')
        
    if request.method == 'POST':
        destination = request.POST.get('t1')
        latitude = float(request.POST.get('t2'))
        longitude = float(request.POST.get('t3'))
        driver_location = [latitude, longitude]

        columns = ['Ride ID','Driver Name','Location Name','Latitude','Longitude','Available Seats','Ride Date','Time','Share Location']
        output = "<table border=1 align=center class='table table-striped'><tr>"
        for col in columns:
            output += f'<th>{col}</th>'
        output += "</tr>"

        contract_ride, web3 = load_contract('ride')
        try:
            current_rides = contract_ride.functions.getRide().call()
        except Exception as e:
            current_rides = ""

        rows = current_rides.split('\n')
        for row in rows:
            if not row.strip():
                continue
            arr = row.split('#')
            if len(arr) > 7 and arr[7] == 'waiting':
                try:
                    user_location = [float(arr[3]), float(arr[4])]
                    miles = geodesic(driver_location, user_location).miles
                    if miles <= 3:
                        output += '<tr>'
                        # Include time if available
                        ride_display = arr[:7]
                        if len(arr) > 8:
                            ride_display.append(arr[8])  # Add time
                        else:
                            ride_display.append('12:00')  # Default time
                        output += ''.join([f'<td>{x}</td>' for x in ride_display])
                        output += f'<td><a href="/ShareLocationAction?rid={arr[0]}&driver={arr[1]}" class="btn btn-sm btn-primary">Share Location</a></td></tr>'
                except (ValueError, IndexError) as e:
                    continue
        output += "</table>"
        
        wallet_address = get_user_wallet_address(user)
        token_balance = get_token_balance(wallet_address)
        
        context = {
            'data': output, 
            'user': user,
            'wallet_address': wallet_address,
            'token_balance': token_balance
        }
        return render(request, 'UserScreen.html', context)
    return redirect('UserScreen')

def ShareLocationAction(request):
    user = get_current_user(request)
    if not user:
        return redirect('Login')
        
    if request.method == 'GET':
        rid = request.GET.get('rid')
        driver_name = request.GET.get('driver')
        contract_pass, web3 = load_contract('passengers')
        try:
            current = contract_pass.functions.getPassengers().call()
        except Exception as e:
            current = ""

        rows = [r for r in current.split('\n') if r.strip()]
        passenger_id = len(rows) + 1 if rows else 1
        data = f"{passenger_id}#{rid}#{driver_name}#{user}#0#0#0#0#waiting\n"
        
        if current and current.strip():
            updated_passengers = current + data
        else:
            updated_passengers = data
            
        send_transaction('passengers', 'setPassengers', updated_passengers)
        
        wallet_address = get_user_wallet_address(user)
        token_balance = get_token_balance(wallet_address)
        
        context = {
            'data': f'Your request shared with driver {driver_name} (ID: {passenger_id})', 
            'user': user,
            'wallet_address': wallet_address,
            'token_balance': token_balance
        }
        return render(request, 'UserScreen.html', context)
    return redirect('UserScreen')

# -------------------- Token & Payment System --------------------

@csrf_exempt
def distribute_tokens(request):
    """Give CPT tokens to users for testing"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            
            if not username:
                return JsonResponse({'status': 'error', 'message': 'No username provided'})
            
            # Get wallet from our storage
            wallet_address = get_user_wallet_address(username)
            
            if wallet_address:
                token_contract, web3 = load_contract('token')
                amount = web3.to_wei(1000, 'ether')  # 1000 CPT tokens
                
                tx_hash = token_contract.functions.transfer(
                    web3.to_checksum_address(wallet_address),
                    amount
                ).transact({'from': web3.eth.default_account})
                
                receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
                
                return JsonResponse({
                    'status': 'success', 
                    'message': '1000 CPT tokens sent to your wallet!',
                    'tx_hash': tx_hash.hex(),
                    'wallet_address': wallet_address,
                    'amount': '1000'
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'No wallet address found for user'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'POST required'})

@csrf_exempt
def get_user_token_balance(request):
    """Get token balance for the current user"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Not logged in'})
    
    wallet_address = get_user_wallet_address(user)
    if wallet_address:
        try:
            token_contract, web3 = load_contract('token')
            balance = token_contract.functions.balanceOf(wallet_address).call()
            balance_tokens = web3.utils.fromWei(balance, 'ether')
            
            return JsonResponse({
                'status': 'success',
                'balance': balance_tokens,
                'wallet_address': wallet_address
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'No wallet address found'})

@csrf_exempt
def get_pending_payments(request):
    """Get pending payments for the current user"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Not logged in'})
        
    contract_pass, web3 = load_contract('passengers')
    try:
        current = contract_pass.functions.getPassengers().call()
    except Exception as e:
        current = ""

    pending_payments = []
    rows = [r for r in current.split('\n') if r.strip()]
    for row in rows:
        arr = row.split('#')
        if len(arr) > 8 and arr[3] == user and arr[8] == 'completed' and arr[5] != '0':
            pending_payments.append({
                'passenger_id': arr[0],
                'ride_id': arr[1],
                'driver': arr[2],
                'amount': arr[5],
                'miles': arr[4]
            })
    
    return JsonResponse({'pending_payments': pending_payments})

@csrf_exempt
def get_driver_wallet(request):
    """Get driver's wallet address - FIXED VERSION"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            driver_username = data.get('driver_username')
            
            if not driver_username:
                return JsonResponse({'error': 'No driver username provided'}, status=400)
            
            # First try to get from our wallet storage
            wallet_address = get_user_wallet_address(driver_username)
            
            if wallet_address:
                return JsonResponse({'wallet_address': wallet_address})
            
            # If not found in storage, try to get from blockchain
            contract_signup, web3 = load_contract('signup')
            try:
                stored = contract_signup.functions.getUser().call()
            except Exception as e:
                stored = ""
            
            rows = [r for r in stored.split('\n') if r.strip()]
            for row in rows:
                arr = row.split('#')
                if arr and arr[0] == driver_username and len(arr) > 6:
                    wallet_address = arr[6]
                    # Store it for future use
                    store_user_wallet(driver_username, wallet_address)
                    return JsonResponse({'wallet_address': wallet_address})
            
            # If still not found, return error
            return JsonResponse({'error': 'Driver wallet not found'}, status=404)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'POST required'}, status=400)

@csrf_exempt
def provide_token_info(request):
    """Return token ABI & address for frontend"""
    try:
        token_json_path = build_contract_path('CarpoolToken')
        if not os.path.exists(token_json_path):
            return JsonResponse({'error': 'token artifact not found'}, status=500)

        with open(token_json_path) as f:
            token_json = json.load(f)

        networks = token_json.get('networks', {})
        deployed = networks.get(CHAIN_NETWORK_ID) or (next(iter(networks.values())) if networks else None)
        if not deployed:
            return JsonResponse({'error': 'token not deployed'}, status=500)

        return JsonResponse({
            'address': deployed.get('address'),
            'abi': token_json.get('abi'),
            'decimals': 18
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def verify_token_payment(request):
    """Verify an ERC-20 token transfer happened on-chain - FIXED VERSION"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        tx_hash = payload.get('tx_hash')
        expected_to = payload.get('expected_to')
        expected_amount = int(payload.get('expected_amount', 0))
        passenger_username = payload.get('passenger')
        rid = payload.get('rid')

        if not tx_hash or not expected_to or expected_amount <= 0:
            return JsonResponse({'error': 'missing parameters'}, status=400)

        token_contract, web3 = load_contract('token')

        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            return JsonResponse({'error': f'web3 error: {str(e)}'}, status=500)

        if receipt is None:
            return JsonResponse({'error': 'transaction not found'}, status=400)
        
        if receipt.status != 1:
            return JsonResponse({'error': 'transaction failed'}, status=400)

        try:
            transfer_events = token_contract.events.Transfer().process_receipt(receipt)
        except Exception as e:
            return JsonResponse({'error': f'Error processing receipt: {str(e)}'}, status=400)

        matched = False
        for ev in transfer_events:
            ev_args = ev['args']
            to_addr = web3.to_checksum_address(ev_args.get('to'))
            value = ev_args.get('value')
            if to_addr.lower() == expected_to.lower() and int(value) >= expected_amount:
                matched = True
                break

        if not matched:
            return JsonResponse({'error': 'No matching token Transfer event found'}, status=400)

        # Update passenger record to mark as paid
        contract_pass, web3 = load_contract('passengers')
        try:
            current = contract_pass.functions.getPassengers().call()
        except Exception as e:
            current = ""

        rows = [r for r in current.split('\n') if r.strip()]
        new_record = ''
        for row in rows:
            arr = row.split('#')
            if arr[0] == passenger_username and arr[1] == rid:
                # Mark as paid
                arr[6] = tx_hash
                arr[8] = 'paid'
                new_record += '#'.join(arr) + '\n'
                logger.info(f"✅ Marked ride {rid} as paid with tx: {tx_hash}")
            else:
                new_record += row + '\n'

        if new_record != current:
            send_transaction('passengers', 'setPassengers', new_record)

        return JsonResponse({'status': 'ok', 'message': 'Payment verified!'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# -------------------- Additional Utility Views --------------------

def map_view(request):
    """Display map view for finding rides"""
    user = get_current_user(request)
    if not user:
        return redirect('Login')
    
    wallet_address = get_user_wallet_address(user)
    token_balance = get_token_balance(wallet_address)
    
    context = {
        'user': user,
        'wallet_address': wallet_address,
        'token_balance': token_balance
    }
    return render(request, 'MapView.html', context)

@csrf_exempt
def get_completed_rides_for_passenger(request):
    """Get completed rides that need payment from the current passenger"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Not logged in'})
        
    contract_pass, web3 = load_contract('passengers')
    try:
        current = contract_pass.functions.getPassengers().call()
    except Exception as e:
        current = ""

    completed_rides = []
    rows = [r for r in current.split('\n') if r.strip()]
    for row in rows:
        arr = row.split('#')
        # Look for rides where: passenger is current user, status is completed, amount > 0, and not paid
        if (len(arr) > 8 and 
            arr[3] == user and 
            arr[8] == 'completed' and 
            arr[5] != '0' and 
            arr[5] != '0.0' and
            (len(arr) <= 6 or arr[6] == '0' or arr[6] == '0#0')):  # Not paid yet
            completed_rides.append({
                'passenger_id': arr[0],
                'ride_id': arr[1],
                'driver': arr[2],
                'amount': arr[5],
                'miles': arr[4],
                'status': arr[8]
            })
    
    return JsonResponse({'completed_rides': completed_rides})

@csrf_exempt
def notify_passenger_payment(request):
    """Send notification to passenger about pending payment"""
    if request.method == 'POST':
        passenger_username = request.POST.get('passenger')
        ride_id = request.POST.get('ride_id')
        amount = request.POST.get('amount')
        
        # In a real app, you'd send email/push notification
        logger.info(f"Payment notification: Passenger {passenger_username} needs to pay {amount} CPT for ride {ride_id}")
        
        return JsonResponse({'status': 'notification_sent'})
    return JsonResponse({'status': 'error'})

# -------------------- Ratings & Safety --------------------

def Ratings(request):
    user = get_current_user(request)
    if not user:
        return redirect('Login')
        
    if request.method == 'GET':
        output = '<div class="mb-3"><label class="form-label">Driver Name</label><select name="t1" class="form-select">'
        contract_signup, web3 = load_contract('signup')
        try:
            stored = contract_signup.functions.getUser().call()
        except Exception as e:
            stored = ""

        rows = [r for r in stored.split('\n') if r.strip()]
        for row in rows:
            arr = row.split('#')
            if len(arr) > 5 and arr[5] == 'Driver':
                output += f'<option value="{arr[0]}">{arr[0]}</option>'
        output += "</select></div>"
        
        wallet_address = get_user_wallet_address(user)
        token_balance = get_token_balance(wallet_address)
        
        context = {
            'data1': output, 
            'user': user,
            'wallet_address': wallet_address,
            'token_balance': token_balance
        }
        return render(request, 'Ratings.html', context)
    return redirect('UserScreen')

@csrf_exempt
def get_completed_paid_rides(request):
    """Get rides that are completed AND paid"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Not logged in'})
        
    try:
        contract_pass, web3 = load_contract('passengers')
        current = contract_pass.functions.getPassengers().call()
    except Exception as e:
        current = ""

    paid_rides = []
    rows = [r for r in current.split('\n') if r.strip()]
    
    for row in rows:
        arr = row.split('#')
        # Look for rides where: driver is current user, status is 'paid'
        if (len(arr) > 8 and 
            arr[2] == user and  # driver is current user
            arr[8] == 'paid' and  # status is paid
            arr[5] != '0' and arr[5] != '0.0'):  # has payment amount
            
            paid_rides.append({
                'ride_id': arr[1],
                'passenger': arr[3],
                'amount': arr[5],
                'miles': arr[4],
                'tx_hash': arr[6] if len(arr) > 6 else '',
                'status': arr[8]
            })
    
    return JsonResponse({'paid_rides': paid_rides})

def RatingsAction(request):
    user = get_current_user(request)
    if not user:
        return redirect('Login')
        
    if request.method == 'POST':
        driver_name = request.POST.get('t1')
        rating = request.POST.get('t2')
        data = f"{user}#{driver_name}#{rating}\n"
        
        contract_ratings, web3 = load_contract('ratings')
        try:
            current = contract_ratings.functions.getRatings().call()
        except Exception as e:
            current = ""
            
        if current and current.strip():
            updated_ratings = current + data
        else:
            updated_ratings = data
            
        send_transaction('ratings', 'setRatings', updated_ratings)
        
        wallet_address = get_user_wallet_address(user)
        token_balance = get_token_balance(wallet_address)
        
        context = {
            'data': 'Ratings accepted! Thank you', 
            'user': user,
            'wallet_address': wallet_address,
            'token_balance': token_balance
        }
        return render(request, 'UserScreen.html', context)
    return redirect('UserScreen')

@csrf_exempt
def verify_user(request):
    """Verify user identity (simplified)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        
        # For demo: just return success without modifying blockchain
        logger.info(f"User {username} verification requested")
        return JsonResponse({'status': 'verified'})
    return JsonResponse({'status': 'error'})

@csrf_exempt
def emergency_contact(request):
    """Add emergency contact"""
    if request.method == 'POST':
        username = request.POST.get('username')
        contact_name = request.POST.get('contact_name')
        contact_phone = request.POST.get('contact_phone')
        
        # Store emergency contact (in a real app, use a separate contract)
        logger.info(f"Emergency contact added for {username}: {contact_name} - {contact_phone}")
        return JsonResponse({'status': 'contact_added'})
    return JsonResponse({'status': 'error'})