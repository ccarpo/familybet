"""User utilities for FamilyBet.

This module provides centralized user-related functionality
to ensure consistent user list handling across the application.
"""

from app import db
from app.models import User


def get_sorted_users(include_hidden=False, include_all=True):
    """Get alphabetically sorted list of all users.
    
    This function queries all users and returns them sorted by name.
    Hidden users (is_hidden_from_leaderboard=True) are excluded by default.
    
    Args:
        include_hidden: If True, include users hidden from leaderboard.
                       If False (default), exclude hidden users.
        include_all: If True, return all users. If False, applies include_hidden filter.
    
    Returns:
        List of User objects sorted by name (case-insensitive)
    """
    query = User.query
    
    if not include_hidden:
        query = query.filter_by(is_hidden_from_leaderboard=False)
    
    # Sort by name case-insensitively using SQL LOWER function
    users = query.order_by(db.func.lower(User.name)).all()
    
    return users


def get_user_by_id(user_id):
    """Get a user by their ID.
    
    Args:
        user_id: The user's ID
        
    Returns:
        User object or None if not found
    """
    return User.query.get(user_id)


def get_user_by_email(email):
    """Get a user by their email address.
    
    Args:
        email: The user's email
        
    Returns:
        User object or None if not found
    """
    return User.query.filter_by(email=email).first()


def get_user_by_token(token):
    """Get a user by their magic login token.
    
    Args:
        token: The magic login token
        
    Returns:
        User object or None if not found
    """
    return User.query.filter_by(magic_token=token).first()


def email_exists(email, exclude_user_id=None):
    """Check if an email address is already in use.
    
    Args:
        email: The email to check
        exclude_user_id: Optional user ID to exclude (for updates)
        
    Returns:
        True if email exists, False otherwise
    """
    query = User.query.filter_by(email=email)
    
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    
    return query.first() is not None
