import mysql.connector
from datetime import datetime

# MySQL Database Settings
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '', # Update this
    'database': 'lpr_testing'
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS lpr_testing")
        cursor.execute("USE lpr_testing")
        
        # 1. System Parameters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sys_param (
                param_code INT PRIMARY KEY,
                param_name VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        params = [(1, 'Active'), (2, 'Deactivated'), (3, 'Unpaid'), (4, 'Paid')]
        for code, name in params:
            cursor.execute("""
                INSERT INTO sys_param (param_code, param_name) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE param_name = %s
            """, (code, name, name))

        # 2. Parking Scheme
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parking_scheme (
                id INT AUTO_INCREMENT PRIMARY KEY,
                scheme_name VARCHAR(50),
                first_hour_rate DECIMAL(10, 2),
                additional_hour_rate DECIMAL(10, 2),
                grace_period_mins INT DEFAULT 15,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT IGNORE INTO parking_scheme (id, scheme_name, first_hour_rate, additional_hour_rate, grace_period_mins) 
            VALUES (1, 'Standard Tiered', 3.00, 1.50, 15)
        """)

        # 3. Parking Records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parking_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plate_number VARCHAR(20) NOT NULL,
                in_time DATETIME NOT NULL,
                out_time DATETIME DEFAULT NULL,
                fee DECIMAL(10, 2) DEFAULT 0.00,
                status_code INT DEFAULT 1,
                payment_status_code INT DEFAULT 3,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        # Run migrations
        try:
            cursor.execute("ALTER TABLE parking_records ADD COLUMN status_code INT DEFAULT 1")
        except: pass
        try:
            cursor.execute("ALTER TABLE parking_records ADD COLUMN payment_status_code INT DEFAULT 3")
        except: pass
        try:
            cursor.execute("ALTER TABLE parking_scheme ADD COLUMN grace_period_mins INT DEFAULT 15")
        except: pass
        
        tables = ["sys_param", "parking_scheme", "parking_records"]
        for table in tables:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            except: pass

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database Layer Initialized.")
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    init_db()
