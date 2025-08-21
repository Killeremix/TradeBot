import os
import time
import requests
import json

class BirdeyeClient:
    def __init__(self, newer_than_minutes, min_liquidity_usd, min_volume_1h):
        self.newer_than_minutes = newer_than_minutes
        self.min_liquidity_usd = min_liquidity_usd
        self.min_volume_1h = min_volume_1h
        self.api_key = "28d8fbf2ad53490eafbe49a263f9185d"  # Using the provided API key

    def fetch_latest_pairs(self):
        backoff = 1
        while True:
            try:
                # Use the exact working URL format with time_to parameter
                url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"
                headers = {
                    "accept": "application/json",
                    "x-chain": "solana",
                    "X-API-KEY": self.api_key
                }
                
                # Get current time in seconds (Unix timestamp)
                current_time = int(time.time())
                
                params = {
                    "time_to": current_time,  # Current time in seconds
                    "limit": 10,
                    "meme_platform_enabled": "false"
                }
                
                print(f"🌐 Fetching NEW LISTINGS from Birdeye API (time_to: {current_time})...")
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                
                if resp.status_code == 429:
                    print(f"⚠️ Rate limit hit, backing off for {backoff} seconds...")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 64)
                    continue
                
                resp.raise_for_status()
                backoff = 1
                data = resp.json()
                
                # Extract tokens from the response structure we now know
                if not isinstance(data, dict) or 'data' not in data:
                    print("❌ Unexpected response structure from Birdeye API")
                    return []
                
                data_content = data.get('data', {})
                if not isinstance(data_content, dict) or 'items' not in data_content:
                    print("❌ Expected 'items' not found in response data")
                    return []
                
                tokens = data_content.get('items', [])
                if not isinstance(tokens, list):
                    print("❌ Tokens data is not a list")
                    return []
                
                print(f"📊 Found {len(tokens)} tokens in API response")
                
                # Filter tokens based on our criteria
                filtered_tokens = []
                now_ms = int(time.time() * 1000)
                
                for i, token in enumerate(tokens):
                    print(f"🔍 Processing token {i+1}/{len(tokens)}")
                    
                    # Skip if token is not a dictionary
                    if not isinstance(token, dict):
                        print(f"⚠️ Token {i+1} is not a dictionary: {type(token)}")
                        continue
                    
                    # Get token address
                    address = token.get('address')
                    if not address:
                        print(f"⚠️ Token {i+1} has no address")
                        continue
                    
                    # Skip well-known tokens
                    if address in [
                        'So11111111111111111111111111111111111111112',  # Wrapped SOL
                        'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                        'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'   # USDT
                    ]:
                        print(f"⏭️  Skipping {address} - well-known token")
                        continue
                    
                    # Get liquidity
                    liquidity = token.get('liquidity', 0)
                    print(f"💰 Token {token.get('symbol', 'Unknown')} - Liquidity: ${liquidity:.2f}")
                    
                    # Apply liquidity filter
                    if liquidity < self.min_liquidity_usd:
                        print(f"❌ Token {address} doesn't meet liquidity requirement")
                        continue
                    
                    # Get creation time from DexScreener
                    created_at = self.get_creation_time_from_dexscreener(address)
                    if created_at:
                        age_minutes = (now_ms - created_at) / 60000
                        print(f"⏱️  Token {address} created {age_minutes:.1f} minutes ago (from DexScreener)")
                        
                        # Only include tokens newer than our threshold
                        if age_minutes > self.newer_than_minutes:
                            print(f"⏭️  Skipping {address} - too old ({age_minutes:.1f} minutes)")
                            continue
                    else:
                        print(f"⚠️ Could not get creation time for {address}, assuming it's new")
                        age_minutes = 0
                    
                    # Convert token data to our format
                    pair_data = self.convert_to_pair_format(token, created_at if created_at else now_ms)
                    if pair_data:
                        filtered_tokens.append(pair_data)
                        print(f"✅ Qualifying token: {token.get('symbol', 'Unknown')} - {age_minutes:.1f}m old")
                
                print(f"✅ Found {len(filtered_tokens)} NEW tokens after filtering")
                return filtered_tokens
                
            except Exception as e:
                print(f"❌ Birdeye API error: {e}. Retry in {backoff}s.")
                import traceback
                traceback.print_exc()
                time.sleep(backoff)
                backoff = min(backoff * 2, 64)

    def get_creation_time_from_dexscreener(self, token_address):
        """Get token creation time from DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            resp = requests.get(url, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get('pairs', [])
                
                if pairs:
                    # Get the pair with the highest liquidity (most likely the main pair)
                    main_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
                    created_at = main_pair.get('pairCreatedAt')
                    
                    if created_at:
                        return created_at
            
            return None
        except Exception as e:
            print(f"⚠️ Error getting creation time from DexScreener for {token_address}: {e}")
            return None

    def convert_to_pair_format(self, token, created_at):
        """Convert Birdeye token format to our pair format"""
        try:
            # Get values with fallbacks for different field names
            def get_value(fields, default=0):
                for field in fields:
                    if field in token:
                        return token[field]
                return default
            
            address = token.get('address', '')
            name = get_value(['name', 'tokenName'], 'Unknown')
            symbol = get_value(['symbol', 'tokenSymbol'], 'UNKNOWN')
            price = get_value(['price', 'priceUSD'], 0)
            liquidity = get_value(['liquidity', 'liquidityUSD', 'totalLiquidityUSD'], 0)
            volume_24h = get_value(['v24hUSD', 'volume24h', 'volume24hUSD'], 0)
            market_cap = get_value(['mc', 'marketCap', 'marketCapUSD'], 0)
            change_24h = get_value(['v24hChangePercent', 'priceChange24h'], 0)
            
            pair_data = {
                'pairAddress': address,
                'baseToken': {
                    'name': name,
                    'symbol': symbol,
                    'address': address
                },
                'priceUsd': price,
                'liquidity': {'usd': liquidity},
                'volume': {'h1': volume_24h / 24 if volume_24h else 0},
                'marketCap': market_cap,
                'pairCreatedAt': created_at,
                'url': f"https://birdeye.so/token/{address}",
                'dexId': 'Birdeye',
                'v24hChangePercent': change_24h
            }
            return pair_data
        except Exception as e:
            print(f"❌ Error converting token data: {e}")
            return None

    def score_token(self, liquidity, volume, kol_count=0):
        base_score = min(100, (liquidity / 1000) + (volume / 500))
        kol_bonus = kol_count * 10
        return min(100, base_score + kol_bonus)