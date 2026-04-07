# Firebase Setup Guide for Visilink

## Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Add project"
3. Project name: `visilink`
4. Disable Google Analytics (optional)
5. Click "Create project"

## Step 2: Create Firestore Database

1. In Firebase Console, go to **Build** → **Firestore Database**
2. Click **Create database**
3. Select **Start in test mode** (easier for development)
4. Choose region: `e.g., us-central1`
5. Click **Create**

Your database is now ready! No tables needed - Firestore is NoSQL.

## Step 3: Get Service Account Credentials

1. Go to **Project Settings** (gear icon, top-left)
2. Go to **Service Accounts** tab
3. Click **Generate New Private Key**
4. Save the JSON file as `serviceAccountKey.json` in your `backend/` folder

⚠️ **IMPORTANT:** This file is in `.gitignore` - never commit it to GitHub!

## Step 4: Update Environment Variables

### Option A: Using Service Account File (Local Development)
- Place `serviceAccountKey.json` in `backend/` folder
- Leave `FIREBASE_CREDENTIALS` empty in `.env`

### Option B: Using Environment Variable (Production/GitHub)
- Open the downloaded `serviceAccountKey.json`
- Copy the entire JSON content
- In your `.env` file, add:
```
FIREBASE_CREDENTIALS=<paste-entire-json-here-as-one-line>
```

## Step 5: Update .env File

On your local machine, create `backend/.env`:
```
# Use either serviceAccountKey.json OR FIREBASE_CREDENTIALS env var
FIREBASE_CREDENTIALS=
GEMINI_API_KEY=your_actual_gemini_key_here
```

## Step 6: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 7: Test Locally

```bash
cd backend
uvicorn main:app --reload
```

Go to `http://localhost:8000/docs` - if it loads, Firebase is connected! ✅

## Step 8: Push to GitHub

```bash
cd "c:/Users/ASUS/Desktop/NLP Project"
git add .
git commit -m "Set up Firebase database integration"
git push origin main
```

## Step 9: Deploy (After Configuration)

You can now deploy to:
- **Render.com** (Backend)
- **Vercel** (Frontend)
- **Railway** (Full stack)
- **Google Cloud Run** (Backend)

---

## Troubleshooting

### Firebase Credentials Not Working
- Check `FIREBASE_CREDENTIALS` is valid JSON
- Confirm service account has "Cloud Datastore User" role
- Check Firestore Database > Rules (should allow in test mode)

### Connection Refused
- Ensure Firebase Admin SDK is installed: `pip install firebase-admin`
- Check internet connection
- Verify project ID is correct

### Data Not Saving
- Check Firestore Database > Data tab - documents should appear
- Verify CORS is set correctly in `main.py`
