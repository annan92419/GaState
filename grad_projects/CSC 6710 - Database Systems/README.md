```bash
Link to demo: https://youtu.be/BA7b1GwGNkQ
```


# Fantasy League Management System

A full-stack fantasy football management application that allows users to create teams, manage lineups, and compete in head-to-head league fixtures with simulated match results.

## Features

### Core Functionality
- **Team Building**: Select 11 starters/players within a £100M budget
- **Squad Constraints**: Maximum 2 players per real club, exactly 1 goalkeeper
- **Captain System**: Designate captain and vice-captain for bonus points
- **Transfer System**: Make up to 3 transfers between gameweeks
- **Chemistry Bonus**: +15 points when 6+ players stay together for 5 consecutive gameweeks
- **AI Recommender System**: Generates transfer recommendation based on performance and difficult schedule ahead

### Competition Format
- **Head-to-Head Leagues**: Fantasy teams compete directly against each other
- **League Standings**: Win = 3 points, Draw = 1 point, Loss = 0 points
- **Real Match Simulation**: Points based on simulated Premier League results
- **Live Standings**: Track both fantasy league and actual EPL table

### Point Scoring
- **Appearance**: +2 points for playing
- **Goals**: GK/DEF: +6, MID: +5, FWD: +4
- **Clean Sheets**: GK/DEF: +4 points
- **Goals Conceded**: GK/DEF: -1 per 2 goals conceded

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js (React/TypeScript)
- **Database**: PostgreSQL (Supabase)
- **Styling**: CSS Modules

## Prerequisites

- **Python** 3.8+
- **Node.js** 16+ and npm
- **PostgreSQL** (or Supabase account)
- **Git**

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/.../xFPL.git
cd xFPL
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cd backend
nano .env
```

**Edit `.env` with your database credentials:**
```env
DB_HOST=aws*****.****.supabase.com
DB_PORT=1234
DB_NAME=postgres
DB_USER=postgres.<user>
DB_PASSWORD=your-password
SSLMODE=require
```

### 3. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install
```

## Database Setup

### Step 1: Initialize Schema
Run `schema_complete.sql` (SQL) file in your Supabase SQL Editor

### Step 2: Generate Data CSVs
```bash
cd ../db

# For current season (2025/26)
python fetch_schema_data.py --out data --mode live --season 2526
```

### Step 3: Load Data into Database
```bash
python load_schema_data.py --data data
```

## Running the Application

### Start Backend Server
```bash
cd ../backend
python main.py
```

### Start Frontend Server
```bash
# in a different terminal (activate venv again)
cd frontend
npm run dev
```

The application will be available at `http://localhost:3000`

## Usage

### 1. Create Manager Account
- Navigate to `http://localhost:3000`
- Click "Account" button
- Create a new manager with username and email

### 2. Build Your Squad
- Click "Squad Builder" from the dashboard
- Select exactly 11 players (within £100M budget)
- Assign captain and vice-captain
- Choose starting gameweek
- Submit to create your fantasy team

### 3. Simulate Gameweeks
- Return to main dashboard
- Select your team and gameweek from dropdowns
- Click "Simulate GW" to generate match results
- View updated standings and your team's points

### 4. Join/Create Leagues
- Use league endpoints to create mini-leagues
- Generate fixtures for head-to-head competition
- View league tables with win/draw/loss records

## Project Structure
```
xFPL/
│
├── backend/
│   ├── ai_recommendations.py
│   ├── apply_transfers.py
│   ├── simulate_gameweek.py
│   ├── db.py
│   ├── main.py
│   ├── .env                     # create this file using your superbase credentials
│   └── data/                    # created with fetch_schema_data.py
│       ├── gameweek.csv
│       ├── match.csv
│       ├── player.csv
│       └── team.csv
│
├── db/
│   ├── schema_complete.sql
│   ├── fetch_schema_data.py
│   └── load_schema_data.py
│
├── frontend/
│   ├── app/
│   │   ├── account/
│   │   ├── team-builder/
│   │   ├── transfers/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── page.module.css
│   │   └── globals.css
│   ├── public/
│   ├── package.json
│   ├── next.config.js
│   └── ...
│
└── requirements.txt
```

## Rules & Constraints

1. **Squad Rules**:
   - Exactly 11 players
   - Maximum 2 players from same real club
   - Exactly 1 goalkeeper, at least 3 defenders, at least 2 midfilders, at least 1 attacker
   - Budget: £100.0M maximum

2. **Transfer Rules**:
   - Up to 3 transfers between gameweeks
   - Transfers apply before next GW lineup

3. **Chemistry Bonus**:
   - Requires 6+ players unchanged for 5 consecutive GWs
   - Awards +15 points once per qualifying streak

4. **Simulation Order**:
   - Gameweeks must be simulated sequentially
   - Cannot skip ahead if earlier GWs incomplete


## License
This project is for educational purposes.

## Acknowledgments
- Data source: Fantasy Premier League API
- Historical data: [Vaastav's FPL repository](https://github.com/vaastav/Fantasy-Premier-League)
