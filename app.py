import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import random
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hmac
import hashlib
import base64
import requests
import json
from dotenv import load_dotenv

from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
import atexit


load_dotenv()


app = Flask(__name__)
csrf = CSRFProtect(app)

app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')
PRODUCTS_UPLOAD_FOLDER = os.path.join('static', 'uploads', 'products')
os.makedirs(PRODUCTS_UPLOAD_FOLDER, exist_ok=True)


# --- APSCHEDULER: Abandoned Order Rollback ---
def rollback_abandoned_orders():
    with app.app_context():
        db = get_db()
        # Find PENDING orders older than 30 minutes
        cutoff_time = (datetime.now() - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            abandoned_orders = db.execute(
                "SELECT id, order_number FROM orders WHERE payment_status = 'PENDING' AND created_at < ?",
                (cutoff_time,)
            ).fetchall()
            
            if not abandoned_orders:
                return
                
            cursor = db.cursor()
            
            for order in abandoned_orders:
                order_id = order['id']
                # Get items for this order
                items = cursor.execute('SELECT product_id, quantity FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
                
                # Restore stock
                for item in items:
                    cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (item['quantity'], item['product_id']))
                
                # Update status
                cursor.execute("UPDATE orders SET payment_status = 'CANCELLED', order_status = 'CANCELLED' WHERE id = ?", (order_id,))
            
            db.commit() # Atomic rollback
            print(f"APScheduler: Automatically cancelled {len(abandoned_orders)} abandoned orders and restored stock.")
        except Exception as e:
            db.rollback()
            print(f"APScheduler Error during rollback: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=rollback_abandoned_orders, trigger="interval", minutes=15)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown(wait=False))
# ---------------------------------------------


app.config['PRODUCTS_UPLOAD_FOLDER'] = PRODUCTS_UPLOAD_FOLDER
DATABASE = 'bn_organic.db'

def is_valid_image(file_stream):
    header = file_stream.read(512)
    file_stream.seek(0)
    if header.startswith(b'\xff\xd8\xff'): return True # JPEG
    if header.startswith(b'\x89PNG\r\n\x1a\n'): return True # PNG
    if header.startswith(b'RIFF') and b'WEBP' in header[8:16]: return True # WEBP
    return False

# Initialize Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.context_processor
def inject_categories():
    try:
        db = get_db()
        categories = db.execute('SELECT name, slug FROM categories').fetchall()
    except Exception:
        categories = []
    return dict(nav_categories=categories)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/product/<slug>')
def product_details(slug):
    db = get_db()
    product = db.execute('''
        SELECT p.*, 
               ROUND(AVG(r.rating), 1) as avg_rating,
               COUNT(r.rating) as review_count
        FROM products p
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE p.slug = ?
        GROUP BY p.id
    ''', (slug,)).fetchone()
    if not product:
        return "Product not found", 404
        
    reviews = db.execute('''
        SELECT r.*, c.username as customer_name 
        FROM reviews r 
        JOIN customers c ON r.customer_id = c.id 
        WHERE r.product_id = ? ORDER BY r.created_at DESC
    ''', (product['id'],)).fetchall()
    
    reviews_list = []
    for r in reviews:
        r_dict = dict(r)
        verified = db.execute('''
            SELECT 1 FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.customer_id = ? AND oi.product_id = ? AND o.payment_status IN ('PAID', 'PAID_LATE')
            LIMIT 1
        ''', (r_dict['customer_id'], product['id'])).fetchone()
        r_dict['verified'] = bool(verified)
        reviews_list.append(r_dict)
        
    return render_template('product-details.html', product=product, reviews=reviews_list)

@app.route('/checkout')
def checkout():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    return render_template('checkout.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def customer_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db()
        customer = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        
        if customer and check_password_hash(customer['password_hash'], password):
            session['customer_id'] = customer['id']
            session['customer_name'] = customer['name']
            return redirect(url_for('index'))
            
        return render_template('login.html', error="Invalid email or password")
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def customer_register():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        # Validate username is lowercase letters only
        import re
        if not re.match(r'^[a-z]+$', username):
            return render_template('register.html', error="Username must be lowercase letters only, no spaces or numbers.")
        
        db = get_db()
        existing_email = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        if existing_email:
            return render_template('register.html', error="Email already exists")
            
        existing_username = db.execute('SELECT * FROM customers WHERE username = ?', (username,)).fetchone()
        if existing_username:
            return render_template('register.html', error="Username is already taken")
            
        hashed = generate_password_hash(password)
        db.execute('INSERT INTO customers (username, name, email, phone, password_hash) VALUES (?, ?, ?, ?, ?)', 
                  (username, name, email, phone, hashed))
        db.commit()
        return redirect(url_for('customer_login'))
        
    return render_template('register.html')

@app.route('/orders', methods=['GET'])
def customer_orders():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
        
    db = get_db()
    customer_id = session['customer_id']
    
    # Fetch orders for this customer
    orders = db.execute('SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC', (customer_id,)).fetchall()
    
    return render_template('orders.html', orders=orders)

@app.route('/profile')
def customer_profile():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    orders = db.execute('SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC', (session['customer_id'],)).fetchall()
    return render_template('profile.html', customer=customer, orders=orders)

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy.html')

@app.route('/terms-conditions')
def terms_conditions():
    return render_template('terms.html')

@app.route('/password', methods=['GET'])
def customer_password():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    return render_template('password.html')

@app.route('/logout')
def customer_logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    return redirect(url_for('index'))



@app.route('/invoice/<order_number>')
def invoice(order_number):
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,)).fetchone()
    if not order:
        return "Order not found", 404
        
    customer_id = session.get('customer_id')
    admin_id = session.get('admin_id')
    if not admin_id and (not customer_id or order['customer_id'] != customer_id):
        return "Unauthorized", 401
    
    items = db.execute('''
        SELECT oi.*, p.name 
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.id 
        WHERE oi.order_id = ?
    ''', (order['id'],)).fetchall()
    
    return render_template('invoice.html', order=order, items=items)

# Admin Routes
@app.route('/admin/login.html', methods=['GET'])
def admin_login_page():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/login.html')

@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login_page'))
    return render_template('admin/dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login_page'))

