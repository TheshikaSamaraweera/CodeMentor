import requests
import os
from dotenv import load_dotenv

load_dotenv()
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/paraphrase-MiniLM-L3-v2"

def verify_token():
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": "test"}
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            print("Token is valid. Response length:", len(response.json()))
            return True
        else:
            print(f"Token invalid. Status: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print(f"Token verification failed: {str(e)}")
        return False

if __name__ == "__main__":
    if not HF_API_TOKEN:
        print("Error: HUGGINGFACE_API_TOKEN not set in .env")
    else:
        verify_token()