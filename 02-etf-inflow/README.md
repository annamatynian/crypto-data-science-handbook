# Bitcoin ETF Flows & BTC Price Correlation Analysis

A Python-based tool that analyzes the impact of institutional flows on Bitcoin price action using automated data scraping and statistical modeling.

## 📊 Project Overview
This project scrapes daily institutional flow data for Spot BTC ETFs (from Farside Investors) and synchronizes it with market price action. 

**Key Features:**
- **Automated Scraping:** Uses `cloudscraper` to bypass bot detection on financial data providers.
- **Statistical Analysis:** Calculates **Pearson Correlation Coefficient** to quantify the relationship between cumulative ETF liquidity and $BTC.
- **Cyberpunk Visualization:** High-fidelity dashboards using `mplcyberpunk`.

## 📈 Current Findings
- **Correlation:** 0.83 (Strong positive relationship)
- **Trend:** Cumulative inflows are currently the primary driver for BTC price discovery in the $95k-$97k range.

## 🛠 Tech Stack
- **Python 3.10+**
- **Libraries:** Pandas, BeautifulSoup4, YFinance, Matplotlib, Mplcyberpunk.

## 🚀 How to Run
1. Clone the repo: `git clone https://github.com/annamatynian/crypto-data-science-handbook`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the notebook: `jupyter notebook ETF_inflow_analysis.ipynb`