# Project Aegis — Agent Research Command Center

Aegis is an autonomous market research and signaling system. It uses a multi-agent architecture to scan markets, analyze signals, and generate trading insights.

## Prerequisites

- Python 3.9+
- Internet connection (for yfinance and data scraping)

## Installation

Install the required Python dependencies:

```bash
pip install streamlit pandas plotly yfinance streamlit-autorefresh numpy
```

## Running the Project

Project Aegis consists of two main components that should run simultaneously.

### 1. The Autonomous Brain (Background Loop)
This is the core engine that performs market scans, news research, and signal scoring on a schedule.

```bash
python src/aegis_brain.py --loop
```

Optional arguments:
- `--interval <minutes>`: Set a custom scan interval (default: 30).

### 2. The Command Center Dashboard
A Streamlit-based dark-themed terminal for visualizing live logs, performance charts, and signal cards.

```bash
python -m streamlit run dashboard/app.py
```

## System Architecture

- **`src/`**: Core engine components (Scanner, Analyst, Researcher, etc.).
- **`dashboard/`**: Streamlit application code.
- **`memory/`**: Peer-to-peer knowledge storage and performance history.
- **`research_outputs/`**: Generated markdown reports for every trade alert.

## Monitoring
- **Logs**: Real-time activity is logged to `agent_logs.txt`.
- **Dashboard**: Open the URL provided by Streamlit (usually `http://localhost:8501`) to view the UI.