@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset-password')
def reset_password_page():
    return render_template('reset_password.html')

@app.route('/api/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")
def api_forgot_password():
    data = request.json
    email = data.get('email')
    phone = data.get('phone')
    
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE email = ? AND phone = ?', (email, phone)).fetchone()
    
    if not customer:
        return jsonify({'success': False, 'message': 'No account found matching this email and phone number.'})
        
    otp = str(random.randint(100000, 999999))
    expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    
    db.execute('INSERT INTO password_resets (customer_id, otp, expires_at) VALUES (?, ?, ?)', (customer['id'], otp, expires_at))
    db.commit()
    
    print("\n" + "="*50)
    print(f"MOCK OTP DELIVERY FOR {customer['name']}")
    print(f"OTP: {otp}")
    print(f"Expires at: {expires_at.split(' ')[1]}")
    print("="*50 + "\n")
    
    return jsonify({'success': True, 'message': 'An OTP has been sent to your email and phone number!'})

@app.route('/api/reset-password', methods=['POST'])
@limiter.limit("3 per minute")
def api_reset_password():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('new_password')
    
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
    
    if not customer:
        return jsonify({'success': False, 'message': 'Invalid request'})
        
    reset_record = db.execute('SELECT * FROM password_resets WHERE customer_id = ? AND otp = ? ORDER BY expires_at DESC LIMIT 1', (customer['id'], otp)).fetchone()
    
    if not reset_record:
        return jsonify({'success': False, 'message': 'Invalid OTP'})
        
    # Parse the exact format we stored it in to avoid microsecond formatting errors
    expires_at = datetime.strptime(reset_record['expires_at'], '%Y-%m-%d %H:%M:%S')
    if datetime.now() > expires_at:
        return jsonify({'success': False, 'message': 'OTP has expired'})
        
    hashed = generate_password_hash(new_password)
    db.execute('UPDATE customers SET password_hash = ? WHERE id = ?', (hashed, customer['id']))
    db.execute('DELETE FROM password_resets WHERE id = ?', (reset_record['id'],))
    db.commit()
    
    return jsonify({'success': True, 'message': 'Password has been successfully reset!'})

# API Routes
@app.route('/api/products', methods=['GET'])
def api_products():
    db = get_db()
    category = request.args.get('category')
    search = request.args.get('search')
    
    query = '''
        SELECT p.*, c.name as category_name,
               ROUND(AVG(r.rating), 1) as avg_rating,
               COUNT(r.rating) as review_count
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE 1=1
    '''
    params = []
    
    if category and category != 'all':
        query += ' AND c.slug = ?'
        params.append(category)
        
    if search:
        query += ' AND (p.name LIKE ? OR p.description LIKE ?)'
        params.extend(['%' + search + '%', '%' + search + '%'])
        
    query += ' GROUP BY p.id'
        
    products = db.execute(query, tuple(params)).fetchall()
    
    return jsonify([dict(p) for p in products])

@app.route('/api/categories', methods=['GET'])
def api_categories():
    db = get_db()
    categories = db.execute('SELECT * FROM categories').fetchall()
    return jsonify([dict(c) for c in categories])

@app.route('/api/orders/create', methods=['POST'])
def api_create_order():
    data = request.json
    db = get_db()
    
    customer_id = session.get('customer_id')
    if not customer_id:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
    order_number = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    delivery_charge = 100.0
    calculated_subtotal = 0.0

    cursor = db.cursor()
    
    verified_items = []
    for item in data['items']:
        qty = int(item.get('quantity', 0))
        if qty <= 0:
            return jsonify({'success': False, 'message': 'Invalid quantity detected'}), 400
            
        product = cursor.execute('SELECT price, stock FROM products WHERE id = ?', (item['productId'],)).fetchone()
        
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
            
        if product['stock'] < qty:
            return jsonify({'success': False, 'message': 'Insufficient stock for a product'}), 400
            
        calculated_subtotal += product['price'] * qty
        verified_items.append({
            'productId': item['productId'],
            'quantity': qty,
            'price': product['price']
        })

    total_with_delivery = calculated_subtotal + delivery_charge

    landmark = data.get('landmark', '').strip()
    postal_code_val = landmark if landmark else 'N/A'
    street_address_val = f"{data['municipality']}, {data['ward_tol']}"
    
    cursor.execute('''
        INSERT INTO orders (customer_id, order_number, customer_name, email, phone, street_address, city, state, postal_code, delivery_charge, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        customer_id, order_number, data['fullName'], data['email'], 
        data['phone'], street_address_val, data['district'], data['province'], 
        postal_code_val, delivery_charge, total_with_delivery
    ))
    order_id = cursor.lastrowid
    
    for item in verified_items:
        cursor.execute('''
            INSERT INTO order_items (order_id, product_id, quantity, unit_price)
            VALUES (?, ?, ?, ?)
        ''', (order_id, item['productId'], item['quantity'], item['price']))
        
        cursor.execute('''
            UPDATE products SET stock = stock - ? WHERE id = ?
        ''', (item['quantity'], item['productId']))
        
    db.commit()
    
    def generate_esewa_signature(total_amount, transaction_uuid, product_code):
        secret_key = os.environ.get('ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')
        if product_code == 'EPAYTEST':
            secret_key = '8gBm/:&EnhH.1/q'
        message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
        hash_obj = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(hash_obj.digest()).decode('utf-8')
        
    product_code = os.environ.get('ESEWA_PRODUCT_CODE', 'EPAYTEST')
    
    # Format to strictly 2 decimal places and cast to string to prevent any JSON parser/float truncation mismatch
    total_str = f"{total_with_delivery:.2f}"
    
    signature = generate_esewa_signature(total_str, order_number, product_code)
    
    esewa_payload = {
        "amount": f"{calculated_subtotal:.2f}",
        "tax_amount": "0.00",
        "total_amount": total_str,
        "transaction_uuid": order_number,
        "product_code": product_code,
        "product_service_charge": "0.00",
        "product_delivery_charge": f"{delivery_charge:.2f}",
        "success_url": request.host_url.rstrip('/') + url_for('esewa_verify'),
        "failure_url": request.host_url.rstrip('/') + url_for('customer_orders'),
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": signature
    }
    
    return jsonify({
        'success': True, 
        'order_number': order_number, 
        'esewa_payload': esewa_payload,
        'esewa_url': os.environ.get('ESEWA_API_URL', 'https://rc-epay.esewa.com.np/api/epay/main/v2/form')
    })

@app.route('/payment/esewa/verify')
def esewa_verify():
    encoded_data = request.args.get('data')
    if not encoded_data:
        return "Invalid payment callback", 400
        
    try:
        decoded_str = base64.b64decode(encoded_data).decode('utf-8')
        response_data = json.loads(decoded_str)
        transaction_uuid = response_data.get('transaction_uuid')
        total_amount = response_data.get('total_amount')
        
        status_url = os.environ.get('ESEWA_STATUS_URL', 'https://rc-epay.esewa.com.np/api/epay/transaction/status/')
        merchant_code = os.environ.get('ESEWA_PRODUCT_CODE', 'EPAYTEST')
        
        verify_url = f"{status_url}?product_code={merchant_code}&total_amount={total_amount}&transaction_uuid={transaction_uuid}"
        status_req = requests.get(verify_url)
        status_res = status_req.json()
        
        if status_res.get('status') == 'COMPLETE':
            db = get_db()
            
            # Check if order was cancelled
            order_record = db.execute("SELECT payment_status FROM orders WHERE order_number = ?", (transaction_uuid,)).fetchone()
            if order_record and order_record['payment_status'] == 'CANCELLED':
                db.execute("UPDATE orders SET payment_status = 'PAID_LATE' WHERE order_number = ?", (transaction_uuid,))
            else:
                db.execute("UPDATE orders SET payment_status = 'PAID' WHERE order_number = ?", (transaction_uuid,))
            db.commit()
            return redirect(url_for('customer_orders'))
        else:
            return "Payment verification failed or pending.", 400
            
    except Exception as e:
        return f"Error verifying payment: {str(e)}", 400

@app.route('/api/admin/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    db = get_db()
    admin = db.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
    
    if admin and check_password_hash(admin['password_hash'], password):
        session['admin_id'] = admin['id']
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/admin/metrics', methods=['GET'])
def api_admin_metrics():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
        
    db = get_db()
    
    total_orders = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    total_revenue = db.execute("SELECT SUM(total_amount) FROM orders WHERE payment_status = 'PAID'").fetchone()[0] or 0
    low_stock = db.execute('SELECT COUNT(*) FROM products WHERE stock < 20').fetchone()[0]
    
    recent_orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 5').fetchall()
    
    return jsonify({
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'low_stock_alerts': low_stock,
        'recent_orders': [dict(o) for o in recent_orders]
    })

@app.route('/api/admin/orders', methods=['GET'])
def api_admin_orders():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    return jsonify([dict(o) for o in orders])

@app.route('/api/admin/customers', methods=['GET'])
def api_admin_customers():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    db = get_db()
    customers = db.execute('SELECT id, username, name, email, phone FROM customers').fetchall()
    return jsonify([dict(c) for c in customers])

@app.route('/api/admin/customers/<int:id>', methods=['GET'])
def api_admin_customer_detail(id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    db = get_db()
    customer = db.execute('SELECT id, username, name, email, phone FROM customers WHERE id = ?', (id,)).fetchone()
    if not customer:
        return jsonify({'error': 'Not found'}), 404
        
    orders = db.execute('SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC', (id,)).fetchall()
    
    return jsonify({
        'customer': dict(customer),
        'orders': [dict(o) for o in orders]
    })

@app.route('/api/profile/password', methods=['POST'])
def api_change_password():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
        
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Invalid input'})
        
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if not check_password_hash(customer['password_hash'], current_password):
        return jsonify({'success': False, 'message': 'Incorrect current password'})
        
    hashed = generate_password_hash(new_password)
    db.execute('UPDATE customers SET password_hash = ? WHERE id = ?', (hashed, session['customer_id']))
    db.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/categories/add', methods=['POST'])
def api_admin_categories_add():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 403
    data = request.json
    db = get_db()
    try:
        db.execute('INSERT INTO categories (name, slug) VALUES (?, ?)', (data['name'], data['slug']))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/admin/categories/edit/<int:id>', methods=['PUT'])
def api_admin_categories_edit(id):
    if 'admin_id' not in session:
        return jsonify({'success': False}), 403
    data = request.json
    db = get_db()
    try:
        db.execute('UPDATE categories SET name = ?, slug = ? WHERE id = ?', (data['name'], data['slug'], id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/admin/categories/delete/<int:id>', methods=['DELETE'])
def api_admin_categories_delete(id):
    if 'admin_id' not in session:
        return jsonify({'success': False}), 403
    db = get_db()
    try:
        products_count = db.execute('SELECT COUNT(*) as count FROM products WHERE category_id = ?', (id,)).fetchone()
        if products_count and products_count['count'] > 0:
            return jsonify({'success': False, 'message': 'Cannot delete category because it contains products. Reassign or delete the products first.'}), 400
            
        db.execute('DELETE FROM categories WHERE id = ?', (id,))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/admin/products/add', methods=['POST'])
def api_admin_products_add():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 403
        
    data = request.form
    image_url = '/static/images/placeholder.jpg'
    
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and file.filename != '':
            if not is_valid_image(file):
                return jsonify({'success': False, 'message': 'Invalid image file format. Only PNG, JPG, and WEBP are allowed.'}), 400
            
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.webp']:
                return jsonify({'success': False, 'message': 'Unsupported file extension.'}), 400
                
            filename = uuid.uuid4().hex + ext
            file.save(os.path.join(app.config['PRODUCTS_UPLOAD_FOLDER'], filename))
            image_url = f'/static/uploads/products/{filename}'

    db = get_db()
    try:
        db.execute('''
            INSERT INTO products (category_id, name, slug, price, stock, description, image_url) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['category_id'], data['name'], data['slug'], data['price'], data['stock'], data['description'], image_url))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/admin/products/<int:id>', methods=['PUT', 'DELETE'])
