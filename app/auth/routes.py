from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # 1. Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please login.', 'error')
            return redirect(url_for('auth.login'))

        # 2. Hash the password securely
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # 3. Create the new user and save to database
        new_user = User(email=email, password_hash=hashed_password, role='user')
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # 1. Find the user by email
        user = User.query.filter_by(email=email).first()

        # 2. Check if user exists and password matches
        if user and check_password_hash(user.password_hash, password):
            # 3. Check if account is archived (soft deleted)
            if user.is_archived:
                flash('This account has been deactivated.', 'error')
                return redirect(url_for('auth.login'))

            # 4. Log them in!
            login_user(user)
            
            # 5. Route them based on their role
            # 5. Route them based on their role
            if user.role in ['super_admin', 'admin', 'staff']:
                # Send admins to the new dashboard!
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('public.index')) # Send normal users to landing page
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('public.index'))