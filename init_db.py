#!/usr/bin/env python
"""
Initialize the database with an admin user.
Run this once after setting up the application.
"""

from app import create_app, db
from app.models import User

def init_admin():
    app = create_app()
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if admin already exists
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            print(f"Admin already exists: {admin.name} ({admin.email})")
            return
        
        # Create default admin user
        admin = User(
            name='Admin',
            email='admin@familybet.local',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        
        print(f"Admin user created: {admin.name} ({admin.email})")
        print("\nTo login, request a magic link at /login")
        print(f"User ID: {admin.id}")

if __name__ == '__main__':
    init_admin()
