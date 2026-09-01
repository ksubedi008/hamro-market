import sqlite3
import os
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash

DATABASE_FILE = 'bn_organic.db'

def init_db():
    load_dotenv()
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        print(f"Removed existing database: {DATABASE_FILE}")

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Create Customers Table
    cursor.execute('''
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')

    # Create Categories Table
    cursor.execute('''
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        slug TEXT NOT NULL UNIQUE
    )
    ''')

    # Create Products Table
    cursor.execute('''
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        price REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 10,
        description TEXT NOT NULL,
        image_url TEXT NOT NULL,
        rating REAL DEFAULT 5.0,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    ''')

    # Create Orders Table
    cursor.execute('''
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        order_number TEXT NOT NULL UNIQUE,
        customer_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        street_address TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        postal_code TEXT NOT NULL,
        delivery_charge REAL NOT NULL DEFAULT 100.0,
        total_amount REAL NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'PENDING',
        order_status TEXT NOT NULL DEFAULT 'PROCESSING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    ''')

    # Create Order Items Table
    cursor.execute('''
    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    ''')

    # Create Admins Table
    cursor.execute('''
    CREATE TABLE admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
    ''')

    # Create Reviews Table
    cursor.execute('''
    CREATE TABLE reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
        comment TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    ''')

    # Create Password Resets Table
    cursor.execute('''
    CREATE TABLE password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        otp TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    ''')

    # Seed Data

    # 1. Categories
    categories = [
        ('Groceries', 'groceries'),
        ('Juice', 'juice')
    ]
    cursor.executemany('INSERT INTO categories (name, slug) VALUES (?, ?)', categories)

    # 2. Products
    products = [
        (1, 'Fresh Organic Honey', 'fresh-organic-honey', 1100.00, 50, 'Sweeten your day with our fresh organic honey, harvested straight from the hive, offering a natural, rich flavor and packed with beneficial nutrients.', '/static/images/organic_honey.jpg', 5.0),
        (1, 'Assorted Coffee', 'assorted-coffee', 400.00, 20, 'Premium roasted organic coffee beans.', '/static/images/organic_coffee.jpg', 4.5),
        (1, 'Cashew Butter', 'cashew-butter', 1400.00, 15, 'Creamy and organic cashew butter.', '/static/images/placeholder.jpg', 4.8),
        (1, 'Natural Extracted Edible Oil', 'edible-oil', 650.00, 30, 'Natural organic extracted edible oil for your daily cooking.', '/static/images/placeholder.jpg', 4.7),
        (1, 'Diabetic Cookies', 'diabetic-cookies', 95.00, 100, 'Healthy cookies for diabetic patients.', '/static/images/placeholder.jpg', 4.6),
        (2, 'Fresh Orange Juice', 'fresh-orange-juice', 250.00, 40, '100% pure organic orange juice.', '/static/images/organic_juice.jpg', 4.9),
    ]
    cursor.executemany('''
        INSERT INTO products (category_id, name, slug, price, stock, description, image_url, rating) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', products)

    # 3. Admins and Customers
    raw_admin_password = os.environ.get('ADMIN_PASSWORD', os.urandom(12).hex())
    admin_password = generate_password_hash(raw_admin_password)
    cursor.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)', ('admin', admin_password))

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
