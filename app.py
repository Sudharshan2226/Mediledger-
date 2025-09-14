from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import qrcode
import os
import uuid
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json
import pandas as pd
from io import BytesIO

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_tracking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Blockchain server configuration
BLOCKCHAIN_SERVER_URL = 'http://127.0.0.1:5000'

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
    company_name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    batch_id = db.Column(db.String(50), unique=True, nullable=False)
    qr_code_path = db.Column(db.String(200), nullable=False)
    manufacturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    medicine_type = db.Column(db.String(50), nullable=False)
    distributor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    medicine_form = db.Column(db.String(50), nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    dosage = db.Column(db.String(100), nullable=True)
    side_effects = db.Column(db.Text, nullable=True)
    storage_conditions = db.Column(db.String(200))
    price = db.Column(db.Float)
    quantity = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Active')

class TransportTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    tracking_status = db.Column(db.String(50), nullable=False)
    current_location = db.Column(db.String(200))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    transport_conditions = db.Column(db.Text)
    expected_delivery_date = db.Column(db.Date)
    actual_delivery_date = db.Column(db.Date)
    carrier = db.Column(db.String(100))
    tracking_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PharmacyInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    batch_id = db.Column(db.String(50), db.ForeignKey('product.batch_id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Received')
    quantity = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float)
    expiry_alert = db.Column(db.Boolean, default=False)
    low_stock_alert = db.Column(db.Boolean, default=False)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def generate_qr_code(batch_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"{BLOCKCHAIN_SERVER_URL}/track/{batch_id}")
    qr.make(fit=True)
    qr_code_path = os.path.join('static/qr_codes', f"{batch_id}.png")
    os.makedirs(os.path.dirname(qr_code_path), exist_ok=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_code_path)
    return qr_code_path

def check_expiry_alerts():
    today = date.today()
    soon_expiring = Product.query.filter(
        Product.expiration_date <= today + timedelta(days=30)
    ).all()
    
    for product in soon_expiring:
        alert = Alert(
            user_id=product.manufacturer_id,
            product_id=product.id,
            type='expiry',
            message=f'Product {product.name} (Batch: {product.batch_id}) will expire on {product.expiration_date}'
        )
        db.session.add(alert)
    db.session.commit()

def check_inventory_alerts():
    low_stock = Product.query.filter(
        Product.quantity <= Product.reorder_level
    ).all()
    
    for product in low_stock:
        alert = Alert(
            user_id=product.manufacturer_id,
            product_id=product.id,
            type='inventory',
            message=f'Low stock alert for {product.name} (Quantity: {product.quantity})'
        )
        db.session.add(alert)
    db.session.commit()

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
        company_name = request.form.get('company_name')
        address = request.form.get('address')
        phone = request.form.get('phone')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role,
            company_name=company_name,
            address=address,
            phone=phone
        )
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
            user.last_login = datetime.utcnow()
            db.session.commit()
            
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

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.company_name = request.form.get('company_name')
        current_user.address = request.form.get('address')
        current_user.phone = request.form.get('phone')
        
        if 'current_password' in request.form and 'new_password' in request.form:
            if check_password_hash(current_user.password, request.form['current_password']):
                current_user.password = generate_password_hash(
                    request.form['new_password'],
                    method='pbkdf2:sha256'
                )
                flash('Password updated successfully!', 'success')
            else:
                flash('Current password is incorrect!', 'danger')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/manufacturer', methods=['GET', 'POST'])
