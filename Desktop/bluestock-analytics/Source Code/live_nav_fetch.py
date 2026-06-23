import os
import time
import requests
import pandas as pd

# Directories and Configurations
RAW_DATA_DIR = os.path.join("data", "raw")
os.makedirs(RAW_DATA_DIR, exist_ok=True)

SCHEMES = {
    "HDFC Top 100 Direct": 125497,
    "SBI Bluechip": 119551,
    "ICICI Bluechip": 120503,
    "Nippon Large Cap": 118632,
    "Axis Bluechip": 119092,
    "Kotak Bluechip": 120841
}

def fetch_nav_with_backoff(scheme_code, retries=5):
    """
    Fetches NAV details from api.mfapi.in using exponential backoff
    to guarantee reliable execution in case of network throttle.
    """
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    delay = 1
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    return data
            # If status code is bad (e.g., 429 rate limit or 500 error)
            time.sleep(delay)
            delay *= 2
        except requests.exceptions.RequestException:
            time.sleep(delay)
            delay *= 2
            
    print(f"Failed to fetch scheme code {scheme_code} after {retries} attempts.")
    return None

def main():
    all_live_navs = []

    print("=========================================")
    print("     MUTUAL FUND LIVE NAV INGESTION      ")
    print("=========================================\n")

    for scheme_name, code in SCHEMES.items():
        print(f"Fetching live NAV data for {scheme_name} (AMFI Code: {code})...")
        json_data = fetch_nav_with_backoff(code)
        
        if json_data:
            # Extract meta information
            meta = json_data.get("meta", {})
            fund_house = meta.get("fund_house", "N/A")
            scheme_type = meta.get("scheme_type", "N/A")
            
            # Fetch the most recent daily NAV record
            latest_record = json_data["data"][0]
            latest_date = latest_record.get("date")
            latest_nav = latest_record.get("nav")
            
            print(f" -> Found: NAV = INR {latest_nav} (As of Date: {latest_date})")
            
            all_live_navs.append({
                "Scheme Code": code,
                "Scheme Name": scheme_name,
                "Fund House": fund_house,
                "Scheme Type": scheme_type,
                "Latest Date": latest_date,
                "Live NAV": latest_nav
            })
            
            # Special deliverable for Task 4: HDFC Top 100 raw daily historic details saved in its own file
            if code == 125497:
                hdfc_df = pd.DataFrame(json_data["data"])
                hdfc_df["scheme_code"] = code
                hdfc_df["scheme_name"] = "HDFC Top 100 Direct"
                # Reorder columns nicely
                hdfc_df = hdfc_df[["scheme_code", "scheme_name", "date", "nav"]]
                raw_hdfc_path = os.path.join(RAW_DATA_DIR, "hdfc_top_100_live_nav.csv")
                hdfc_df.to_csv(raw_hdfc_path, index=False)
                print(f" -> Detailed historic data saved separately to: {raw_hdfc_path}")
                
        else:
            print(f" -> [Error] Skipping {scheme_name} due to fetch error.")
            
        # Polite delay to respect API rate limiting
        time.sleep(0.5)

    # Save summary of all key scheme NAVs
    if all_live_navs:
        summary_df = pd.DataFrame(all_live_navs)
        summary_path = os.path.join(RAW_DATA_DIR, "key_schemes_nav.csv")
        summary_df.to_csv(summary_path, index=False)
        print("\n=========================================")
        print(f"All live data written to: {summary_path}")
        print("=========================================")
        print(summary_df.to_string(index=False))

if __name__ == "__main__":
    main()