# FamilyBet - FIFA World Cup 2026

A family betting application for the FIFA World Cup 2026. Family members can place bets on matches and compete on the leaderboard using real match data from OpenLigaDB.

## Features

- 🏆 **Match Betting**: Place bets on all World Cup 2026 matches
- 📊 **5-3-1 Scoring**: 5 pts exact, 3 pts goal diff, 1 pt winner
- 🎯 **Tournament Betting**: Bet on winner and semifinalists before kickoff
- 🔄 **Auto Sync**: Daily sync of match results from OpenLigaDB
- 📱 **Mobile Friendly**: Responsive design for all devices
- 🔐 **Magic Links**: Simple token-based login
- ⚙️ **Admin Panel**: Manage users, enter bets for others, sync data

## Quick Start (Docker - Recommended)

### 1. Build and Run with Docker Compose

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

### 2. Initialize Database

```bash
# Create admin user
docker-compose exec familybet python init_db.py
```

### 3. Access the App

Open your browser to `http://localhost:5000`

### 4. First Login

1. Go to `/login`
2. Enter `admin@familybet.local`
3. Click the magic link shown on screen

### 5. Update Container (after code changes)

```bash
docker-compose down
docker-compose up --build -d
```

---

## Alternative: Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python init_db.py
```

This creates the database tables and an initial admin user.

### 3. Run the Application

```bash
python run.py
```

### 4. Access the App

Open your browser to `http://localhost:5000`

### 5. First Login

1. Go to `/login`
2. Enter `admin@familybet.local`
3. Click the magic link shown on screen

### 6. Setup Family Members

1. Go to Admin Panel
2. Add family member accounts
3. Share login emails with family

## Scoring System

| Prediction | Points |
|-----------|--------|
| Exact score (e.g., 3:1 = 3:1) | 5 |
| Correct goal diff (e.g., 3:1 vs 2:0) | 3 |
| Correct winner/draw | 1 |
| Wrong | 0 |

**Tournament Bonus:**
- Correct World Cup winner: 10 points
- Correct semifinalist: 5 points each

## Project Structure

```
familybet/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Database models
│   ├── routes/              # Blueprints
│   │   ├── auth.py          # Magic link auth
│   │   ├── main.py          # Main pages
│   │   ├── bets.py          # Betting logic
│   │   ├── admin.py         # Admin routes
│   │   └── api.py           # JSON API
│   ├── services/            # Business logic
│   │   ├── openligadb.py    # API client
│   │   ├── scoring.py       # Points calculation
│   │   └── scheduler.py     # Background jobs
│   └── templates/           # HTML templates
├── config.py                # Configuration
├── run.py                   # Entry point
├── init_db.py               # Database init
├── requirements.txt         # Dependencies
└── requirements.md          # Full requirements
```

## API Integration

Uses [OpenLigaDB](https://www.openligadb.de) for World Cup 2026 data:
- League: `wm2026`
- Season: `2026`
- Auto-sync: Every 24 hours
- Manual sync: Via admin panel

## Admin Features

- Add/remove family members
- Enter bets on behalf of any user
- Trigger manual match sync
- Recalculate all points
- View all bets and results

## Development

```bash
# Run in debug mode
python run.py

# Access admin at
http://localhost:5000/admin

# API endpoints
GET /api/matches
GET /api/leaderboard
GET /api/teams
```

## Deployment

### Docker (Recommended)

The application is containerized with Docker for easy deployment:

```bash
# Production deployment with custom secret
docker-compose down
SECRET_KEY=your-secret-key docker-compose up -d
```

**Docker Features:**
- Persistent SQLite database in `./data/` volume
- Automatic restart on failure
- Health checks configured
- Production-ready with Python 3.12 slim image

**Environment Variables:**
- `SECRET_KEY` - Change for production (required)
- `DATABASE_URL` - SQLite path (default: `sqlite:///data/familybet.db`)

### Manual Deployment

For production deployment without Docker:

1. Change `SECRET_KEY` in `config.py`
2. Set environment variable: `SECRET_KEY=your-secret-key`
3. Use WSGI server (e.g., gunicorn)
4. Ensure SQLite file is on persistent storage

```bash
# Example with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## Rounds

The World Cup 2026 has 5 rounds:
1. Group Phase (Gruppenphase)
2. Round of 16 (Achtelfinale)
3. Quarterfinals (Viertelfinale)
4. Semifinals (Halbfinale)
5. Final & 3rd Place (Finale & Spiel um Platz 3)

## License

Private family project.
