#!/usr/bin/env python3
"""
Polymarket CLOB Client Initialization Script

Creates or derives API credentials and verifies connection.
Run once to set up credentials, then use them in the trading system.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# Load environment variables
env_path = Path(__file__).parent.parent / ".env.local"
load_dotenv(env_path)


async def initialize_polymarket_client():
    """Initialize and verify Polymarket CLOB client connection."""

    host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")
    chain_id = 137  # Polygon mainnet
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")

    if not private_key:
        print("ERROR: POLYMARKET_PRIVATE_KEY not set in .env.local")
        return None

    # Validate private key format
    if not private_key.startswith("0x") or len(private_key) != 66:
        print(f"ERROR: Invalid private key format. Expected 0x + 64 hex chars, got length {len(private_key)}")
        print(f"Key starts with: {private_key[:10]}...")
        return None

    print(f"Connecting to Polymarket CLOB at {host}")
    print(f"Chain ID: {chain_id} (Polygon Mainnet)")

    # Step 1: Create temporary client to derive API credentials
    print("\n[1/3] Creating temporary client...")
    temp_client = ClobClient(host, key=private_key, chain_id=chain_id)

    # Step 2: Create or derive API credentials
    print("[2/3] Deriving API credentials...")
    try:
        api_creds = temp_client.create_or_derive_api_creds()
        print(f"  API Key: {api_creds.api_key[:20]}...")
        print(f"  API Secret: {api_creds.api_secret[:20]}...")
        print(f"  API Passphrase: {api_creds.api_passphrase[:20]}...")
    except Exception as e:
        print(f"ERROR deriving credentials: {e}")
        return None

    # Step 3: Initialize full trading client
    # Signature type 0 = EOA wallet, 1 = Polymarket proxy wallet, 2 = Gnosis Safe
    signature_type = 0  # EOA wallet signing

    print("[3/3] Initializing trading client...")
    client = ClobClient(
        host,
        key=private_key,
        chain_id=chain_id,
        creds=api_creds,
        signature_type=signature_type,
    )

    # Verify connection by fetching server time
    print("\n--- Connection Test ---")
    try:
        server_time = client.get_server_time()
        print(f"Server time: {server_time}")
    except Exception as e:
        print(f"Warning: Could not get server time: {e}")

    # Get markets to verify API access
    print("\n--- Fetching Sample Markets ---")
    try:
        markets = client.get_markets()
        print(f"Found {len(markets)} markets")
        if markets:
            sample = markets[0]
            print(f"Sample market: {sample.get('question', 'N/A')[:60]}...")
    except Exception as e:
        print(f"Warning: Could not fetch markets: {e}")

    # Check balance if possible
    print("\n--- Account Status ---")
    try:
        # Get the wallet address from the client
        print(f"Funder address: {os.getenv('FUNDER_ADDRESS', 'Not set')}")
    except Exception as e:
        print(f"Could not get account info: {e}")

    print("\n" + "="*50)
    print("Polymarket client initialized successfully!")
    print("="*50)

    # Store credentials for use in config
    print("\nTo use in .env.local, add these derived credentials:")
    print(f"POLYMARKET_API_KEY={api_creds.api_key}")
    print(f"POLYMARKET_API_SECRET={api_creds.api_secret}")
    print(f"POLYMARKET_API_PASSPHRASE={api_creds.api_passphrase}")

    return client


if __name__ == "__main__":
    client = asyncio.run(initialize_polymarket_client())
    if client:
        print("\nClient ready for trading operations.")
    else:
        print("\nClient initialization failed. Check configuration.")
