from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime
from app.models import RoomType, Room, Booking
from app import db
from app import os
from werkzeug.utils import secure_filename

# Create the User blueprint
user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/book/<int:room_type_id>', methods=['GET', 'POST'])
@login_required # Security: Only logged-in users can book!
def book_room(room_type_id):
    # Fetch the specific room type they clicked on
    room_type = RoomType.query.get_or_404(room_type_id)
    
    if request.method == 'POST':
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        
        # Convert the HTML string dates into Python Date objects
        date_format = "%Y-%m-%d"
        ci_date = datetime.strptime(check_in, date_format).date()
        co_date = datetime.strptime(check_out, date_format).date()
        
        # 1. Calculate Total Days
        delta = co_date - ci_date
        days = delta.days
        
        if days <= 0:
            flash("System Error: Check-out date must be AFTER check-in date.", "error")
            return redirect(url_for('user.book_room', room_type_id=room_type_id))
            
        # 2. Find an available physical room of this exact type
        available_room = Room.query.filter_by(room_type_id=room_type_id, status='available').first()
        
        if not available_room:
            flash("Critcal: No physical rooms of this classification are currently available.", "error")
            return redirect(url_for('public.index'))
            
        # 3. Calculate Financials (Base * Days + 12% Tax)
        total_room_cost = float(room_type.base_price) * days
        tax_amount = total_room_cost * 0.12 
        final_total = total_room_cost + tax_amount
        
        # 4. Save the Booking to monster_db
        new_booking = Booking(
            user_id=current_user.id,
            room_id=available_room.id,
            check_in_date=ci_date,
            check_out_date=co_date,
            total_amount=final_total,
            tax_amount=tax_amount,
            status='pending'
        )
        
        # Optional: Change room status to occupied (we will make this more advanced later)
        available_room.status = 'occupied'
        
        db.session.add(new_booking)
        db.session.commit()
        
        flash(f"Transaction Secured! Total Amount: ₱{final_total:,.2f}", "success")
        return redirect(url_for('public.index'))
        
    return render_template('user/book_room.html', room_type=room_type)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # Fetch all bookings for the currently logged-in user, newest first!
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    
    return render_template('user/dashboard.html', bookings=bookings)

from app.models import Review # Add this to your imports at the top if it's not there!

# --- GUEST FEEDBACK SYSTEM ---

@user_bp.route('/review/<int:room_type_id>', methods=['GET', 'POST'])
@login_required
def leave_review(room_type_id):
    room_type = RoomType.query.get_or_404(room_type_id)
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        # --- IMAGE UPLOAD LOGIC ---
        image_file = request.files.get('review_image') # Grab the file
        db_image_path = None # Default to None if they didn't upload anything
        
        if image_file and image_file.filename != '':
            # 1. Clean the filename
            filename = secure_filename(image_file.filename)
            
            # 2. BULLETPROOF PATH: Find the exact absolute path to your static folder
            upload_folder = os.path.join(current_app.root_path, 'static', 'img', 'reviews')
            
            # 3. AUTO-CREATE FOLDER: If the folder doesn't exist, Python will build it right now!
            os.makedirs(upload_folder, exist_ok=True)
            
            # 4. Define the final save path and save the file
            upload_path = os.path.join(upload_folder, filename)
            image_file.save(upload_path)
            
            # 5. Save the relative path for the database so HTML can read it later
            db_image_path = f"img/reviews/{filename}"
            
        # Create the review object with the image path!
        new_review = Review(
            user_id=current_user.id,
            room_type_id=room_type.id,
            rating=int(rating),
            comment=comment,
            image_url=db_image_path, # Saves the path to monster_db
            status='pending' 
        )
        
        db.session.add(new_review)
        db.session.commit()
        
        flash('Review and media submitted successfully! Pending Admin approval.', 'success')
        return redirect(url_for('user.dashboard'))
        
    return render_template('user/leave_review.html', room_type=room_type)