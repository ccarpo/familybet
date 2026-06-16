from app import db
from app.models import User, Match, Bet, TournamentBet


class ScoringService:
    
    @staticmethod
    def recalculate_all_match_points():
        """Recalculate points for all bets on finished matches"""
        finished_matches = Match.query.filter_by(is_finished=True).all()
        
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
    def get_leaderboard():
        """Get sorted leaderboard with stats"""
        users = User.query.all()
        
        leaderboard = []
        for user in users:
            stats = ScoringService.get_user_stats(user.id)
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
    def get_user_stats(user_id):
        """Get detailed stats for a user"""
        from app.models import ScoringConfig
        bets = Bet.query.filter_by(user_id=user_id).all()
        config = ScoringConfig.get_current()
        
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
    def calculate_tournament_points():
        """
        Calculate points for tournament bets after tournament ends.
        This should be called once all semifinals are done and final is complete.
        
        Points system for tournament bets:
        - Correct winner: 10 points
        - Correct semifinalist: 5 points each (excluding winner)
        """
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
            
            # Check winner (10 points)
            if bet.winner_team_id == winner_id:
                points += 10
            
            # Check semifinalists (5 points each, excluding the winner team)
            semifinalists = [
                bet.semifinalist1_id,
                bet.semifinalist2_id,
                bet.semifinalist3_id
            ]
            
            for sf_id in semifinalists:
                if sf_id in semifinalist_ids and sf_id != winner_id:
                    points += 5
            
            bet.points_earned = points
        
        db.session.commit()
        print(f'Calculated tournament points for {len(tournament_bets)} users')
        return True
