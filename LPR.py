import cv2
import torch
import os
import time
import subprocess
import webbrowser
import sys
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import easyocr

# Import custom modules
from db_manager import init_db
from parking_logic import process_parking, correct_plate_errors

# Optimize CPU threads for inference
torch.set_num_threads(min(os.cpu_count(), 4))

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model")

# OCR Engines Initialization
print("Initializing LPR Engines...")
reader = easyocr.Reader(['en']) 
model = None
processor = None

def load_precise_model():
    global model, processor
    if model is not None: return
    print("Loading Precise Engine (Qwen2-VL)...")
    try:
        model = Qwen2VLForConditionalGeneration.from_pretrained(MODEL_PATH, torch_dtype="auto", device_map="auto")
        processor = AutoProcessor.from_pretrained(MODEL_PATH)
    except Exception as e:
        print(f"Precise engine failed to load: {e}")
        model = Qwen2VLForConditionalGeneration.from_pretrained(MODEL_PATH, torch_dtype=torch.float32, device_map="cpu")
        processor = AutoProcessor.from_pretrained(MODEL_PATH)

def scan_plate_precise(frame):
    load_precise_model()
    color_coverted = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(color_coverted)
    res_limit = {"min_pixels": 224*28*28, "max_pixels": 448*28*28}
    messages = [{"role": "user", "content": [{"type": "image", "image": pil_image, **res_limit}, {"type": "text", "text": "Extract Malaysian plate number. Format like 'WYY 1234'. Return ONLY THE TEXT."}]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to(model.device)
    generated_ids = model.generate(**inputs, max_new_tokens=20)
    generated_ids_trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
    return processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0].strip()

def scan_plate_fast(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    results = reader.readtext(gray)
    plates = []
    for (bbox, text, prob) in results:
        clean_text = "".join(c for c in text if c.isalnum() or c == " ").upper().strip()
        if len(clean_text) >= 3:
            plates.append(correct_plate_errors(clean_text))
    return plates[0] if plates else "No Plate Found"

def main():
    # Initialize Database
    init_db()

    # Launch Dashboard
    print("🚀 Starting LPR Web Dashboard...")
    dashboard_proc = None
    try:
        dashboard_proc = subprocess.Popen([sys.executable, "lpr_dashboard_web.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        webbrowser.open("http://localhost:8005")
    except Exception as e:
        print(f"⚠️ Dashboard error: {e}")

    print("Starting camera feed...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0) # Fallback to default
        if not cap.isOpened():
            print("❌ Error: Could not open camera. Please check your webcam connection.")
            if dashboard_proc:
                dashboard_proc.terminate()
            input("Press Enter to exit...")
            return

    print("\n--- Malaysian Smart Parking LPR ---")
    print("Commands: [S] Scan | [G] Toggle Gate | [M] Toggle Engine | [Q] Quit")
    
    last_plate = "N/A"
    status_msg = "Waiting..."
    scanning = False
    is_fast_mode = True
    gate_type = "IN"

    while True:
        ret, frame = cap.read()
        if not ret: break

        display_frame = frame.copy()
        cv2.rectangle(display_frame, (0, 0), (640, 140), (0,0,0), -1)
        
        gate_color = (0, 255, 0) if gate_type == "IN" else (0, 165, 255)
        cv2.putText(display_frame, f"GATE: {gate_type}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, gate_color, 2)
        cv2.putText(display_frame, f"Engine: {'FAST' if is_fast_mode else 'PRECISE'}", (200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(display_frame, f"Last Plate: {last_plate}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Status: {status_msg}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        if scanning:
            cv2.putText(display_frame, "PROCESSING...", (450, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow("Malaysian LPR", display_frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('s'):
            scanning = True
            cv2.imshow("Malaysian LPR", display_frame)
            cv2.waitKey(1)
            try:
                plate = scan_plate_fast(frame) if is_fast_mode else scan_plate_precise(frame)
                last_plate = plate
                status_msg = process_parking(plate, gate_type)
                print(f"[{gate_type}] {plate}: {status_msg}")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                scanning = False

        elif key == ord('g'):
            gate_type = "OUT" if gate_type == "IN" else "IN"
            print(f"Gate switched to: {gate_type}")

        elif key == ord('m'):
            is_fast_mode = not is_fast_mode
            if not is_fast_mode: load_precise_model()

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    if dashboard_proc and dashboard_proc.poll() is None:
        print("🛑 Shutting down dashboard server...")
        dashboard_proc.terminate()
        dashboard_proc.wait(timeout=5)

if __name__ == "__main__":
    main()