@login_required
def manufacturer():
    if current_user.role != 'manufacturer':
        abort(403)
    
    # Get all distributors
    distributors = User.query.filter_by(role='distributor').all()
    
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
        storage_conditions = request.form.get('storage_conditions')
        price = float(request.form.get('price', 0))
        quantity = int(request.form.get('quantity', 0))
        reorder_level = int(request.form.get('reorder_level', 10))
        distributor_id = int(request.form['distributor_id'])  # New field
        
        qr_code_path = generate_qr_code(batch_id)
        
        product = Product(
            name=name, 
            batch_id=batch_id, 
            qr_code_path=qr_code_path, 
            manufacturer_id=current_user.id,
            distributor_id=distributor_id,  # Add distributor_id
            product_id=product_id,
            description=description,
            medicine_type=medicine_type,
            medicine_form=medicine_form,
            expiration_date=expiration_date,
            manufacturing_date=manufacturing_date,
            dosage=dosage,
            side_effects=side_effects,
            storage_conditions=storage_conditions,
            price=price,
            quantity=quantity,
            reorder_level=reorder_level
        )
        db.session.add(product)
        db.session.commit()
        
        # Add to blockchain
        product_data = {
            'name': name,
            'product_id': product_id,
            'manufacturer_id': current_user.id,
            'distributor_id': distributor_id,  # Add distributor_id
            'description': description,
            'medicine_type': medicine_type,
            'medicine_form': medicine_form,
            'expiration_date': expiration_date.isoformat(),
            'manufacturing_date': manufacturing_date.isoformat(),
            'dosage': dosage,
            'side_effects': side_effects,
            'storage_conditions': storage_conditions,
            'price': price,
            'quantity': quantity,
            'created_at': datetime.utcnow().isoformat()
        }
        add_to_blockchain('product_creation', batch_id, product_data)
        
        flash('Product added and QR code generated!', 'success')
        return redirect(url_for('manufacturer'))
    
    products = Product.query.filter_by(manufacturer_id=current_user.id).all()
    alerts = Alert.query.filter_by(user_id=current_user.id, is_read=False).all()
    
    # Get analytics data
    total_products = len(products)
    active_products = len([p for p in products if p.status == 'Active'])
    low_stock_products = len([p for p in products if p.quantity <= p.reorder_level])
    expiring_soon = len([p for p in products if p.expiration_date <= date.today() + timedelta(days=30)])
    
    return render_template(
        'manufacturer.html',
        products=products,
        distributors=distributors,  # Pass distributors to template
        medicine_types=MEDICINE_TYPES,
        medicine_forms=MEDICINE_FORMS,
        alerts=alerts,
        analytics={
            'total_products': total_products,
            'active_products': active_products,
            'low_stock': low_stock_products,
            'expiring_soon': expiring_soon
        }
    )

@app.route('/distributor', methods=['GET', 'POST'])
@login_required
def distributor():
    if current_user.role != 'distributor':
        abort(403)
    
    # Get all pharmacies
    pharmacies = User.query.filter_by(role='pharmacy').all()
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        tracking_status = request.form['tracking_status']
        current_location = request.form['current_location']
        temperature = request.form.get('temperature')
        humidity = request.form.get('humidity')
        transport_conditions = request.form.get('transport_conditions')
        expected_delivery_date = request.form.get('expected_delivery_date')
        carrier = request.form.get('carrier')
        tracking_number = request.form.get('tracking_number')
        notes = request.form.get('notes')
        pharmacy_id = int(request.form['pharmacy_id'])  # New field
        
        # Update product with pharmacy_id
        product = Product.query.get(product_id)
        if product:
            product.pharmacy_id = pharmacy_id
            
            # Add tracking details
            transport_tracking = TransportTracking(
                product_id=product_id,
                tracking_status=tracking_status,
                current_location=current_location,
                temperature=temperature,
                humidity=humidity,
                transport_conditions=transport_conditions,
                expected_delivery_date=datetime.strptime(expected_delivery_date, '%Y-%m-%d') if expected_delivery_date else None,
                carrier=carrier,
                tracking_number=tracking_number,
                notes=notes,
                updated_by=current_user.id
            )
            db.session.add(transport_tracking)
            db.session.commit()
            
            # Add to blockchain
            tracking_data = {
                'product_id': product_id,
                'pharmacy_id': pharmacy_id,  # Add pharmacy_id
                'status': tracking_status,
                'current_location': current_location,
                'temperature': temperature,
                'humidity': humidity,
                'transport_conditions': transport_conditions,
                'expected_delivery_date': expected_delivery_date,
                'carrier': carrier,
                'tracking_number': tracking_number,
                'notes': notes
            }
            add_to_blockchain('status_update', product.batch_id, tracking_data, status=tracking_status, updated_by=current_user.id)
            
            flash('Product tracking updated successfully!', 'success')
            return redirect(url_for('distributor'))
    
    products = Product.query.filter_by(distributor_id=current_user.id).all()
    tracking_history = TransportTracking.query.all()
    
    # Get analytics data
    total_shipments = len(tracking_history)
    in_transit = len([t for t in tracking_history if t.tracking_status == 'In Transit'])
    delivered = len([t for t in tracking_history if t.tracking_status == 'Delivered'])
    delayed = len([t for t in tracking_history if t.expected_delivery_date and t.expected_delivery_date < date.today()])
    
    return render_template(
        'distributor.html',
        products=products,
        pharmacies=pharmacies,  # Pass pharmacies to template
        tracking_history=tracking_history,
        analytics={
            'total_shipments': total_shipments,
            'in_transit': in_transit,
            'delivered': delivered,
            'delayed': delayed
        }
    )