def api_admin_products_mod(id):
    if 'admin_id' not in session:
        return jsonify({'success': False}), 403
    db = get_db()
    if request.method == 'DELETE':
        db.execute('DELETE FROM products WHERE id = ?', (id,))
        db.commit()
        return jsonify({'success': True})
    else:
        data = request.form
        image_url = None
        
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '':
                if not is_valid_image(file):
                    return jsonify({'success': False, 'message': 'Invalid image file format. Only PNG, JPG, and WEBP are allowed.'}), 400
                
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in ['.png', '.jpg', '.jpeg', '.webp']:
                    return jsonify({'success': False, 'message': 'Unsupported file extension.'}), 400
                    
                filename = uuid.uuid4().hex + ext
                file.save(os.path.join(app.config['PRODUCTS_UPLOAD_FOLDER'], filename))
                image_url = f'/static/uploads/products/{filename}'
                
        try:
            if image_url:
                db.execute('''
                    UPDATE products SET category_id=?, name=?, slug=?, price=?, stock=?, description=?, image_url=?
                    WHERE id=?
                ''', (data['category_id'], data['name'], data['slug'], data['price'], data['stock'], data['description'], image_url, id))
            else:
                db.execute('''
                    UPDATE products SET category_id=?, name=?, slug=?, price=?, stock=?, description=?
                    WHERE id=?
                ''', (data['category_id'], data['name'], data['slug'], data['price'], data['stock'], data['description'], id))
            db.commit()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/reviews/<int:product_id>', methods=['GET', 'POST'])
