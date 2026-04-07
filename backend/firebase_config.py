import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Get Firebase credentials from environment variable or file
firebase_creds = os.getenv("FIREBASE_CREDENTIALS")

if firebase_creds:
    # If credentials are in environment variable (JSON string)
    cred = credentials.Certificate(json.loads(firebase_creds))
else:
    # If using credentials file
    cred = credentials.Certificate("serviceAccountKey.json")

# Initialize Firebase
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

def get_db():
    """Dummy function for compatibility with existing code"""
    return db
