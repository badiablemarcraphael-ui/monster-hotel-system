from flask import Blueprint, render_template
from app.models import RoomType, Review  # Make sure Review is imported!

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    # 1. Fetch all room classifications
    room_types = RoomType.query.all()
    
    # 2. Fetch ONLY 'published' reviews, limited to the latest 6
    published_reviews = Review.query.filter_by(status='published').order_by(Review.created_at.desc()).limit(6).all()
    
    # Pass both to the HTML template
    return render_template('public/index.html', room_types=room_types, reviews=published_reviews)