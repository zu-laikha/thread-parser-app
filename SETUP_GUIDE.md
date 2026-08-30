# Thread Parser App - Setup Guide

## Quick Start (Next Time You Open the Project)

### Step 1: Start the Backend
```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
✅ The backend will respond with: `Uvicorn running on http://0.0.0.0:8000`

### Step 2: Start the Frontend (In a New Terminal)
```powershell
cd frontend
npm.cmd start -- --clear
```
✅ The frontend will show a QR code and say: `Web is waiting on http://localhost:8081`

### Step 3: Open the Web App
Navigate to http://localhost:8081 in your browser

---

## What Changed in This Session

### 🔴 Critical: Canonical URL Normalization
**File:** `backend/main.py`
- Added `normalize_threads_url()` function
- When you paste a Threads **share link** (e.g., `https://www.threads.com/share/BAVhRUmY1E/`), the backend now:
  1. Fetches the share link page
  2. Extracts the canonical post URL from the `<link rel="canonical">` tag
  3. Uses the canonical URL to fetch full metadata and images

**Why this matters:** Share links only preview 1 image. The canonical URL exposes the full gallery.

### 🟢 OCR Fallback for Generic Metadata
**File:** `backend/main.py`
- When a post's metadata is generic (just emoji, "Threads Post", etc.)
- The backend OCRs the image to extract real content (prices, locations, etc.)
- This is how promo catalogues get classified as "Promo / Groceries"

### 🟡 Multi-Image Carousel
**File:** `frontend/src/app/index.tsx`
- Backend now returns both `image_url` and `image_urls` array
- Frontend renders a horizontally scrollable carousel showing all images
- Users can swipe through multiple photos from the post

### 🟠 Fixed React Native Web Warnings
**File:** `frontend/src/app/index.tsx`
- Removed unsupported `gap` properties from StyleSheet
- Replaced with explicit `marginTop`/`marginRight` for RN Web compatibility
- No more "createDOMProps" warnings in the browser console

### 🔵 API URL Configuration
**File:** `frontend/.env`
- Changed from LAN IP (`192.168.100.95:8000`) to localhost (`127.0.0.1:8000`)
- This allows local browser testing
- If testing on phone with Expo Go, change back to your computer's LAN IP

---

## Key Implementation Details

### Backend Flow (for Threads URLs)
```
User pastes URL
  ↓
normalize_threads_url()
  ├─ If it's a share URL, extract canonical post URL
  └─ Return canonical URL (or original if not a share link)
  ↓
fetch_open_graph(canonical_url)
  ├─ Extract HTML metadata (og:title, og:description, og:image)
  ├─ Extract all images from meta tags
  ↓
looks_like_generic_threads_text()
  ├─ If metadata looks generic (empty, just emoji, "Threads Post")
  └─ Call OCR on the primary image to extract real text
  ↓
summarize_with_gemini()
  ├─ Send extracted text + all image URLs to Gemini
  ├─ Returns structured JSON (category, subcategory, title, etc.)
  └─ Returns both image_url (first) and image_urls (all)
```

### Frontend Flow
```
User enters URL → Calls /parse endpoint
  ↓
Backend returns ParsedPost with:
  - category, subcategory, title
  - image_url (first image)
  - image_urls (all images)
  ↓
If image_urls.length > 1:
  - Render horizontal ScrollView carousel
  - Show all images with swipe capability
Else if image_url:
  - Show single image
```

---

## Running Tests

To verify the canonical URL and OCR logic are working:

```powershell
cd backend
python -m unittest test_threads_parser
```

✅ Expected output: `Ran 2 tests in 0.002s - OK`

The tests verify:
1. **Canonical URL normalization** - Share URLs are converted to post URLs
2. **OCR fallback** - Generic metadata triggers image text extraction

---

## Troubleshooting

### "Failed to fetch"
- ❌ Backend is not running → Start it with `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
- ❌ Frontend .env points to wrong IP → Verify `EXPO_PUBLIC_API_URL=http://127.0.0.1:8000`
- ❌ Port 8000 is already in use → Kill the process using it or use a different port

### Only 1 photo showing
- This should now be fixed by canonical URL normalization
- If it still happens, check:
  1. Backend logs to see if `normalize_threads_url()` is converting the share URL
  2. Verify the backend is actually calling the normalized URL
  3. Check if the canonical URL page has more images

### No text extracted from promo image
- The backend might not have a valid GEMINI_API_KEY in `backend/.env`
- Verify `GEMINI_API_KEY` is set and valid
- Check backend logs for API errors

### React Native Web warnings
- All `gap` properties should be removed
- Use explicit margins instead
- If warnings persist, check the browser console

---

## Environment Files

### `backend/.env`
```
GEMINI_API_KEY=your_api_key_here
```

### `frontend/.env`
```
# For local browser testing:
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000

# For phone testing with Expo Go:
# EXPO_PUBLIC_API_URL=http://YOUR_COMPUTER_LAN_IP:8000
```

---

## Important Notes

1. **The canonical URL fix is the key to multi-photo posts**
   - Without it, Threads share links only show the preview image
   - With it, the app gets the full gallery from the canonical post

2. **Both backend and frontend must be running**
   - Backend: http://0.0.0.0:8000
   - Frontend: http://localhost:8081 (web) or Expo Go (phone)

3. **Tests validate the core logic**
   - Run them after any changes to ensure the normalization and OCR still work

4. **The carousel requires multiple images**
   - Single-image posts show one image
   - Multi-image posts show a swipeable carousel
   - Check `image_urls` array length in the parsed response

---

## Next Steps (Future Improvements)

- [ ] Add loading spinner while parsing
- [ ] Cache parsed results by canonical URL
- [ ] Add error retry logic
- [ ] Support more platforms (not just Threads)
- [ ] Add offline mode
- [ ] Improve UI styling and polish