def api_reviews(product_id):
    db = get_db()
    if request.method == 'GET':
        reviews = db.execute('''
            SELECT r.*, c.username as customer_name 
            FROM reviews r 
            JOIN customers c ON r.customer_id = c.id 
            WHERE r.product_id = ? ORDER BY r.created_at DESC
        ''', (product_id,)).fetchall()
        
        reviews_list = []
        for r in reviews:
            r_dict = dict(r)
            verified = db.execute('''
                SELECT 1 FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                WHERE o.customer_id = ? AND oi.product_id = ? AND o.payment_status IN ('PAID', 'PAID_LATE')
                LIMIT 1
            ''', (r_dict['customer_id'], product_id)).fetchone()
            r_dict['verified'] = bool(verified)
            reviews_list.append(r_dict)
            
        return jsonify(reviews_list)
    
    if request.method == 'POST':
        if 'customer_id' not in session:
            return jsonify({'success': False, 'message': 'Must be logged in to leave a review'}), 401
        data = request.json
        db.execute('INSERT INTO reviews (product_id, customer_id, rating, comment) VALUES (?, ?, ?, ?)', 
                   (product_id, session['customer_id'], data['rating'], data['comment']))
        db.commit()
        return jsonify({'success': True})

@app.route('/api/review_action/<int:review_id>', methods=['PUT', 'DELETE'])
def api_review_action(review_id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Must be logged in'}), 401
        
    db = get_db()
    review = db.execute('SELECT * FROM reviews WHERE id = ?', (review_id,)).fetchone()
    
    if not review:
        return jsonify({'success': False, 'message': 'Review not found'}), 404
        
    if review['customer_id'] != session['customer_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    if request.method == 'PUT':
        data = request.json
        db.execute('UPDATE reviews SET rating = ?, comment = ? WHERE id = ?', 
                   (data['rating'], data['comment'], review_id))
        db.commit()
        return jsonify({'success': True})
        
    if request.method == 'DELETE':
        db.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
        db.commit()
        return jsonify({'success': True})

if __name__ == '__main__':
    # Ensure database exists before running
    if not os.path.exists(DATABASE):
        import database
        database.init_db()
    app.run(debug=True, port=5000)
