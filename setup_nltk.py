import nltk
import os

# ✅ Use your actual AFML path instead of AppData
NLTK_DATA_PATH = r"C:\Users\Tanisha Jain\Downloads\AFML\nltk_data"
os.makedirs(NLTK_DATA_PATH, exist_ok=True)

# Tell NLTK to look here
nltk.data.path.append(NLTK_DATA_PATH)

print("⬇️ Downloading essential NLTK data...")

# Download into that path
nltk.download("punkt", download_dir=NLTK_DATA_PATH)
nltk.download("wordnet", download_dir=NLTK_DATA_PATH)
nltk.download("omw-1.4", download_dir=NLTK_DATA_PATH)

print("✅ All NLTK data downloaded successfully!")
