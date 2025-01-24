from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import qrcode
import os
import uuid
from datetime import datetime , date
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_tracking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Blockchain server configuration
BLOCKCHAIN_SERVER_URL = 'http://10.1.51.217:5000'

# Initialize Extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


MEDICINE_TYPES = [
    'Analgesics', 
    'Antibiotics', 
    'Anticonvulsants', 
    'Antidepressants', 
    'Antihistamines', 
    'Antihypertensives', 
    'Anti-inflammatories', 
    'Antipyretics', 
    'Antifungals', 
    'Antiemetics', 
    'Antacids'
]

MEDICINE_FORMS = [
    'Tablets', 
    'Capsules', 
    'Topical medicines', 
    'Suppositories', 
    'Inhalers', 
    'Transdermal patches', 
    'Sublingual medicines', 
    'Injections'
]


# Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    batch_id = db.Column(db.String(50), unique=True, nullable=False)
    qr_code_path = db.Column(db.String(200), nullable=False)
    manufacturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # New fields
    product_id = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    medicine_type = db.Column(db.String(50), nullable=False)
    medicine_form = db.Column(db.String(50), nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    dosage = db.Column(db.String(100), nullable=True)
    side_effects = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TransportTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    tracking_status = db.Column(db.String(50), nullable=False)
    current_location = db.Column(db.String(200))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    transport_conditions = db.Column(db.Text)
    expected_delivery_date = db.Column(db.Date)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PharmacyInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    batch_id = db.Column(db.String(50), db.ForeignKey('product.batch_id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Received')  # Status: Received, Stocked, Sold, etc.
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function: Generate QR Code
def generate_qr_code(batch_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"http://10.1.51.217:8080/track/{batch_id}")
    qr.make(fit=True)
    qr_code_path = os.path.join('static/qr_codes', f"{batch_id}.png")
    os.makedirs(os.path.dirname(qr_code_path), exist_ok=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_code_path)
    return qr_code_path

# Blockchain integration helpers
def add_to_blockchain(transaction_type, batch_id, product_data, status=None, updated_by=None):
    transaction = {
        'type': transaction_type,
        'batch_id': batch_id,
        'timestamp': datetime.utcnow().timestamp(),
        'product_data': product_data
    }
    
    if status:
        transaction['status'] = status
    if updated_by:
        transaction['updated_by'] = updated_by

    try:
        response = requests.post(
            f'{BLOCKCHAIN_SERVER_URL}/add_transaction',
            json=transaction
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        flash('Warning: Blockchain server is not accessible', 'warning')
        return False

def get_product_history(batch_id):
    try:
        response = requests.get(f'{BLOCKCHAIN_SERVER_URL}/get_product_history/{batch_id}')
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        flash('Warning: Could not fetch blockchain history', 'warning')
    return []

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        user = User.query.filter_by(email=email, role=role).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            if role == 'manufacturer':
                return redirect(url_for('manufacturer'))
            elif role == 'distributor':
                return redirect(url_for('distributor'))
            elif role == 'pharmacy':
                return redirect(url_for('pharmacy'))
        flash('Invalid credentials or role', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/manufacturer', methods=['GET', 'POST'])
@login_required
def manufacturer():
    if current_user.role != 'manufacturer':
        abort(403)
    if request.method == 'POST':
        name = request.form['name']
        batch_id = str(uuid.uuid4())
        product_id = request.form['product_id']
        description = request.form['description']
        medicine_type = request.form['medicine_type']
        medicine_form = request.form['medicine_form']
        expiration_date = datetime.strptime(request.form['expiration_date'], '%Y-%m-%d').date()
        manufacturing_date = datetime.strptime(request.form['manufacturing_date'], '%Y-%m-%d').date()
        dosage = request.form['dosage']
        side_effects = request.form['side_effects']
        
        qr_code_path = generate_qr_code(batch_id)
        
        # Create product in SQL database
        product = Product(
            name=name, 
            batch_id=batch_id, 
            qr_code_path=qr_code_path, 
            manufacturer_id=current_user.id,
            product_id=product_id,
            description=description,
            medicine_type=medicine_type,
            medicine_form=medicine_form,
            expiration_date=expiration_date,
            manufacturing_date=manufacturing_date,
            dosage=dosage,
            side_effects=side_effects
        )
        db.session.add(product)
        db.session.commit()
        
        # Add to blockchain
        product_data = {
            'name': name,
            'product_id': product_id,
            'manufacturer_id': current_user.id,
            'description': description,
            'medicine_type': medicine_type,
            'medicine_form': medicine_form,
            'expiration_date': expiration_date.isoformat(),
            'manufacturing_date': manufacturing_date.isoformat(),
            'dosage': dosage,
            'side_effects': side_effects,
            'created_at': datetime.utcnow().isoformat()
        }
        add_to_blockchain('product_creation', batch_id, product_data)
        
        flash('Product added and QR code generated!', 'success')
        return redirect(url_for('manufacturer'))
    
    products = Product.query.filter_by(manufacturer_id=current_user.id).all()
    return render_template('manufacturer.html', 
                           products=products, 
                           medicine_types=MEDICINE_TYPES, 
                           medicine_forms=MEDICINE_FORMS)

@app.route('/distributor', methods=['GET', 'POST'])
@login_required
def distributor():
    if current_user.role != 'distributor':
        abort(403)
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        tracking_status = request.form['tracking_status']
        current_location = request.form['current_location']
        temperature = request.form.get('temperature')
        humidity = request.form.get('humidity')
        transport_conditions = request.form.get('transport_conditions')
        expected_delivery_date = request.form.get('expected_delivery_date')
        
        # Ensure product exists
        product = Product.query.get(product_id)
        if product:
            # Add tracking details to the database
            transport_tracking = TransportTracking(
                product_id=product_id,
                tracking_status=tracking_status,
                current_location=current_location,
                temperature=temperature,
                humidity=humidity,
                transport_conditions=transport_conditions,
                expected_delivery_date=datetime.strptime(expected_delivery_date, '%Y-%m-%d') if expected_delivery_date else None,
                updated_by=current_user.id
            )
            db.session.add(transport_tracking)
            db.session.commit()
            
            # Prepare detailed tracking data for blockchain
            tracking_data = {
                'product_id': product_id,
                'status': tracking_status,
                'current_location': current_location,
                'temperature': temperature,
                'humidity': humidity,
                'transport_conditions': transport_conditions,
                'expected_delivery_date': expected_delivery_date
            }
            
            # Add to blockchain
            add_to_blockchain('status_update', product.batch_id, tracking_data, 
                              status=tracking_status, 
                              updated_by=current_user.id)
            
            flash('Product tracking updated successfully and stored in the database!', 'success')
            return redirect(url_for('distributor'))
    
    products = Product.query.all()
    return render_template('distributor.html', products=products)


@app.route('/pharmacy', methods=['GET', 'POST'])
@login_required
def pharmacy():
    if current_user.role != 'pharmacy':
        abort(403)
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        status = request.form['status']
        
        product = Product.query.get(product_id)
        if product:
            product_data = {
                'product_id': product_id,
                'status_update': status
            }
            add_to_blockchain('status_update', product.batch_id, product_data, status, current_user.id)
            flash('Tracking status updated!', 'success')
    
    products = Product.query.all()
    return render_template('pharmacy.html', products=products)

@app.route('/track/<batch_id>')
def track_product(batch_id):
    product = Product.query.filter_by(batch_id=batch_id).first_or_404()
    manufacturer = User.query.get(product.manufacturer_id)
    
    # Get all users to find potential distributors or pharmacies
    distributor = User.query.filter_by(role='distributor').first()
    pharmacy = User.query.filter_by(role='pharmacy').first()
    
    # Get tracking history from blockchain
    history = get_product_history(batch_id)
    
    # Process history to match template expectations
    history_details = []
    for entry in history:
        if entry['type'] in ['product_creation', 'status_update']:
            updated_user = User.query.get(entry.get('updated_by')) if entry.get('updated_by') else None
            history_details.append({
                'status': entry.get('status', 'Product Created'),
                'timestamp': datetime.fromtimestamp(entry['timestamp']),
                'updated_by': updated_user.username if updated_user else 'System'
            })

    return render_template(
        'consumer.html', 
        product=product, 
        manufacturer=manufacturer,
        distributor=distributor,
        pharmacy=pharmacy,
        history=history_details
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080, debug=True)