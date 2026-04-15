import math
import time
from datetime import datetime
from db_manager import get_connection

def correct_plate_errors(text):
    """Smart correction based on Malaysian plate standards."""
    if not text: return text
    chars = list(text)
    
    # Prefix (Letters)
    for i in range(min(len(chars), 3)):
        if chars[i].isdigit():
            mapping = {'8': 'B', '5': 'S', '0': 'D', '2': 'Z', '1': 'I'}
            chars[i] = mapping.get(chars[i], chars[i])
        
    # Suffix/Number (Digits)
    first_digit_found = False
    for i in range(len(chars)):
        if chars[i].isdigit(): first_digit_found = True
        if first_digit_found:
            mapping = {'S': '5', 'O': '0', 'I': '1', 'Z': '2', 'B': '8'}
            chars[i] = mapping.get(chars[i], chars[i])

    return "".join(chars)

def process_parking(plate, gate_type="IN"):
    """Core Business Logic for Gate Entry/Exit."""
    if plate == "No Plate Found": return "Invalid Scan"
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        now = datetime.now()
        
        if gate_type == "IN":
            cursor.execute("SELECT id FROM parking_records WHERE plate_number = %s AND status_code = 1", (plate,))
            if cursor.fetchone():
                return "Error: Already inside!"
            
            cursor.execute("INSERT INTO parking_records (plate_number, in_time, status_code, payment_status_code) VALUES (%s, %s, 1, 3)", (plate, now))
            conn.commit()
            return f"CHECK-IN SUCCESS at {now.strftime('%H:%M')}"
            
        else:
            # OUT GATE
            cursor.execute("SELECT * FROM parking_records WHERE plate_number = %s AND status_code = 1", (plate,))
            record = cursor.fetchone()
            if not record: return "Error: No matching check-in!"
            
            # Fetch Scheme
            cursor.execute("SELECT first_hour_rate, additional_hour_rate, grace_period_mins FROM parking_scheme LIMIT 1")
            scheme = cursor.fetchone()
            rate_1 = float(scheme['first_hour_rate']) if scheme else 3.00
            rate_extra = float(scheme['additional_hour_rate']) if scheme else 1.50
            grace = int(scheme['grace_period_mins']) if scheme else 15
            
            # Calculate
            duration = now - record['in_time']
            mins = duration.total_seconds() / 60
            hours = math.ceil(duration.total_seconds() / 3600)
            
            if mins <= grace:
                fee = 0.0
            elif hours <= 1:
                fee = rate_1
            else:
                fee = rate_1 + (hours - 1) * rate_extra
            
            if fee > 0:
                print(f"💳 Simulating Payment for {plate}: RM {fee:.2f}...")
                time.sleep(1)
            
            cursor.execute("""
                UPDATE parking_records 
                SET out_time = %s, fee = %s, status_code = 2, payment_status_code = 4 
                WHERE id = %s
            """, (now, fee, record['id']))
            conn.commit()
            return f"PAID RM {fee:.2f}. Safe Trip!"
            
    except Exception as e:
        return f"Logic Error: {str(e)}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