@app.route('/pharmacy', methods=['GET', 'POST'])
@login_required
def pharmacy():
    if current_user.role != 'pharmacy':
        abort(403)
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        status = request.form['status']
        quantity = int(request.form.get('quantity', 0))
        unit_price = float(request.form.get('unit_price', 0))
        
        product = Product.query.get(product_id)
        if product:
            inventory = PharmacyInventory(
                product_id=product_id,
                batch_id=product.batch_id,
                status=status,
                quantity=quantity,
                unit_price=unit_price,
                updated_by=current_user.id
            )
            db.session.add(inventory)
            
            # Update product quantity
            product.quantity = quantity
            if quantity <= product.reorder_level:
                alert = Alert(
                    user_id=current_user.id,
                    product_id=product_id,
                    type='inventory',
                    message=f'Low stock alert for {product.name}'
                )
                db.session.add(alert)
            
            db.session.commit()
            
            # Add to blockchain
            inventory_data = {
                'product_id': product_id,
                'status': status,
                'quantity': quantity,
                'unit_price': unit_price
            }
            add_to_blockchain('inventory_update', product.batch_id, inventory_data, status, current_user.id)
            
            flash('Inventory updated successfully!', 'success')
            return redirect(url_for('pharmacy'))
    
    products = Product.query.all()
    inventory = PharmacyInventory.query.all()
    alerts = Alert.query.filter_by(user_id=current_user.id, is_read=False).all()
    
    # Get analytics data
    total_inventory = len(inventory)
    low_stock = len([i for i in inventory if i.quantity <= Product.query.get(i.product_id).reorder_level])
    total_value = sum([i.quantity * i.unit_price for i in inventory])
    expiring_soon = len([i for i in inventory if Product.query.get(i.product_id).expiration_date <= date.today() + timedelta(days=30)])
    
    return render_template(
        'pharmacy.html',
        products=products,
        inventory=inventory,
        alerts=alerts,
        analytics={
            'total_inventory': total_inventory,
            'low_stock': low_stock,
            'total_value': total_value,
            'expiring_soon': expiring_soon
        }
    )

