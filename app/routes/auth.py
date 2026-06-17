from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User
from app import db
from app.services.users import get_user_by_email, get_user_by_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Bitte Email eingeben', 'error')
            return render_template('login.html')
        
        user = get_user_by_email(email)
        
        if not user:
            flash('Email nicht gefunden. Bitte Admin kontaktieren.', 'error')
            return render_template('login.html')
        
        # Generate magic token
        token = user.generate_magic_token()
        db.session.commit()
        
        # Display the magic link directly (since we don't have email configured)
        magic_link = url_for('auth.magic_login', token=token, _external=True)
        
        flash(f'Login-Link erstellt! Klicke hier: <a href="{magic_link}">Einloggen</a>', 'success')
        return render_template('login.html', magic_link=magic_link)
    
    return render_template('login.html')

@auth_bp.route('/auth/<token>')
def magic_login(token):
    user = get_user_by_token(token)
    
    if not user:
        flash('Ungültiger oder abgelaufener Login-Link', 'error')
        return redirect(url_for('auth.login'))
    
    if not user.is_token_valid():
        flash('Login-Link ist abgelaufen. Bitte neu anfordern.', 'error')
        return redirect(url_for('auth.login'))
    
    # Log the user in
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['is_admin'] = user.is_admin
    
    # Clear the token
    user.magic_token = None
    user.token_expires_at = None
    db.session.commit()
    
    flash(f'Willkommen, {user.name}!', 'success')
    
    if user.is_admin:
        return redirect(url_for('admin.index'))
    return redirect(url_for('main.dashboard'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Erfolgreich abgemeldet', 'success')
    return redirect(url_for('auth.login'))
