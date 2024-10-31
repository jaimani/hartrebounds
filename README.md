# Hart Rebounds Video Generator

A Python script that generates compilation videos of Josh Hart's rebounds from NBA games. The script downloads individual rebound clips from NBA.com, adds statistical overlays, and combines them into a single video. The videos can be found on [@HartRebounds](https://x.com/HartRebounds) after each game.

## My comments
This script was primarily generated by the ChatGPT o1-preview. I made some key changes, namely switching to playwright to download the videos instead of requests.get which didn't seem to work no matter how many prompts I made. Also made some minor ones like fixing some logic bugs directly instead of via prompts to save time (and o1-preview queries). Pretty much everything else was written by ChatGPT with no edits. The README and most of the comments were generated by Claude 3.5 Sonnet, again to save o1-preview queries and also they seemed to be better than the regular 4o results. I run this script manually so posts might be delayed depending on when I go to bed. 

There's an escape hatch to replace clips because sometimes the ones posted do not reflect actual Josh Hart rebounds. EG: [this is not in fact his 12th rebound of this game](https://www.nba.com/stats/events?CFID=&CFPARAMS=&GameEventID=423&GameID=0022400122&Season=2024-25&flag=1&title=Hart%20REBOUND%20(Off%3A1%20Def%3A11)) but [I had to manually find this clip which is his 12th rebound](https://www.nba.com/stats/events?CFID=&CFPARAMS=&GameEventID=421&GameID=0022400122&Season=2024-25&flag=1&title=Bridges%20BLOCK%20(2%20BLK)). Replacement clips are the only manual work required, everything is generated automatically.

## Usage
All rights to these videos belong to the NBA. The clips come from the NBA.com play-by-play game summaries. The purpose of this script is for a fan to generate a highlight video of one of his favorite players. There will be no attempts to monetize the results (although maybe Josh will use it for his next contract).

## Features

- Extracts rebound clips from NBA.com game data
- Downloads individual video clips for each rebound
- Adds overlay text showing offensive/defensive rebound stats
- Concatenates clips into a single compilation video
- Generates ready-to-use social media captions
- Allows for clip replacement if needed

## Prerequisites

- Python 3.7+
- Google Chrome browser installed
- FFmpeg installed and available in system PATH
- Playwright for Python

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd hart-rebounds
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install required Python packages:
```bash
pip install requests beautifulsoup4 playwright
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Install FFmpeg:
   - **Mac OS (using Homebrew):**
     ```bash
     brew install ffmpeg
     ```
   - **Windows:**
     - Download from [FFmpeg website](https://ffmpeg.org/download.html)
     - Add FFmpeg to system PATH
   - **Linux:**
     ```bash
     sudo apt-get update
     sudo apt-get install ffmpeg
     ```

## Usage

1. Find the NBA.com game URL you want to process. It should look like:
   `https://www.nba.com/game/cle-vs-nyk-0022400106/play-by-play?period=All`

2. Run the script:
```bash
python hartrebounds.py
```

3. When prompted, enter the NBA game URL.

4. The script will:
   - Download all Josh Hart rebound clips
   - Add statistical overlays
   - Combine clips into a single video
   - Generate social media captions
   - Allow you to replace any clips if needed

5. The final video will be saved in the current directory with the format:
   `AWAY_HOME_DATE_OffX_DefY_TotalZ.mp4`

## Troubleshooting

Common issues and solutions:

1. **Chrome Path Issues:**
   - Verify Chrome is installed in the default location
   - For Mac: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   - For Windows: Update the chrome_path variable in the script

2. **FFmpeg Not Found:**
   - Ensure FFmpeg is properly installed
   - Verify FFmpeg is in system PATH
   - Try running `ffmpeg -version` in terminal

3. **Rate Limiting:**
   - The script includes random delays between requests
   - If you encounter rate limiting, try increasing the delay values

## Notes

- The script uses NBA.com's public APIs and may break if they change
- Video quality depends on the source clips from NBA.com
- Chrome is required (Chromium won't work due to codec limitations)
- Some clips may need manual replacement due to NBA.com's video player quirks

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.