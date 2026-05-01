from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    load_dotenv()
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    
    # --- Initialize Login Manager ---
    login_manager.login_view = 'auth.login' # Where to send users if they aren't logged in
    login_manager.init_app(app)

    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- Register Blueprints ---
    from app.public.routes import public_bp
    app.register_blueprint(public_bp)
    
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp)
    
    # ... (Keep your previous blueprint registrations)
    
    # 4. User Blueprint (Bookings & Profiles)
    from app.user.routes import user_bp
    app.register_blueprint(user_bp)
    
    return app