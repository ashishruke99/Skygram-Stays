from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import Config
from forms import VillaForm
from models import db, Villa, Photo
from models import db, Property, PropertyImage, Amenity, MealOption, Room, FAQ, DailyPrice, Review
import sqlite3
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import razorpay
import psycopg2
from flask_mail import Mail, Message
from sqlalchemy import or_
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5 GB
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customer_villa.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # For flash messages

load_dotenv(dotenv_path='security/.env')
# Configure the mail server using environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'

mail = Mail(app)
db.init_app(app)
#Creating Data Base
def init_db():
    with app.app_context():
        # SQLAlchemy database for villas and photos
        db.init_app(app)
        db.create_all()

    #User Information (Login)
    # SQLite database for users and plans
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            dob TEXT,
            password TEXT,
            roSle TEXT
        )
    ''')
    conn.commit()
    conn.close()
    

    #Pop Form Information
    conn = sqlite3.connect('info.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            mobile TEXT NOT NULL,
            place_to_visit TEXT NOT NULL,
            check_in_date DATE NOT NULL,
            check_out_date DATE NOT NULL,
            adults INTEGER NOT NULL,
            children INTEGER NOT NULL,
            infants INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Razorpay API keys
RAZORPAY_KEY_ID = 'rzp_test_HOusTnQDlShkjm'
RAZORPAY_KEY_SECRET = 'rTcwFAH7dPhlzCBfB2pejgRl'

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

from functools import wraps
from flask import session, redirect, url_for, request

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

#Main Page
@app.route('/')
def home():
    return redirect(url_for('Customer_properties'))

#page 1
@app.route('/explore')
def explore():
    return render_template('explore.html', role='user')

#page 2
@app.route('/our_destination')
def our_destination():
    return render_template('our_destination.html', role='user')

#page 2- pop form box
@app.route('/submit', methods=['POST'])
def submit():
    try:
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            mobile = request.form['mobile']
            place = request.form['place']
            checkin = request.form['checkin']
            checkout = request.form['checkout']
            adults = int(request.form['guest_adults'])
            children = int(request.form['guest_children'])
            infants = int(request.form['guest_infants'])

            conn = sqlite3.connect('info.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO plans (name, email, mobile, place, checkin, checkout, adults, children, infants)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, mobile, place, checkin, checkout, adults, children, infants))
            conn.commit()
            conn.close()
            
            return jsonify(status='OK')
    except Exception as e:
        return jsonify(status='Error', message=str(e))

#page 2 - pop display in admin section
@app.route('/view')
def view():
    conn = sqlite3.connect('info.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plans')
    plans = cursor.fetchall()
    conn.close()
    return render_template('view.html', plans=plans)

#Page 3 
@app.route('/list_your_property', methods=['GET', 'POST'])
def list_your_property():
    form = VillaForm()
    if form.validate_on_submit():
        try:
            new_villa = Villa(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                phone=form.phone.data,
                location=form.location.data,
                property_type=form.property_type.data,
                rooms=form.rooms.data,
                heard_about=form.heard_about.data,
                description=form.description.data,
                link=form.link.data
            )
            db.session.add(new_villa)
            db.session.commit()

            # Save photos
            if form.photos.data:
                photo_file = form.photos.data
                filename = os.path.join(app.config['UPLOADS_DEFAULT_DEST'], photo_file.filename)
                photo_file.save(filename)
                new_photo = Photo(filename=photo_file.filename, villa_id=new_villa.id)
                db.session.add(new_photo)
                db.session.commit()

            return redirect(url_for('list_your_property'))
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')

    villas = Villa.query.order_by(Villa.timestamp.desc()).all()
    return render_template('list_your_property.html', form=form, villas=villas, role='user')

@app.route('/delete_villa', methods=['POST'])
def delete_villa():
    if request.method == 'POST':
        villa_id = request.form.get('villa_id')
        villa = Villa.query.get(villa_id)
        if villa:
            try:
                db.session.delete(villa)
                db.session.commit()
                return jsonify(status='success', message='Villa deleted successfully'), 200
            except Exception as e:
                db.session.rollback()
                return jsonify(status='error', message=str(e)), 500
        else:
            return jsonify(status='error', message='Villa not found'), 404

    return jsonify(status='error', message='Invalid request method'), 405

#display properies in admin Section as container
@app.route('/properties')
def view_properties():
    villas = Villa.query.all()
    if not villas:
        flash('No properties found.')
    else:
        for villa in villas:
            print(villa)  # Log the villas for debugging
    return render_template('properties.html', villas=villas)

#Display single properties  of new customer in single page
@app.route('/property/<int:villa_id>')
def view_property(villa_id):
    villa = Villa.query.get_or_404(villa_id)
    return render_template('property_detail.html', villa=villa)

#page 4
@app.route('/about_us')
def about_us():
    return render_template('about_us.html', role='user')

#Page 5
@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html', role='user')

#Page 6 login form

@app.route('/check_login_status', methods=['GET'])
def check_login_status():
    if 'user_id' in session:
        return jsonify({"logged_in": True})
    else:
        return jsonify({"logged_in": False})

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
            user = c.fetchone()
            if user:
                session['user_id'] = user[0]
                session['first_name'] = user[1]
                session['last_name'] = user[2]
                session['role'] = user[7]  # Role is stored in the 8th column (index 7)
                next_url = request.args.get('next')
                if next_url:
                    return redirect(next_url)
                if session['role'] == "user":
                    return redirect(url_for('Customer_properties'))
                elif session['role'] == "admin":
                    return redirect(url_for('admin_dashboard'))
            else:
                error = 'Invalid email or password.'

    return render_template('login.html', error=error)

# page 6 logout form
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('first_name', None)
    session.pop('last_name', None)
    return redirect(url_for('Customer_properties'))

#login admin Section
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    search_key = request.form.get('search_key', '').strip() if request.method == 'POST' else ''
    
    query_user = "SELECT * FROM users WHERE role='user'"
    params_user = ()

    if search_key:
        query_user += " AND (first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ? OR dob LIKE ?)"
        params_user = tuple(['%' + search_key + '%'] * 5)

    query_guest = "SELECT * FROM plans"
    params_guest = ()

    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute(query_user, params_user)
        customers = c.fetchall()

    with sqlite3.connect('info.db') as conn:
        c = conn.cursor()
        c.execute(query_guest, params_guest)
        guest_customers = c.fetchall()

    villas = Villa.query.all()  # Fetch villas from the database
    properties = db.session.query(Property).all()
    # Handle POST request for updating price
    if request.method == 'POST':
        try:
            property_id = request.form['property_id']
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            new_price = request.form['new_price']
            
            daily_price = db.session.query(DailyPrice).filter_by(property_id=property_id, date=date).first()
            if daily_price:
                daily_price.price = new_price
            else:
                daily_price = DailyPrice(property_id=property_id, date=date, price=new_price)
                db.session.add(daily_price)
            db.session.commit()
            flash('Price updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", 'error')

    return render_template('admin_dashboard.html', customers=customers, search_key=search_key, guest_customers=guest_customers, villas=villas,properties=properties)

#user create account
@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        first_name = request.form.get('first_name').capitalize()
        last_name = request.form.get('last_name').capitalize()
        email = request.form.get('email')
        phone = request.form.get('phone')
        dob = request.form.get('dob')
        password = request.form.get('password')
        re_password = request.form.get('re_password')

        if not (first_name.isalpha() and last_name.isalpha()):
            error = 'First and last names must contain only alphabetic characters.'
            return render_template('create_account.html', error=error)

        if len(phone) != 10 or not phone.isdigit():
            error = 'Phone number must be 10 digits.'
            return render_template('create_account.html', error=error)

        if password != re_password:
            error = 'Passwords do not match.'
            return render_template('create_account.html', error=error)

        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO users (first_name, last_name, email, phone, dob, password, role)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (first_name, last_name, email, phone, dob, password, "user"))
                conn.commit()
                success_message = f'{first_name} {last_name}, your account has been created successfully!'
                return render_template('create_account.html', success_message=success_message)
            except sqlite3.IntegrityError as e:
                if "email" in str(e):
                    error = 'Email already exists.'
                elif "phone" in str(e):
                    error = 'Phone number already exists.'
                else:
                    error = 'An error occurred. Please try again.'
                return render_template('create_account.html', error=error)

    return render_template('create_account.html')

@app.route('/submitP', methods=['POST'])
def submitP():
    if request.method == 'POST':
        try:
            amenities = [
    ('tv', request.form.get('amenities_tv')),
    ('toiletries', request.form.get('amenities_toiletries')),
    ('wardrobe', request.form.get('amenities_wardrobe')),
    ('ac', request.form.get('amenities_ac')),
    ('balcony', request.form.get('amenities_balcony')),
    ('bar', request.form.get('amenities_bar')),
    ('bathtub', request.form.get('amenities_bathtub')),
    ('bbq', request.form.get('amenities_bbq')),
    ('bluetooth-speaker', request.form.get('amenities_bluetooth-speaker')),
    ('bonfire', request.form.get('amenities_bonfire')),
    ('cctv-exterior', request.form.get('amenities_cctv-exterior')),
    ('cctv-interior', request.form.get('amenities_cctv-interior')),
    ('driver-staff-stay', request.form.get('amenities_driver-staff-stay')),
    ('extra-mattress', request.form.get('amenities_extra-mattress')),
    ('fire-extinguisher', request.form.get('amenities_fire-extinguisher')),
    ('gazebo', request.form.get('amenities_gazebo')),
    ('hair-dryer', request.form.get('amenities_hair-dryer')),
    ('heater', request.form.get('amenities_heater')),
    ('indoor-games', request.form.get('amenities_indoor-games')),
    ('jacuzzi', request.form.get('amenities_jacuzzi')),
    ('lawn', request.form.get('amenities_lawn')),
    ('mini-fridge', request.form.get('amenities_mini-fridge')),
    ('music-system', request.form.get('amenities_music-system')),
    ('outdoor-games', request.form.get('amenities_outdoor-games')),
    ('parking', request.form.get('amenities_parking')),
    ('pet-friendly', request.form.get('amenities_pet-friendly')),
    ('private-pool', request.form.get('amenities_private-pool')),
    ('projector', request.form.get('amenities_projector')),
    ('refrigerator', request.form.get('amenities_refrigerator')),
    ('towels', request.form.get('amenities_towels')),
    ('water-purifier', request.form.get('amenities_water-purifier')),
    ('wheelchair-friendly', request.form.get('amenities_wheelchair-friendly')),
    ('wifi', request.form.get('amenities_wifi')),
    ('workstation', request.form.get('amenities_workstation')),
    ('chef', request.form.get('amenities_chef')),
    ('first-aid', request.form.get('amenities_first-aid')),
    ('fresh-linens', request.form.get('amenities_fresh-linens')),
    ('genset-backup', request.form.get('amenities_genset-backup')),
    ('inverter-backup', request.form.get('amenities_inverter-backup')),
    ('ironing-board', request.form.get('amenities_ironing-board')),
    ('karaoke', request.form.get('amenities_karaoke')),
    ('kitchen-access', request.form.get('amenities_kitchen-access')),
    ('lift', request.form.get('amenities_lift')),
    ('lockers', request.form.get('amenities_lockers')),
    ('mobile-network', request.form.get('amenities_mobile-network')),
    ('mobile', request.form.get('amenities_mobile')),
    ('volleyball', request.form.get('amenities_volleyball'))
]

            property_name = request.form['property_name']
            location = request.form['location']
            guest_capacity = request.form['guest_capacity']
            room_count = request.form['room_count']
            baths = request.form['baths']
            rating = request.form['rating']
            rule = request.form['rule']
            great_for = request.form['great_for']
            price = request.form['price']
            highlights = request.form['highlights']
            location_description = request.form['location_description']
            location_link = request.form['location_link']
            cover_photo = request.files['cover_photo']

            if 'cover_photo' not in request.files or cover_photo.filename == '':
                flash('No cover photo uploaded', 'error')
                return redirect(url_for('our_destination'))

            cover_photo_filename = secure_filename(cover_photo.filename)
            cover_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_photo_filename))

            new_property = Property(
                property_name=property_name,
                location=location,
                guest_capacity=guest_capacity,
                room_count=room_count,
                baths=baths,
                rating=rating,
                rule=rule,
                great_for=great_for,
                price=price,
                highlights=highlights,
                cover_photo=cover_photo_filename,
                location_description=location_description,
                location_link=location_link
            )
            db.session.add(new_property)
            db.session.commit()

            for image in request.files.getlist('images'):
                if image.filename != '':
                    image_filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                    new_image = PropertyImage(property_id=new_property.id, image_file=image_filename)
                    db.session.add(new_image)

            for amenity_name, amenity_status in amenities:
                if amenity_status:  # Check if a status was selected
                    amenity_icon_path = f'icon/{amenity_name}.webp'
                    new_amenity = Amenity(
                        property_id=new_property.id,
                        name=amenity_name,
                        icon=amenity_icon_path,
                        status=amenity_status
                    )
                    db.session.add(new_amenity)

            for meal_image in request.files.getlist('meal_images'):
                if meal_image.filename != '':
                    meal_image_filename = secure_filename(meal_image.filename)
                    meal_image.save(os.path.join(app.config['UPLOAD_FOLDER'], meal_image_filename))
                    meal_description = request.form['meal_description']
                    new_meal = MealOption(property_id=new_property.id, image_file=meal_image_filename, description=meal_description)
                    db.session.add(new_meal)

            room_photos = request.files.getlist('room_photos')
            room_descriptions = request.form.getlist('room_descriptions')

            for photo, description in zip(room_photos, room_descriptions):
                if photo.filename != '':
                    room_photo_filename = secure_filename(photo.filename)
                    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], room_photo_filename))
                    new_room = Room(property_id=new_property.id, room_photo=room_photo_filename, room_description=description)
                    db.session.add(new_room)

            faq_questions = request.form.getlist('faq_question')
            faq_answers = request.form.getlist('faq_answer')

            for question, answer in zip(faq_questions, faq_answers):
                new_faq = FAQ(property_id=new_property.id, question=question, answer=answer)
                db.session.add(new_faq)

                        # Handle multiple reviews
            user_names = request.form.getlist('user_name[]')
            comments = request.form.getlist('comment[]')
            ratings = request.form.getlist('rating[]')
            for user_name, comment, rating in zip(user_names, comments, ratings):
                new_review = Review(
                    property_id=new_property.id,
                    user_name=user_name,
                    comment=comment,
                    rating=rating
                )
                db.session.add(new_review)

            db.session.commit()
            flash('Property added successfully!', 'success')
            return redirect(url_for('Customer_properties'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", 'error')
            return redirect(url_for('admin_dashboard'))
        
@app.route('/edit_property', methods=['GET', 'POST'])
def edit_property():
    properties = Property.query.all()
    selected_property = None

    if request.method == 'POST':
        selected_property_id = request.form.get('property_id')
        if selected_property_id:
            selected_property = Property.query.get(selected_property_id)
            if 'update_property' in request.form:
                # Handle the update of the selected property
                selected_property.property_name = request.form['property_name']
                selected_property.location = request.form['location']
                selected_property.guest_capacity = request.form['guest_capacity']
                selected_property.room_count = request.form['room_count']
                selected_property.baths = request.form['baths']
                selected_property.rating = request.form['rating']
                selected_property.rule = request.form['rule']
                selected_property.great_for = request.form['great_for']
                selected_property.price = request.form['price']
                selected_property.highlights = request.form['highlights']
                selected_property.location_description = request.form['location_description']
                selected_property.location_link = request.form['location_link']

                # Handle cover photo update if needed
                if 'cover_photo' in request.files and request.files['cover_photo'].filename != '':
                    cover_photo = request.files['cover_photo']
                    cover_photo_filename = secure_filename(cover_photo.filename)
                    cover_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_photo_filename))
                    selected_property.cover_photo = cover_photo_filename

                db.session.commit()
                flash('Property updated successfully!', 'success')
                return redirect(url_for('edit_property'))
            

    return render_template('edit_property.html', properties=properties, selected_property=selected_property)


@app.route('/Customer_properties', methods=['GET', 'POST'])
def Customer_properties():
    # Initialize properties query  
    properties_query = Property.query

        # Filter by price ranges (checkboxes)
    price_ranges = request.args.getlist('price_range')
    if price_ranges:
        price_filters = []
        for price_range in price_ranges:
            min_range, max_range = map(int, price_range.split('-'))
            price_filters.append(Property.price.between(min_range, max_range))
        properties_query = properties_query.filter(or_(*price_filters))

    # Filter by price range
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    if min_price is not None and max_price is not None:
        properties_query = properties_query.filter(Property.price.between(min_price, max_price))

    # Filter by room count
    room_count = request.args.get('room_count', type=int)
    if room_count:
        properties_query = properties_query.filter(Property.room_count >= room_count)

    # Filter by available amenities
    amenities_filters = []
    
    if request.args.get('amenities_tv') == 'available':
        amenities_filters.append(or_(Amenity.name == 'TV', Amenity.status == 'available'))
    if request.args.get('amenities_wifi') == 'available':
        amenities_filters.append(or_(Amenity.name == 'Wi-Fi', Amenity.status == 'available'))
    
    # Apply amenities filter if any are selected
    if amenities_filters:
        properties_query = properties_query.filter(
            Property.amenities.any(*amenities_filters)
        )

    # Execute the query to get the properties
    properties = properties_query.all()

    # Filter by location
    location_filter = request.args.get('location', 'ALL')
    if location_filter != 'ALL':
        properties_query = properties_query.filter(Property.location == location_filter)

    # Execute the query to get the properties
    properties = properties_query.all()

    # Handle POST request for updating price
    if request.method == 'POST':
        try:
            property_id = request.form['property_id']
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            new_price = request.form['new_price']
            
            daily_price = db.session.query(DailyPrice).filter_by(property_id=property_id, date=date).first()
            if daily_price:
                daily_price.price = new_price
            else:
                daily_price = DailyPrice(property_id=property_id, date=date, price=new_price)
                db.session.add(daily_price)
            db.session.commit()
            flash('Price updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", 'error')
    
    return render_template('Customer_properties.html', properties=properties)

@app.route('/villa/<int:property_id>')
def villa(property_id):
    property = db.session.get(Property, property_id)
    return render_template('villa.html', property=property, key=RAZORPAY_KEY_ID)

@app.route('/edit_prices')
def edit_prices():
    properties = db.session.query(Property).all()
    return render_template('edit_prices.html', properties=properties)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    # Handle the webhook data here
    # Validate webhook signature if needed
    return jsonify({'status': 'success'})

@app.route('/get_prices')
def get_prices():
    property_id = request.args.get('property_id')
    property = db.session.get(Property, property_id)
    if not property:
        return jsonify({'status': 'error', 'message': 'Property not found'}), 404

    base_price = property.price
    daily_prices = db.session.query(DailyPrice).filter_by(property_id=property_id).all()
    booked_dates = [price.date.strftime('%Y-%m-%d') for price in daily_prices if price.price == 0]  # Assuming price of 0 indicates a booking

    price_dict = {price.date.strftime('%Y-%m-%d'): price.price for price in daily_prices}

    return jsonify({'base_price': base_price, 'daily_prices': price_dict, 'booked_dates': booked_dates})

@app.route('/update_price', methods=['POST'])
def update_price():
    data = request.get_json()
    property_id = data['property_id']
    date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    new_price = data['new_price']

    daily_price = db.session.query(DailyPrice).filter_by(property_id=property_id, date=date).first()
    if daily_price:
        daily_price.price = new_price
    else:
        daily_price = DailyPrice(property_id=property_id, date=date, price=new_price)
        db.session.add(daily_price)
    
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/calculate_total', methods=['POST'])
def calculate_total():
    data = request.json
    property_id = data['property_id']
    check_in_date = datetime.strptime(data['check_in_date'], '%Y-%m-%d').date()
    check_out_date = datetime.strptime(data['check_out_date'], '%Y-%m-%d').date()
    
    daily_prices = db.session.query(DailyPrice).filter(
        DailyPrice.property_id == property_id,
        DailyPrice.date >= check_in_date,
        DailyPrice.date < check_out_date
    ).all()
    
    base_price = db.session.get(Property, property_id).price
    total_amount = 0

    for single_date in (check_in_date + timedelta(days=n) for n in range((check_out_date - check_in_date).days)):
        daily_price = next((dp for dp in daily_prices if dp.date == single_date), None)
        if daily_price:
            total_amount += daily_price.price
        else:
            total_amount += base_price
    
    # Add GST and Service Charge
    gst = total_amount * 0.18
    service_charge = total_amount * 0.05
    total_amount += gst + service_charge
    
    return jsonify({"status": "success", "total_amount": total_amount})

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/charge', methods=['POST'])
def charge():
    try:
        data = request.json
        payment_id = data['razorpay_payment_id']
        property_id = data['property_id']
        check_in_date = datetime.strptime(data['check_in_date'], '%Y-%m-%d').date()
        check_out_date = datetime.strptime(data['check_out_date'], '%Y-%m-%d').date()
        user_name = data['name']
        user_email = data['email']

        property = db.session.get(Property, property_id)
        property_name = property.property_name
        location = property.location
        guest_count=property.guest_capacity

        # Calculate the total amount
        daily_prices = db.session.query(DailyPrice).filter(
            DailyPrice.property_id == property_id,
            DailyPrice.date >= check_in_date,
            DailyPrice.date < check_out_date
        ).all()
        
        base_price = db.session.get(Property, property_id).price
        total_amount = 0

        for single_date in (check_in_date + timedelta(days=n) for n in range((check_out_date - check_in_date).days)):
            daily_price = next((dp for dp in daily_prices if dp.date == single_date), None)
            if daily_price:
                total_amount += daily_price.price
            else:
                total_amount += base_price

        # Add GST and Service Charge
        gst = total_amount * 0.13
        service_charge = total_amount * 0.05
        total_amount += gst + service_charge

        amount = total_amount * 100  # Amount in paisa (1 rupee = 100 paisa)

        # Process the payment with Razorpay (omitting payment confirmation for brevity)

        # Store the booking
        for single_date in (check_in_date + timedelta(days=n) for n in range((check_out_date - check_in_date).days)):
            daily_price = db.session.query(DailyPrice).filter_by(property_id=property_id, date=single_date).first()
            if daily_price:
                daily_price.price = 0  # Set price to 0 to indicate booking
            else:
                daily_price = DailyPrice(property_id=property_id, date=single_date, price=0)
                db.session.add(daily_price)
        db.session.commit()
        
        
        # Send confirmation email
         # Send confirmation email
        msg = Message(
            subject=f"Booking Confirmation - Welcome to {property_name}!",
            sender='your-email@example.com',
            recipients=[user_email]
        )

# HTML email body with multiple inline images
        msg.html = f"""
        <p>Dear {user_name},</p>

        <p>Thank you for choosing to stay with us at <b>{property_name}</b>! We are delighted to confirm your booking and look forward to hosting you.</p>

        <p><b>Booking Details:</b><br>
        <b>Guest Name:</b> {user_name}<br>
        <b>Property:</b> {property_name}<br>
        <b>Location:</b> {location}<br>
        <b>Check-in Date:</b> {check_in_date}<br>
        <b>Check-out Date:</b> {check_out_date}<br>
        <b>Total Amount:</b> INR {total_amount}</p>



        <p><b>Important Information:</b><br>
        <b>Check-in Time:</b> 2:00 PM<br>
        <b>Check-out Time:</b> 11:00 AM<br>
        <b>Meals:</b> Can be arranged at an additional cost.</p>

        <p>If you have any special requests or need further assistance, please don’t hesitate to reach out to us. We want to ensure your stay is as comfortable and enjoyable as possible.</p>

        <p>We can't wait to welcome you to <b>{property_name}</b> and hope you have a memorable stay!</p>

        <p>Warm regards,<br>
        Team SkyGram Stays<br>
        +91 92267 84221<br>
        3rd Floor, Business Court,<br>
        Mukund Nagar, Pune, Maharashtra 411037</p>
        """

        mail.send(msg)

        return jsonify({"status": "Payment successful"})

    except Exception as e:
        # Handle exceptions
        return jsonify({"status": "Payment failed", "error": str(e)}), 500

@app.route('/favorites')
def favorites():
    favorite_properties = Property.query.filter(Property.id.in_(session.get('favorites', []))).all()
    return render_template('favorites.html', properties=favorite_properties)

@app.route('/toggle-favorite', methods=['POST'])
def toggle_favorite():
    data = request.get_json()
    property_id = data['property_id']

    if 'favorites' not in session:
        session['favorites'] = []

    if property_id in session['favorites']:
        session['favorites'].remove(property_id)
    else:
        session['favorites'].append(property_id)

    session.modified = True
    return jsonify(success=True)

@app.route('/gallery/<int:property_id>')
def gallery(property_id):
    property = Property.query.get_or_404(property_id)
    return render_template('gallery.html', property=property)

@app.route('/delete_property', methods=['GET', 'POST'])
def delete_property():
    if request.method == 'POST':
        try:
            property_id = request.form['property_id']
            property_to_delete = db.session.get(Property, property_id)
            if property_to_delete:
                db.session.delete(property_to_delete)
                db.session.commit()
                flash('Property deleted successfully!', 'success')
            else:
                flash('Property not found!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", 'error')
        return redirect(url_for('delete_property'))

    properties = db.session.query(Property).all()
    return render_template('delete_property.html', properties=properties)

@app.route('/get_user_details', methods=['GET'])
def get_user_details():
    if 'user_id' in session:
        user_id = session['user_id']
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute("SELECT first_name, last_name, email, phone FROM users WHERE id=?", (user_id,))
            user = c.fetchone()
            if user:
                return jsonify({
                    "status": "success",
                    "first_name": user[0],
                    "last_name": user[1],
                    "email": user[2],
                    "phone": user[3]
                })
    return jsonify({"status": "error", "message": "User not logged in"})

@app.route('/user_bookings')
def user_bookings():
    if 'user_id' in session:
        user_id = session['user_id']
        with sqlite3.connect('bookings.db') as conn:
            c = conn.cursor()
            c.execute("""
                SELECT villa_name, check_in_date, check_out_date
                FROM bookings
                WHERE user_id = ?
            """, (user_id,))
            bookings = c.fetchall()
            bookings_list = [{'villa_name': b[0], 'check_in_date': b[1], 'check_out_date': b[2]} for b in bookings]
            return render_template('user_bookings.html', bookings=bookings_list)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        dob = request.form.get('dob')
        password = request.form.get('password')
        role = request.form.get('role')

        # Insert the new user into the database
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO users (first_name, last_name, email, phone, dob, password, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (first_name, last_name, email, phone, dob, password, role))
            conn.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


if __name__ == '__main__':
    init_db()  # Ensure the database is initialized
    app.run(debug=True)
