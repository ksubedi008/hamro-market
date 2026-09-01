import sqlite3
from datetime import datetime
import traceback

with open('db_test_output.txt', 'w') as f:
    try:
        conn = sqlite3.connect('../bn_organic.db')
        c = conn.cursor()
        res = c.execute('SELECT expires_at FROM password_resets').fetchall()
        f.write(f"Stored values: {res}\n")
        for row in res:
            try:
                datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f')
                f.write(f"Parsed {row[0]} successfully\n")
            except Exception as e:
                f.write(f"Error parsing {row[0]}: {e}\n")
    except Exception as e:
        f.write(f"Global error: {traceback.format_exc()}\n")
