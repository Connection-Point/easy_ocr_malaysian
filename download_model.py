from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
import os
from huggingface_hub import snapshot_download

MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"
# Define SAVE_PATH relative to the current script's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "model")

def main():
    # --- PASTE YOUR HUGGING FACE TOKEN BELOW ---
    # Get a free token at: https://huggingface.co/settings/tokens
    custom_token = "YOUR_HUGGING_FACE_TOKEN_HERE"
    
    # Do not change anything below this line
    hf_token = custom_token if custom_token != "PASTE_YOUR_TOKEN_HERE" else os.environ.get("HF_TOKEN")

    if not os.path.exists(SAVE_PATH):
        os.makedirs(SAVE_PATH)
        
    print(f"Starting download of {MODEL_ID}...")
    print(f"Target path: {SAVE_PATH}")
    
    if not hf_token:
        print("Tip: If you get '429 Too Many Requests', paste your token inside the download_model.py script.")

    try:
        # Download the entire repository efficiently
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=SAVE_PATH,
            local_dir_use_symlinks=False,
            token=hf_token
        )
        print("\nSuccess! The model files have been downloaded to the 'model' folder.")
        print("You can now run 'python main.py' to start the service.")
    except Exception as e:
        print(f"\nError during download: {e}")
        if "429" in str(e):
            print("\nHugging Face is rate-limiting your connection.")
            print("Please create a free token at https://huggingface.co/settings/tokens")
            print("Then run: $env:HF_TOKEN='your_token_here'; python download_model.py")


if __name__ == "__main__":
    main()

