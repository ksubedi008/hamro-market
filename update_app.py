import sys

with open(r'c:\Kamal\BN\app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports
import_insert = '''
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
'''
content = content.replace('from dotenv import load_dotenv', 'from dotenv import load_dotenv\n' + import_insert)

# 2. Init CSRF
csrf_insert = '''
app = Flask(__name__)
csrf = CSRFProtect(app)
'''
content = content.replace('app = Flask(__name__)', csrf_insert)

# 3. Add scheduler logic
scheduler_code = '''

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

'''
content = content.replace('os.makedirs(PRODUCTS_UPLOAD_FOLDER, exist_ok=True)', 'os.makedirs(PRODUCTS_UPLOAD_FOLDER, exist_ok=True)\n' + scheduler_code)

# 4. Modify late payment logic in esewa_verify
esewa_verify_update_old = '''        if status_res.get('status') == 'COMPLETE':
            db = get_db()
            db.execute("UPDATE orders SET payment_status = 'PAID' WHERE order_number = ?", (transaction_uuid,))
            db.commit()
            return redirect(url_for('customer_orders'))'''
esewa_verify_update_new = '''        if status_res.get('status') == 'COMPLETE':
            db = get_db()
            
            # Check if order was cancelled
            order_record = db.execute("SELECT payment_status FROM orders WHERE order_number = ?", (transaction_uuid,)).fetchone()
            if order_record and order_record['payment_status'] == 'CANCELLED':
                db.execute("UPDATE orders SET payment_status = 'PAID_LATE' WHERE order_number = ?", (transaction_uuid,))
            else:
                db.execute("UPDATE orders SET payment_status = 'PAID' WHERE order_number = ?", (transaction_uuid,))
            db.commit()
            return redirect(url_for('customer_orders'))'''
content = content.replace(esewa_verify_update_old, esewa_verify_update_new)

with open(r'c:\Kamal\BN\app.py', 'w', encoding='utf-8') as f:
    f.write(content)