@app.route('/track/<batch_id>')
def track_product(batch_id):
    product = Product.query.filter_by(batch_id=batch_id).first_or_404()
    manufacturer = User.query.get(product.manufacturer_id)
    distributor = User.query.filter_by(role='distributor').first()
    pharmacy = User.query.filter_by(role='pharmacy').first()
    # Get tracking history from database
    tracking_logs = TransportTracking.query.filter_by(product_id=product.id).order_by(TransportTracking.updated_at).all()
    
    # Get tracking history from blockchain
    blockchain_history = get_product_history(batch_id)
    
    # Process tracking logs
    history_details = []
    for log in tracking_logs:
        # Get the user who updated the log
        updated_by_user = User.query.get(log.updated_by)
        
        history_details.append({
            'status': log.tracking_status,
            'timestamp': log.updated_at,
            'current_location': log.current_location,
            'temperature': log.temperature,
            'humidity': log.humidity,
            'updated_by': updated_by_user.username if updated_by_user else 'System',
            'carrier': log.carrier,
            'tracking_number': log.tracking_number,
            'manufacturer_name': manufacturer.username,  # Add manufacturer name
            'manufacturer_email': manufacturer.email , # Add manufacturer email
            'distributor_name': distributor.username,  # Add manufacturer name
            'distributor_email': distributor.email
        })

    return render_template(
        'consumer.html', 
        product=product, 
        manufacturer=manufacturer,
        distributor=distributor,
        pharmacy=pharmacy,
        history=history_details,
    )

@app.route('/alerts')
@login_required
def alerts():
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at.desc()).all()
    return render_template('alerts.html', alerts=alerts)

@app.route('/mark_alert_read/<int:alert_id>')
@login_required
def mark_alert_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    if alert.user_id == current_user.id:
        alert.is_read = True
        db.session.commit()
    return redirect(url_for('alerts'))

# @app.route('/reports')
# @login_required
# def reports():
#     if request.args.get('format') == 'excel':
#         # Generate Excel report
#         output = BytesIO()
#         writer = pd.ExcelWriter(output, engine='xlsxwriter')
        
#         # Products data
#         products_data = []
#         products = Product.query.all()
#         for product in products:
#             products_data.append({
#                 'Name': product.name,
#                 'Batch ID': product.batch_id,
#                 'Type': product.medicine_type,
#                 'Form': product.medicine_form,
#                 'Quantity': product.quantity,
#                 'Expiration Date': product.expiration_date
#             })
        
#         df_products = pd.DataFrame(products_data)
#         df_products.to_excel(writer, sheet_name='Products', index=False)
        
#         writer.save()
#         output.seek(0)
        
#         return send_file(
#             output,
#             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#             as_attachment=True,
#             download_name='medical_tracking_report.xlsx'
#         )
    
#     return render_template('reports.html')

# @app.route('/api/analytics')
# @login_required
# def get_analytics():
#     if current_user.role == 'manufacturer':
#         products = Product.query.filter_by(manufacturer_id=current_user.id).all()
#         data = {
#             'total_products': len(products),
#             'active_products': len([p for p in products if p.status == 'Active']),
#             'low_stock': len([p for p in products if p.quantity <= p.reorder_level]),
#             'expiring_soon': len([p for p in products if p.expiration_date <= date.today() + timedelta(days=30)])
#         }
#     elif current_user.role == 'distributor':
#         tracking = TransportTracking.query.all()
#         data = {
#             'total_shipments': len(tracking),
#             'in_transit': len([t for t in tracking if t.tracking_status == 'In Transit']),
#             'delivered': len([t for t in tracking if t.tracking_status == 'Delivered']),
#             'delayed': len([t for t in tracking if t.expected_delivery_date and t.expected_delivery_date < date.today()])
#         }
#     elif current_user.role == 'pharmacy':
#         inventory = PharmacyInventory.query.all()
#         data = {
#             'total_inventory': len(inventory),
#             'low_stock': len([i for i in inventory if i.quantity <= Product.query.get(i.product_id).reorder_level]),
#             'total_value': sum([i.quantity * i.unit_price for i in inventory]),
#             'expiring_soon': len([i for i in inventory if Product.query.get(i.product_id).expiration_date <= date.today() + timedelta(days=30)])
#         }
#     else:
#         data = {}
    
#     return jsonify(data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080, debug=True)