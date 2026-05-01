from app import create_app, db
from dotenv import load_dotenv
import os

load_dotenv()

app = create_app()
with app.app_context():
    print("Connecting to cloud database...")
    db.create_all()
    print("Tables created successfully!")