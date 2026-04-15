from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import mysql.connector
import os
from datetime import datetime

# Import database configuration
from db_manager import DB_CONFIG

app = FastAPI(title="LPR Parking Platform APIs")

# Mount frontend directory for static assets
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# --- MODELS ---

class SysParamItem(BaseModel):
    param_code: int
    param_name: str

class SchemeItem(BaseModel):
    id: int = None
    scheme_name: str
    first_hour_rate: float
    additional_hour_rate: float
    grace_period_mins: int

class RecordItem(BaseModel):
    id: int = None
    plate_number: str
    in_time: str
    out_time: str = None
    fee: float = 0.0
    status_code: int = 1
    payment_status_code: int = 3

# --- DASHBOARD STATS & RECORDS ---

@app.get("/api/dashboard")
async def get_dashboard():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT pr.*, 
                   s1.param_name as status_name, 
                   s2.param_name as payment_name 
            FROM parking_records pr
            LEFT JOIN sys_param s1 ON pr.status_code = s1.param_code
            LEFT JOIN sys_param s2 ON pr.payment_status_code = s2.param_code
            ORDER BY pr.in_time DESC
        """)
        records = cursor.fetchall()
        
        cursor.execute("SELECT * FROM parking_scheme LIMIT 1")
        scheme = cursor.fetchone()
        
        # Calculate time-based entry stats
        cursor.execute("SELECT in_time FROM parking_records WHERE in_time IS NOT NULL")
        all_times = cursor.fetchall()
        
        now = datetime.now()
        counts = {"10m": 0, "1h": 0, "3h": 0, "24h": 0, "1w": 0}
        for row in all_times:
            diff = (now - row['in_time']).total_seconds()
            if diff <= 600: counts["10m"] += 1
            if diff <= 3600: counts["1h"] += 1
            if diff <= 10800: counts["3h"] += 1
            if diff <= 86400: counts["24h"] += 1
            if diff <= 604800: counts["1w"] += 1

        cursor.close()
        conn.close()
        
        return {
            "records": records,
            "scheme": scheme,
            "counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/revenue")
async def get_revenue(filter: str = "hourly"):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        if filter == "hourly":
            cursor.execute("""
                SELECT DATE_FORMAT(out_time, '%Y-%m-%d %H:00') as label, COALESCE(SUM(fee), 0) as revenue 
                FROM parking_records 
                WHERE out_time IS NOT NULL AND out_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY label ORDER BY label ASC
            """)
        elif filter == "daily":
            cursor.execute("""
                SELECT DATE(out_time) as label, COALESCE(SUM(fee), 0) as revenue 
                FROM parking_records 
                WHERE out_time IS NOT NULL AND out_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY label ORDER BY label ASC
            """)
        elif filter == "weekly":
            cursor.execute("""
                SELECT YEARWEEK(out_time) as label, COALESCE(SUM(fee), 0) as revenue 
                FROM parking_records 
                WHERE out_time IS NOT NULL AND out_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                GROUP BY label ORDER BY label ASC
            """)
        elif filter == "monthly":
            cursor.execute("""
                SELECT DATE_FORMAT(out_time, '%Y-%m') as label, COALESCE(SUM(fee), 0) as revenue 
                FROM parking_records 
                WHERE out_time IS NOT NULL AND out_time >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                GROUP BY label ORDER BY label ASC
            """)
        else:
            cursor.close()
            conn.close()
            return []
        
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"label": str(r["label"]), "revenue": float(r["revenue"])} for r in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- SYS PARAM CRUD ---

@app.get("/api/sysparam")
async def get_sysparams():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sys_param ORDER BY param_code ASC")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sysparam")
async def create_sysparam(item: SysParamItem):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sys_param (param_code, param_name) VALUES (%s, %s)", 
                       (item.param_code, item.param_name))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/sysparam/{code}")
async def update_sysparam(code: int, item: SysParamItem):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE sys_param SET param_name = %s WHERE param_code = %s", 
                       (item.param_name, code))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sysparam/{code}")
async def delete_sysparam(code: int):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sys_param WHERE param_code = %s", (code,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PARKING SCHEME CRUD ---

@app.get("/api/scheme")
async def get_schemes():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM parking_scheme ORDER BY id ASC")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheme")
async def create_scheme(item: SchemeItem):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO parking_scheme (scheme_name, first_hour_rate, additional_hour_rate, grace_period_mins) 
            VALUES (%s, %s, %s, %s)
        """, (item.scheme_name, item.first_hour_rate, item.additional_hour_rate, item.grace_period_mins))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/scheme/{item_id}")
async def update_scheme(item_id: int, item: SchemeItem):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE parking_scheme 
            SET scheme_name = %s, first_hour_rate = %s, additional_hour_rate = %s, grace_period_mins = %s 
            WHERE id = %s
        """, (item.scheme_name, item.first_hour_rate, item.additional_hour_rate, item.grace_period_mins, item_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/scheme/{item_id}")
async def delete_scheme(item_id: int):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM parking_scheme WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PARKING RECORDS CRUD ---

@app.get("/api/records")
async def get_records():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM parking_records ORDER BY in_time DESC")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/records")
async def create_record(item: RecordItem):
    try:
        conn = get_db()
        cursor = conn.cursor()
        out_time = item.out_time if item.out_time else None
        cursor.execute("""
            INSERT INTO parking_records (plate_number, in_time, out_time, fee, status_code, payment_status_code) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (item.plate_number, item.in_time, out_time, item.fee, item.status_code, item.payment_status_code))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/records/{item_id}")
async def update_record(item_id: int, item: RecordItem):
    try:
        conn = get_db()
        cursor = conn.cursor()
        out_time = item.out_time if item.out_time else None
        cursor.execute("""
            UPDATE parking_records 
            SET plate_number = %s, in_time = %s, out_time = %s, fee = %s, status_code = %s, payment_status_code = %s 
            WHERE id = %s
        """, (item.plate_number, item.in_time, out_time, item.fee, item.status_code, item.payment_status_code, item_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Updated successfully"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/records/{item_id}")
async def delete_record(item_id: int):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM parking_records WHERE id = %s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8005)
