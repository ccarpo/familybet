# FamilyBet Requirements Document

## Overview
FamilyBet is a web application that allows family members to place bets on FIFA World Cup 2026 matches using real match data from OpenLigaDB.

---

## Functional Requirements

### 1. User Management
- [x] Users can log in using magic links (token-based, email-less)
- [x] Admin user can create new family member accounts
- [x] Admin user has special privileges (enter bets for others, sync data)
- [x] Simple session-based authentication

### 2. Match Data & Synchronization
- [x] Automatic daily sync of match data from OpenLigaDB (api.openligadb.de)
- [x] Manual sync trigger for admin
- [x] Store: match ID, teams, match date, round, results, finished status
- [x] League: FIFA World Cup 2026 (wm2026)

### 3. Rounds (Spielrunden)
- [x] Group Phase (Gruppenphase)
- [x] Round of 16 (Achtelfinale)
- [x] Quarterfinals (Viertelfinale)
- [x] Semifinals (Halbfinale)
- [x] Final & 3rd Place (Finale & Spiel um Platz 3)

### 4. Match Betting
- [x] Users can place bets on individual match scores (team1:team2)
- [x] Bets must be placed before match starts (deadline enforcement)
- [x] Users can change bets until deadline
- [x] Display all matches grouped by round
- [x] Show user's current bets on match list

### 5. Tournament Betting (Pre-Tournament)
- [x] Users can bet on World Cup winner before tournament starts
- [x] Users can bet on 3 other teams that will reach semifinals
- [x] Tournament bets close when first match starts
- [x] Winner cannot be one of the other 3 semifinalists (validation)

### 6. Scoring System (Configurable, Default 3-2-1)
- [x] **Configurable**: Admin can change point values via UI
- [x] **3 points**: Exact score prediction (default)
- [x] **2 points**: Correct goal difference (default)
- [x] **1 point**: Correct winner/draw (default)
- [x] **0 points**: Wrong prediction
- [x] **Auto-recalculate**: All historical points recalculated on change

### 7. Tournament Scoring
- [x] **10 points**: Correct World Cup winner
- [x] **5 points**: Correct semifinalist (per team, excluding winner)
- [x] Calculated after tournament completion

### 8. Leaderboard & Results
- [x] Display leaderboard with rankings
- [x] Show total points per user
- [x] Breakdown: exact predictions, correct diffs, correct winners
- [x] Show all bets for finished matches
- [x] Real-time point calculation after match sync

### 9. Admin Features
- [x] Admin can enter/change bets for any user
- [x] Admin can add new users
- [x] Admin can trigger manual match sync
- [x] Admin can recalculate all points
- [x] Admin can calculate tournament points

### 10. Mobile Responsiveness
- [x] Mobile-friendly layout (responsive design)
- [x] Touch-friendly buttons and inputs
- [x] Easy navigation on small screens
- [x] Readable match displays on mobile

---

## Non-Functional Requirements

### 1. Technology Stack
- [x] Python 3.x
- [x] Flask web framework
- [x] SQLAlchemy ORM
- [x] SQLite database
- [x] TailwindCSS for styling
- [x] Jinja2 templates

### 2. Data Storage
- [x] SQLite file-based database
- [x] No external database server required
- [x] Automatic table creation on startup

### 3. External API
- [x] OpenLigaDB API integration
- [x] Endpoint: https://api.openligadb.de
- [x] League shortcut: wm2026
- [x] Season: 2026

### 4. Scheduling
- [x] APScheduler for background tasks
- [x] Daily match sync (24h interval)
- [x] Graceful handling of API failures

### 5. Security
- [x] Magic link tokens expire after 24 hours
- [x] Session-based authentication
- [x] Admin-only routes protected
- [x] CSRF protection through session

---

## API Endpoints

### Public
- [x] GET / - Dashboard or redirect to login
- [x] GET /login - Login form
- [x] POST /login - Request magic link
- [x] GET /auth/<token> - Validate magic link

### Authenticated
- [x] GET /dashboard - User dashboard
- [x] GET /matches - All matches by round
- [x] GET /matches/<id> - Match detail + bet form
- [x] POST /bets - Submit/change match bet
- [x] POST /tournament-bets - Submit tournament bet
- [x] GET /leaderboard - Rankings

### Admin
- [x] GET /admin - Admin panel
- [x] POST /admin/users - Add user
- [x] GET /admin/users/<id> - User bets management
- [x] POST /admin/sync - Manual sync
- [x] POST /admin/recalculate - Recalculate points
- [x] POST /admin/calculate-tournament-points - Calc tournament points

### JSON API
- [x] GET /api/matches - JSON match list
- [x] GET /api/matches/<id>/bets - Bet data per match
- [x] GET /api/leaderboard - JSON leaderboard
- [x] GET /api/users/<id>/stats - User statistics
- [x] GET /api/teams - All teams

---

## Testing Checklist

### Setup
- [ ] Install requirements: `pip install -r requirements.txt`
- [ ] Run app: `python run.py`
- [ ] First admin user creation

### Authentication
- [ ] Request magic link for existing user
- [ ] Click magic link to login
- [ ] Verify session persists
- [ ] Logout and re-login

### Admin Functions
- [ ] Create new family member
- [ ] Create admin user
- [ ] View admin dashboard stats
- [ ] Trigger manual match sync
- [ ] Verify matches appear in database

### Match Betting
- [ ] View all matches by round
- [ ] Place bet on upcoming match
- [ ] Try to change bet before match starts
- [ ] Verify bet appears on match list
- [ ] Verify bet deadline enforcement

### Tournament Betting
- [ ] Place tournament bet before first match
- [ ] Validate winner ≠ semifinalists
- [ ] Verify tournament bet appears on dashboard
- [ ] Verify tournament bet closes after match starts

### Scoring
- [ ] Sync finished match with known result
- [ ] Place bets with different outcomes:
  - Exact match (5 pts)
  - Correct diff (3 pts)
  - Correct winner (1 pt)
  - Wrong (0 pts)
- [ ] Verify points calculated correctly
- [ ] Check leaderboard updates

### Leaderboard
- [ ] View leaderboard with rankings
- [ ] Verify total points calculation
- [ ] Check stats breakdown (5/3/1 pointers)
- [ ] Verify own highlighting

### Mobile
- [ ] Test on mobile device/simulator
- [ ] Verify responsive layout
- [ ] Check touch interactions
- [ ] Test navigation flow

---

## Deployment Notes

### Local Development
```bash
# Setup
pip install -r requirements.txt

# Run
python run.py

# Access
http://localhost:5000
```

### First Run Setup
1. Start the application
2. Create first admin user via shell or add to init script
3. Login as admin
4. Add family members
5. Trigger initial match sync

### Production Considerations
- Change default SECRET_KEY in config.py
- Use environment variables for sensitive config
- Set up persistent storage for SQLite file
- Consider email integration for real magic links

---

## Future Enhancements (Optional)

- [ ] Email integration for real magic links
- [ ] Push notifications for match results
- [ ] Group chat/comments per match
- [ ] Historical data from past tournaments
- [ ] Support for other leagues/tournaments
- [ ] User profile pages with stats
- [ ] Export results to PDF/Excel
