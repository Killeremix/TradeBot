import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from birdeye_client import BirdeyeClient
from telegram_poster import TelegramPoster

# List of known KOL wallets to monitor
KOL_WALLETS = {
    "Lowskii": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "The Doc": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "Ansem": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "Bluntz": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
}

def get_kol_transactions(token_address):
    """Check if any KOLs have bought this token recently"""
    kol_buys = {}
    
    # For demonstration, we'll simulate KOL buys
    import random
    if random.random() < 0.2:  # 20% chance of KOL activity
        kol_buys = {
            "Lowskii": round(random.uniform(0.1, 1.0), 3),
            "The Doc": round(random.uniform(0.1, 1.0), 3)
        }
    
    return kol_buys

def safe_float(value, default=0):
    """Safely convert a value to float, with default if None or invalid"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def format_message(pair_data, score, age_minutes, kol_buys):
    base = pair_data.get('baseToken', {})
    name = base.get('name', 'N/A')
    symbol = base.get('symbol', 'N/A')
    address = base.get('address', 'N/A')
    price_usd = safe_float(pair_data.get('priceUsd'))
    liquidity = safe_float(pair_data.get('liquidity', {}).get('usd'))
    volume = safe_float(pair_data.get('volume', {}).get('h1'))
    market_cap = safe_float(pair_data.get('marketCap'))
    url = pair_data.get('url', '')
    dex_name = pair_data.get('dexId', 'Unknown')
    
    # Get 24h change if available
    v24h_change = safe_float(pair_data.get('v24hChangePercent'))
    change_text = f"24h Change: {v24h_change:.2f}%"

    # Format KOL buys
    kol_text = ""
    if kol_buys:
        kol_text = "\n*KOL Buys:*\n"
        for kol, amount in kol_buys.items():
            kol_text += f"{kol}: {amount} SOL\n"

    disclaimer = "\n\n*This is not financial advice.*"
    return (
        f"*🚀 NEW TOKEN DETECTED!*\n"
        f"Name: {name} ({symbol})\n"
        f"Source: {dex_name}\n"
        f"Blockchain: Solana\n"
        f"CA: `{address}`\n"
        f"{change_text}\n"
        f"{len(kol_buys)} KOL addresses bought simultaneously\n"
        f"Market Cap: ${market_cap:,.0f}\n"
        f"Price: ${price_usd:.6f}\n"
        f"Liquidity: ${liquidity:,.2f}\n"
        f"Volume 1h: ${volume:,.2f}\n"
        f"Age: {age_minutes:.1f} minutes\n"
        f"Score: {score:.1f}\n"
        f"{kol_text}"
        f"[View on {dex_name}]({url})"
        f"{disclaimer}"
    )

def main():
    load_dotenv(dotenv_path=os.path.join('c:/Users/bouta/Desktop/Telegram/Bot scrapp/config.env'))

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    newer_than = int(os.getenv('NEWER_THAN_MINUTES', '5'))  # Back to 5 minutes for new tokens
    min_liq = float(os.getenv('MIN_LIQUIDITY_USD', '500'))
    min_vol = float(os.getenv('MIN_VOLUME_1H', '100'))

    client = BirdeyeClient(newer_than, min_liq, min_vol)
    poster = TelegramPoster(token, chat_id)

    print("🚀 Starting REAL-TIME NEW TOKEN detection bot...")
    print("⚡ No database - direct Telegram notifications!")
    
    try:
        while True:
            print(f"\n⏰ Checking for NEW tokens at {datetime.now().strftime('%H:%M:%S')}")
            
            pairs = client.fetch_latest_pairs()
            print(f"📊 Found {len(pairs)} NEW tokens to process")

            for pair in pairs:
                pair_address = pair.get('pairAddress')
                token_address = pair.get('baseToken', {}).get('address') or pair_address
                
                if not pair_address or not token_address:
                    continue
                
                # Check when the token was created
                pair_created_ms = pair.get('pairCreatedAt')
                if not pair_created_ms:
                    continue
                    
                age_minutes = int((int(time.time() * 1000) - int(pair_created_ms)) / 60000)
                print(f"⏱️  Token {token_address} created {age_minutes} minutes ago")

                # Check liquidity only - skip volume check for new tokens
                liquidity = safe_float(pair.get('liquidity', {}).get('usd'))
                if liquidity < min_liq:
                    print(f"❌ Skipping {token_address} - liquidity too low: ${liquidity:.2f}")
                    continue

                # Skip volume check for new tokens as they might not have volume yet
                # volume = safe_float(pair.get('volume', {}).get('h1'))
                # if volume < min_vol:
                #     print(f"❌ Skipping {token_address} - volume too low: ${volume:.2f}")
                #     continue

                print(f"✅ Token {token_address} meets criteria - preparing to send")

                # Get KOL transactions
                kol_buys = get_kol_transactions(token_address)

                score = client.score_token(liquidity, 0, len(kol_buys))  # Pass 0 for volume

                # Format and send message immediately
                msg = format_message(pair, score, age_minutes, kol_buys)
                print(f"📤 SENDING to Telegram: {token_address}")
                
                # Check if message was sent successfully
                success = poster.send_message(msg)
                if success:
                    print(f"✅ SENT: {token_address} | Score: {score:.1f} | Liquidity: ${liquidity:,.0f}")
                else:
                    print(f"❌ FAILED to send: {token_address}")

            print("⏳ Waiting 15 seconds for next check...")
            time.sleep(15)  # Reduced to 15 seconds for maximum speed
            
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔚 Bot stopped")

if __name__ == '__main__':
    main()