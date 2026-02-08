# Crypto Trading Indicator
Easy to use crypto trading indicator, based on the MM(Market Maker) strategy. Works with any cryptocurrency provided by Binance API.

## Overview
This system offers an automated workflow for traders and analysts. It combines powerful high-volume data processing with an intuitive command-line interface.
### Key Features
- Vector Candles Analysis: Detect MM activity through Volume-Spread Analysis (VSA) for Climax and Rising candles.
- Point of Interest (POI): Automatic identification of key Supply and Demand zones.
- Support & Resistance: Defining accurate support and resistance lines
- Parallel Processing: A backtest engine utilizing multiprocessing for maximum computational speed.
- Detects price reversals or goes with trend direction

### Installation & Setup
> The project follows modern standards via `pyproject.toml`
1. Clone the Repository:
   ```
   git clone https://github.com/Kalkata127/trading-indicator.git
   ```
2. Install the Package
   ```Installs all dependencies and registers the 'trading-bot' command```
   
   ```
   pip install -e
   ```
## Usage (CLI Interface)
Launch the system using the global command:
```
trading-bot
```
### Command Reference:
```
Command	Syntax	Description
```
| Command  | Arguments                          | Description                                      |
|----------|:----------------------------------:|-------------------------------------------------|
| list     | `[symbol]`                           | Lists available tokens in `data/`               |
| update   | `<symbol>`                         | Refreshes live data (7-day auto-fetch)          |
| signal   | `<symbol>`                           | Live Check: Scans for active signals            |
| fetch    | `<symbol> <start> <end>   `             | Downloads history (max 1-month chunks)          |
| plot     | `<symbol> <mode> [flags]  `             | Visualizes charts with indicators               |
| test     | `<symbol> <mode> [--rr X]  `            | Runs parallelized backtesting                   |
| delete   |` <symbol> <period>     `                | Removes data with confirmation                  |

### Examples:
- Updating Live Data:  
`TradingBot > update BTCUSDC`

- Fetching Historical Data:  
  `Fetches data from March 1st to March 25th, 2025`   
  `TradingBot > fetch ETHUSDC 01-03-2025:00:00 25-03-2025:00:00`

- Plotting with basic indicators (EMA and Vectors):  
  `TradingBot > plot ETHUSDC live --ema --vector`
  
- Plotting with all available flags  
`TradingBot > plot BTCUSDC live --volume --vector --pois --ema --sr`

- Scanning for a Signal (Automatically updates data and runs the strategy):  
`TradingBot > signal BTCUSDC`  

- Run a backtest for January with a minimum 2.0 Risk/Reward  
`TradingBot > test BTCUSDC backtest_01-01-2025_31-01-2025 --rr 2.0`  

## System Limits:
- Data Fetching: Maximum 30-day period allowed per historical request to ensure stability.
- Date Constraint: Data collection is restricted to periods starting from January 1st, 2025 onwards.
