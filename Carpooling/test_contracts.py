from CarpoolApp.views import readDetails

def main():
    print("=== Testing Carpool Contract ===\n")

    # Test all Carpool-related data
    for contract_type in ["signup", "ride", "passengers", "ratings"]:
        readDetails(contract_type)
        print("\n")

    print("=== Testing Token Contract ===\n")
    # Test token contract
    readDetails("token")

if __name__ == "__main__":
    main()
