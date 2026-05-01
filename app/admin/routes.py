from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.models import RoomType, Room, User, Booking, Review
from app import db
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- SECURITY DECORATOR ---
# This ensures only admins and staff can access these routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role == 'user':
            flash('Access Denied. Terminal restricted to authorized personnel only.', 'error')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function

# --- ADMIN DASHBOARD ---
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Let's count some basic stats to display on the dashboard
    total_users = User.query.filter_by(role='user').count()
    total_rooms = Room.query.count()
    return render_template('admin/dashboard.html', total_users=total_users, total_rooms=total_rooms)

# --- ROOM MANAGEMENT ---

@admin_bp.route('/room-types/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_room_type():
    if request.method == 'POST':
        # Grab the data from the HTML form
        name = request.form.get('name')
        base_price = request.form.get('base_price')
        capacity = request.form.get('capacity')
        description = request.form.get('description')
        image_url = request.form.get('image_url')

        # Create a new RoomType object
        new_type = RoomType(
            name=name,
            base_price=base_price,
            capacity=capacity,
            description=description,
            image_url=image_url
        )
        
        # Save it to monster_db
        db.session.add(new_type)
        db.session.commit()
        
        flash(f'Room Type "{name}" added successfully!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/add_room_type.html')

@admin_bp.route('/rooms/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_room():
    # 1. Fetch all room types so the Admin can choose one from a dropdown
    room_types = RoomType.query.all()
    
    # 2. AUTO-ASCENDING LOGIC: Find the highest room number currently in the database
    last_room = Room.query.order_by(Room.room_number.desc()).first()
    # If a room exists, add 1. If no rooms exist yet, start at Room 101.
    next_room_number = (last_room.room_number + 1) if last_room else 101 

    if request.method == 'POST':
        room_type_id = request.form.get('room_type_id')
        room_number = request.form.get('room_number') # We will pass the auto-number here
        
        # Check if the admin accidentally typed a room number that already exists
        existing_room = Room.query.filter_by(room_number=room_number).first()
        if existing_room:
            flash(f'Room {room_number} already exists! Sequence reset.', 'error')
            return redirect(url_for('admin.add_room'))

        # Create the physical room
        new_room = Room(
            room_number=room_number,
            room_type_id=room_type_id,
            status='available'
        )
        
        db.session.add(new_room)
        db.session.commit()
        
        flash(f'Physical Room {room_number} initialized successfully!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/add_room.html', room_types=room_types, next_room_number=next_room_number)

# --- TRANSACTION MANAGEMENT ---

@admin_bp.route('/bookings')
@login_required
@admin_required
def manage_bookings():
    # Fetch ALL bookings in the system, newest first
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@admin_bp.route('/bookings/<int:booking_id>/status/<string:status>')
@login_required
@admin_required
def update_booking_status(booking_id, status):
    booking = Booking.query.get_or_404(booking_id)
    
    # Security check to ensure valid status updates
    valid_statuses = ['pending', 'confirmed', 'checked_out', 'cancelled']
    
    if status in valid_statuses:
        booking.status = status
        
        # SMART LOGIC: Auto-update the physical room status based on the booking!
        if status in ['checked_out', 'cancelled']:
            booking.room.status = 'available' # Free the room up!
        elif status == 'confirmed':
            booking.room.status = 'occupied' # Lock the room down!
            
        db.session.commit()
        flash(f'Transaction #{booking.id} updated to {status.upper()} successfully.', 'success')
    else:
        flash('Invalid status command.', 'error')
        
    return redirect(url_for('admin.manage_bookings'))

# --- REVIEW MODERATION SYSTEM ---

@admin_bp.route('/reviews')
@login_required
@admin_required
def manage_reviews():
    # Fetch all reviews, newest first
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=reviews)

@admin_bp.route('/reviews/<int:review_id>/<string:action>')
@login_required
@admin_required
def moderate_review(review_id, action):
    review = Review.query.get_or_404(review_id)
    
    # Security check to ensure valid actions
    if action in ['published', 'hidden']:
        review.status = action
        db.session.commit()
        flash(f'System Update: Review #{review.id} is now {action.upper()}.', 'success')
    else:
        flash('System Error: Invalid moderation action.', 'error')
        
    return redirect(url_for('admin.manage_reviews'))

# --- BUSINESS ANALYTICS ENGINE ---

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # 1. Calculate Total Revenue (Only count 'confirmed' or 'checked_out' money)
    revenue_query = db.session.query(func.sum(Booking.total_amount)).filter(
        Booking.status.in_(['confirmed', 'checked_out'])
    ).scalar()
    total_revenue = float(revenue_query) if revenue_query else 0.0
    
    # 2. Calculate Total VAT (Tax) Collected
    tax_query = db.session.query(func.sum(Booking.tax_amount)).filter(
        Booking.status.in_(['confirmed', 'checked_out'])
    ).scalar()
    total_tax = float(tax_query) if tax_query else 0.0

    # 3. Calculate Current Occupancy Rate
    total_rooms = Room.query.count()
    occupied_rooms = Room.query.filter_by(status='occupied').count()
    
    if total_rooms > 0:
        occupancy_rate = round((occupied_rooms / total_rooms) * 100, 1)
    else:
        occupancy_rate = 0.0

    return render_template(
        'admin/analytics.html', 
        revenue=total_revenue, 
        tax=total_tax, 
        occupancy=occupancy_rate, 
        occupied_rooms=occupied_rooms, 
        total_rooms=total_rooms
    )
    
    # --- SYSTEM SECURITY & PERSONNEL MANAGEMENT ---

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    # Fetch all users EXCEPT the currently logged-in one (so you don't accidentally archive yourself!)
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:target_id>/<string:action>')
@login_required
@admin_required
def modify_user(target_id, action):
    target_user = User.query.get_or_404(target_id)
    
    # 1. CLEARANCE CHECK: Admins cannot modify Super Admins
    if current_user.role == 'admin' and target_user.role == 'super_admin':
        flash('Security Violation: Insufficient clearance to modify a Super Administrator.', 'error')
        return redirect(url_for('admin.manage_users'))

    # 2. ARCHIVE / RESTORE LOGIC (Soft Delete)
    if action == 'archive':
        target_user.is_archived = True
        flash(f'Directive Executed: Account {target_user.email} has been securely archived.', 'success')
    elif action == 'restore':
        target_user.is_archived = False
        flash(f'Directive Executed: Account {target_user.email} access restored.', 'success')
        
    # 3. PROMOTION / DEMOTION LOGIC
    elif action == 'promote_staff':
        target_user.role = 'staff'
        flash(f'Account {target_user.email} upgraded to STAFF.', 'success')
    elif action == 'promote_admin':
        # Only Super Admins can create other Admins!
        if current_user.role != 'super_admin':
            flash('Security Violation: Only Super Admins can authorize new Administrator credentials.', 'error')
            return redirect(url_for('admin.manage_users'))
        target_user.role = 'admin'
        flash(f'Account {target_user.email} upgraded to ADMIN.', 'success')
    elif action == 'demote_user':
        target_user.role = 'user'
        flash(f'Account {target_user.email} demoted to standard user.', 'success')
    else:
        flash('System Error: Invalid command parameter.', 'error')

    db.session.commit()
    return redirect(url_for('admin.manage_users'))