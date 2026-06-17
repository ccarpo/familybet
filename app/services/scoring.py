from app import db
from app.models import User, Match, Bet, TournamentBet


class ScoringService:
    
    @staticmethod
    def recalculate_all_match_points(tournament_id=None):
        """Recalculate points for all bets on finished matches
        
        Args:
            tournament_id: Optional tournament ID to scope recalculation
        """
        from app.models import Tournament
        
        # Build match query
        query = Match.query.filter_by(is_finished=True)
        
        # Filter by tournament if specified
        if tournament_id:
            tournament = Tournament.query.get(tournament_id)
            if tournament and tournament.league_shortcut:
                query = query.filter_by(league_shortcut=tournament.league_shortcut)
        
        finished_matches = query.all()
        
        for match in finished_matches:
            if match.team1_score is None or match.team2_score is None:
                continue
            
            bets = Bet.query.filter_by(match_id=match.id).all()
            for bet in bets:
                points = bet.calculate_points(match.team1_score, match.team2_score)
                bet.points_earned = points
        
        db.session.commit()
        return True
    
    @staticmethod
    def get_leaderboard(include_hidden=False, tournament_id=None):
        """Get sorted leaderboard with stats

        Args:
            include_hidden: If True, include users hidden from leaderboard
            tournament_id: Optional tournament ID for tournament-scoped leaderboard
        """
        from app.services.users import get_sorted_users
        from app.models import Tournament
        
        users = get_sorted_users(include_hidden=include_hidden)
        
        # Get active tournament if none specified
        if tournament_id is None:
            active_tournament = Tournament.get_active()
            if active_tournament:
                tournament_id = active_tournament.id

        leaderboard = []
        for user in users:
            stats = ScoringService.get_user_stats(user.id, tournament_id=tournament_id)
            leaderboard.append({
                'user': user,
                'total_points': stats['total_points'],
                'exact_predictions': stats['exact_predictions'],
                'correct_diffs': stats['correct_diffs'],
                'correct_winners': stats['correct_winners'],
                'total_bets': stats['total_bets']
            })

        # Sort by total points descending
        leaderboard.sort(key=lambda x: x['total_points'], reverse=True)

        # Add rank
        for i, entry in enumerate(leaderboard, 1):
            entry['rank'] = i

        return leaderboard
    
    @staticmethod
    def get_user_stats(user_id, tournament_id=None):
        """Get detailed stats for a user
        
        Args:
            user_id: User ID to get stats for
            tournament_id: Optional tournament ID for tournament-scoped stats
        """
        from app.models import ScoringConfig, Tournament, Match
        
        # Get active tournament if none specified
        if tournament_id is None:
            active_tournament = Tournament.get_active()
            if active_tournament:
                tournament_id = active_tournament.id
        
        # Get scoring config for tournament
        config = ScoringConfig.get_current(tournament_id=tournament_id)
        
        # Filter bets by tournament (through matches)
        if tournament_id:
            # Get tournament for league_shortcut
            tournament = Tournament.query.get(tournament_id)
            if tournament and tournament.league_shortcut:
                # Filter bets to matches of this tournament
                match_ids = [m.id for m in Match.query.filter_by(
                    league_shortcut=tournament.league_shortcut
                ).all()]
                bets = Bet.query.filter_by(user_id=user_id).filter(
                    Bet.match_id.in_(match_ids)
                ).all()
            else:
                bets = Bet.query.filter_by(user_id=user_id).all()
        else:
            bets = Bet.query.filter_by(user_id=user_id).all()
        
        total_points = sum(bet.points_earned or 0 for bet in bets)
        
        # Count by matching the config values
        exact_predictions = sum(1 for bet in bets 
            if bet.match and bet.match.is_finished 
            and bet.team1_score_pred == bet.match.team1_score 
            and bet.team2_score_pred == bet.match.team2_score)
        
        correct_diffs = sum(1 for bet in bets 
            if bet.match and bet.match.is_finished 
            and (bet.team1_score_pred - bet.team2_score_pred) == (bet.match.team1_score - bet.match.team2_score)
            and not (bet.team1_score_pred == bet.match.team1_score and bet.team2_score_pred == bet.match.team2_score))
        
        correct_winners = sum(1 for bet in bets 
            if bet.match and bet.match.is_finished 
            and bet.points_earned == config.points_winner)
        
        # Add tournament bet points
        tournament_bet = TournamentBet.query.filter_by(user_id=user_id).first()
        if tournament_bet and tournament_bet.points_earned:
            total_points += tournament_bet.points_earned
        
        return {
            'total_points': total_points,
            'exact_predictions': exact_predictions,
            'correct_diffs': correct_diffs,
            'correct_winners': correct_winners,
            'total_bets': len(bets),
            'tournament_bet': tournament_bet
        }
    
    @staticmethod
    def calculate_tournament_points(tournament_id=None):
        """
        Calculate points for tournament bets after tournament ends.
        This should be called once all semifinals are done and final is complete.
        
        Args:
            tournament_id: Optional tournament ID (uses active if not specified)
        """
        from app.models import Tournament, ScoringConfig
        
        # Get active tournament if none specified
        if tournament_id is None:
            active_tournament = Tournament.get_active()
            if active_tournament:
                tournament_id = active_tournament.id
        
        # Get scoring config for extra points
        scoring_config = ScoringConfig.get_current(tournament_id=tournament_id)
        
        # Get the final match to determine winner
        final_match = Match.query.filter(
            Match.round_name.ilike('%finale%')
        ).filter(
            ~Match.round_name.ilike('%platz 3%')  # Exclude 3rd place match
        ).filter_by(is_finished=True).first()
        
        if not final_match:
            print("Final match not finished yet, cannot calculate tournament points")
            return False
        
        winner_id = final_match.get_winner_id()
        if not winner_id:
            print("No winner determined in final")
            return False
        
        # Get semifinal matches to determine all 4 semifinalists
        semifinal_matches = Match.query.filter(
            Match.round_name.ilike('%halbfinale%')
        ).filter_by(is_finished=True).all()
        
        semifinalist_ids = set()
        for match in semifinal_matches:
            semifinalist_ids.add(match.team1_id)
            semifinalist_ids.add(match.team2_id)
        
        # Calculate points for each user's tournament bet
        tournament_bets = TournamentBet.query.all()
        
        for bet in tournament_bets:
            points = 0
            
            # Check winner (champion points from config)
            if bet.winner_team_id == winner_id:
                points += scoring_config.points_champion or 0
            
            # Check semifinalists (semifinalist points from config, excluding winner team)
            semifinalists = [
                bet.semifinalist1_id,
                bet.semifinalist2_id,
                bet.semifinalist3_id
            ]
            
            semifinalist_points = scoring_config.points_semifinalist or 0
            for sf_id in semifinalists:
                if sf_id in semifinalist_ids and sf_id != winner_id:
                    points += semifinalist_points
            
            bet.points_earned = points
        
        db.session.commit()
        print(f'Calculated tournament points for {len(tournament_bets)} users')
        return True
