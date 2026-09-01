import sqlite3

try:
    conn = sqlite3.connect('bn_organic.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM order_items')
    cursor.execute('DELETE FROM orders')
    conn.commit()
    print("Successfully deleted all records from orders and order_items tables.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
