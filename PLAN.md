# Thread Link Summarizer (MVP)

A cross-platform mobile app (targeting iOS via Expo) to parse Threads post links, extract unstructured content (promos, free courses, skincare tips), and organize key metadata (who, where, when, validity) into visual cards.

---

## 🏗 Tech Stack & Architecture

- **Mobile Frontend:** React Native + Expo (JavaScript/TypeScript)
- **Backend API:** Python (FastAPI)
- **Web Parser:** Python (`requests` + `BeautifulSoup` for Open Graph tags)
- **AI Intelligence:** Google Gemini 3.6 Flash API (Free Tier via `google-genai`)
- **Testing Device:** Personal iPhone using Expo Go app on Windows PC

---

## 🎯 MVP Feature Roadmap

### Phase 1: Environment & Project Scaffolding
- [x] Initialize React Native Expo app inside `frontend/`
- [x] Initialize Python FastAPI project inside `backend/`
- [x] Configure environment variables (`.env`) for Gemini API Key

### Phase 2: Python Backend (Parser & AI Engine)
- [x] Create `POST /parse` endpoint accepting a Threads URL
- [x] Extract Open Graph meta tags (`og:title`, `og:description`) from raw HTML
- [x] Send raw text to Gemini Flash with a JSON Schema prompt
- [x] Return clean JSON payload categorizing content (`Promo`, `Free Course`, `Review`, `Other`)

### Phase 3: React Native Frontend (Mobile UI)
- [ ] Build main screen with URL input field and paste button
- [ ] Build loading state with activity indicator during API fetch
- [ ] Create dynamic card views based on payload category:
  - `PromoCard`: Displays Title, Brand, Location, Validity Period
  - `CourseCard`: Displays Title, Niche, Mode (Online/Offline), Link
- [ ] Handle error states (e.g., invalid URLs, fetch failures)

### Phase 4: Local Storage (Optional MVP Polish)
- [ ] Save analyzed posts to phone local storage (`AsyncStorage`) so user can reference past saved items

---

## 🤖 AI Extraction JSON Target Schema

```json
{
  "category": "Property | Promo | Free Course | Review | Event | Job | Product | Service | Food | Travel | General",
  "subcategory": "Specific type of content",
  "title": "Short descriptive title",
  "brand_or_creator": "Name of brand/person",
  "location": "Location if physical event/mall, otherwise Online or N/A",
  "dates_or_validity": "When is this happening / valid until",
  "key_highlights": ["Bullet point 1", "Bullet point 2"],
  "original_url": "https://..."
}