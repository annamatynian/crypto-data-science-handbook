"""
RWA vs NFT Market Analysis - Enterprise Edition
===============================================
A robust data pipeline that fetches:
1. RWA TVL from DefiLlama (Free API)
2. NFT Volume from Dune Analytics (Requires API Key)

Features:
- Caching system to save API credits
- Automatic data normalization
- Professional matplotlib visualization
- Error handling for enterprise environments

Author: @AMatynian
License: MIT
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
import json
import time
from pathlib import Path

# ==========================================
# ⚙️ CONFIGURATION (USER SETTINGS)
# ==========================================

# INSERT YOUR API KEY
DUNE_API_KEY = "RmlqXbXQFgxmC63oUdz9VaPa68Ri9fYs" 

DUNE_QUERY_ID = 6454950# "NFT Volume by Chain (Weekly)"

CACHE_DIR = Path("./cache")
CACHE_DURATION = 86400  # 24 hours cache (Dune data doesn't change often)
API_TIMEOUT = 30


# ==========================================
# 🛠️ AUXILIARY FUNCTIONS
# ==========================================
def setup_environment():
    if not CACHE_DIR.exists(): CACHE_DIR.mkdir()

def get_cached_data(filename):
    filepath = CACHE_DIR / filename
    if not filepath.exists(): return None
    try:
        with open(filepath, 'r') as f: return json.load(f)
    except: return None

def save_to_cache(data, filename):
    try:
        with open(CACHE_DIR / filename, 'w') as f:
            json.dump(data, f, default=str)
    except Exception as e: print(f"   ❌ Ошибка кэша: {e}")

# ==========================================
# 📡 MODULE 1: RWA (DefiLlama) - REAL DATA
# ==========================================
def fetch_rwa_data():
    print("\n" + "="*60)
    print("🚀 MODULE 1: FETCHING RWA DATA (DefiLlama)")
    print("="*60)

    # Проверка кэша
    cached = get_cached_data("rwa_real_2021.json")
    if cached:
        df = pd.DataFrame(cached)
        df['date'] = pd.to_datetime(df['date'])
        return df

    print("   📡 Downloading the list of protocols...")
    try:
        resp = requests.get("https://api.llama.fi/protocols", timeout=15)
        protocols = [p for p in resp.json() if p.get('category') == 'RWA']
        protocols.sort(key=lambda x: x.get('tvl', 0) or 0, reverse=True)
        top_protocols = protocols[:30] # We take more to include more old players
    except Exception as e:
        print(f"   ❌ API DefiLlama error: {e}")
        return pd.DataFrame()

    all_series = []
    for i, p in enumerate(top_protocols):
        print(f"      [{i+1}/{len(top_protocols)}] {p['name']}...", end="\r")
        try:
            r = requests.get(f"https://api.llama.fi/protocol/{p['slug']}", timeout=10)
            data = r.json()
            if 'tvl' in data:
                df = pd.DataFrame(data['tvl'])
                df['date'] = pd.to_datetime(df['date'], unit='s')
                df = df.set_index('date')['totalLiquidityUSD'].groupby(level=0).last()
                all_series.append(df)
        except: continue
    
    if not all_series: return pd.DataFrame()
    
    print(f"\n   ✓ Data aggregation...")
    combined = pd.concat(all_series, axis=1).fillna(0)
    total_tvl = combined.sum(axis=1).reset_index()
    total_tvl.columns = ['date', 'tvl']
    
    # Filter: Data since 2021
    total_tvl = total_tvl[total_tvl['date'] >= '2021-01-01']
    
    # Resampling by month
    total_tvl = total_tvl.set_index('date').resample('MS').mean().reset_index()
    total_tvl['tvl_billions'] = total_tvl['tvl'] / 1e9

    save_to_cache(total_tvl.to_dict(orient='records'), "rwa_2021.json")
    return total_tvl

# ==========================================
# 🎨 MODULE 2: NFT (Dune Analytics) - API ONLY
# ==========================================
def fetch_nft_data():
    print("\n" + "="*60)
    print("🎨 MODULE 2: FETCHING NFT DATA (Dune API)")
    print("="*60)

    # Cache check
    cached = get_cached_data("nft_real_2021.json")
    if cached:
        print("   📦 We found the cache, loading...")
        df = pd.DataFrame(cached)
        df['date'] = pd.to_datetime(df['date'])
        return df

    headers = {"X-Dune-API-Key": DUNE_API_KEY}
    
    # 1. Launch of query
    print(f"   ⏳ Launching query {DUNE_QUERY_ID} на Dune...")
    try:
        exec_resp = requests.post(
            f"https://api.dune.com/api/v1/query/{DUNE_QUERY_ID}/execute",
            headers=headers
        )
        exec_resp.raise_for_status()
        execution_id = exec_resp.json()['execution_id']
    except Exception as e:
        print(f"   ❌ Error when staring Dune: {e}")
        print("   ⚠️ Check API key и ID query!")
        return pd.DataFrame() 

    # 2. Awaiting result
    while True:
        status_resp = requests.get(
            f"https://api.dune.com/api/v1/execution/{execution_id}/status",
            headers=headers
        )
        state = status_resp.json()['state']
        print(f"      Статус: {state}...", end="\r")
        
        if state == 'QUERY_STATE_COMPLETED': break
        if state == 'QUERY_STATE_FAILED':
            print("\n   ❌ Dune query collapsed (SQL error).")
            return pd.DataFrame()
        time.sleep(2)

    # 3. Скачивание данных
    print("\n   ✓ Done! Downloading results...")
    results_resp = requests.get(
        f"https://api.dune.com/api/v1/execution/{execution_id}/results",
        headers=headers
    )
    rows = results_resp.json()['result']['rows']
    
    # Processing
    df = pd.DataFrame(rows)
    # Dune can return different column names, we are searching for those which we need
    cols = df.columns
    date_col = next((c for c in cols if 'date' in c or 'time' in c), 'date')
    vol_col = next((c for c in cols if 'vol' in c or 'amount' in c or 'usd' in c), 'volume')
    
    df = df.rename(columns={date_col: 'date', vol_col: 'volume'})
    df['date'] = pd.to_datetime(df['date'])
    df['volume_billions'] = pd.to_numeric(df['volume']) / 1e9
    
    # Filter and saving
    df = df[df['date'] >= '2021-01-01']
    df = df.sort_values('date')
    
    save_to_cache(df.to_dict(orient='records'), "nft_2021.json")
    print(f"   ✅ Downloaded {len(df)} months of data.")
    return df

# ==========================================
# 📊 MODULE 3: VISUALIZATION
# ==========================================
def create_dashboard(rwa_df, nft_df):
    print("\n" + "="*60)
    print("🎨 MODULE 3: GENERATING DASHBOARD")
    print("="*60)

    # Remove the last month (incomplete data)
    rwa_df = rwa_df.iloc[:-1].copy()
    nft_df = nft_df.iloc[:-1].copy()

    # Remove timezones for merging
    rwa_df['date'] = pd.to_datetime(rwa_df['date'], utc=True).dt.tz_localize(None)
    nft_df['date'] = pd.to_datetime(nft_df['date'], utc=True).dt.tz_localize(None)

    # Merge dataframes
    df = pd.merge(rwa_df, nft_df, on='date', how='inner')
    
    if df.empty:
        print("❌ Error: No date overlap. Verify that both sources have data for 2021.")
        return

    # Plotting
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(16, 8))
    fig.suptitle('Capital Rotation: NFT vs RWA (Real Data 2021-2025)', fontsize=24, fontweight='bold', color='white')

    # NFT
    ax1.plot(df['date'], df['volume_billions'], color='#ff0055', linewidth=2)
    ax1.fill_between(df['date'], df['volume_billions'], 0, color='#ff0055', alpha=0.3, label='NFT Volume ($B)')
    
    # RWA
    ax1.plot(df['date'], df['tvl_billions'], color='#00f2ea', linewidth=3)
    ax1.fill_between(df['date'], df['tvl_billions'], 0, color='#00f2ea', alpha=0.5, label='RWA TVL ($B)')

    ax1.set_ylabel("Billions USD", fontsize=14)
    ax1.legend(loc='upper center', fontsize=12, ncol=2)
    ax1.grid(alpha=0.1)
    
    # X-axis format
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    plt.tight_layout()
    plt.savefig("capital_rotation_real.png", dpi=300)
    print("\n   ✅ Plot saved: capital_rotation.png")

# ==========================================
# 🚀 EXECUTION
# ==========================================
if __name__ == "__main__":
    setup_environment()
    rwa = fetch_rwa_data()
    nft = fetch_nft_data()
    
    if not rwa.empty and not nft.empty:
        create_dashboard(rwa, nft)
    else:
        print("\n❌ Failed to generate plot. Check API errors above.")