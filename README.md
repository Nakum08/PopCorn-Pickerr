# 🍿 PoPCorn Picker

A content-based movie recommendation web app built with **Python + Flask** and a **cosine similarity ML model**. Search any movie and instantly get personalized recommendations, cast details, user reviews with sentiment analysis, and an official YouTube trailer — all without needing a VPN.

---

## 📸 Features

- 🔍 **Movie Search** — Type a movie name and get 10 diverse recommendations instantly
- 🎭 **Cast Details** — View top cast with photos, biography, birthday, and birthplace
- 🎬 **Official Trailer** — Embedded YouTube trailer fetched automatically
- 😄 **Sentiment Reviews** — IMDB user reviews classified as Good/Bad using a trained NLP model
- 🤝 **Watch Together** — Enter two movies and get recommendations that satisfy both tastes
- ⚡ **Fast** — All heavy ML work happens server-side; browser makes just 1–2 network calls
- 🇮🇳 **Works in India** — Uses OMDb API instead of TMDB (no VPN required)

---

## 🗂️ Project Structure

```
minorProject/
│
├── templates/                  # Jinja2 HTML templates
│   ├── home.html               # Main search page
│   ├── dual.html               # Watch Together page
│   └── recommend.html          # Results page (poster, cast, reviews, trailer)
│
├── static/                     # Frontend assets
│   ├── autocomplete.js         # Movie name autocomplete
│   ├── recommend.js            # Search & dual-recommend logic
│   ├── home.css                # Home page styles
│   ├── img1.jpg – img10.jpeg   # Carousel background images
│   └── ...
│
├── datasets/                   # Raw source datasets (used during preprocessing only)
│
├── main.py                     # ⭐ Flask app — run this to start the server
├── main_data.csv               # ✅ REQUIRED — processed movie dataset used by the ML model
├── nlp_model.pkl               # ✅ REQUIRED — trained Naive Bayes sentiment classifier
├── tranform.pkl                # ✅ REQUIRED — TF-IDF vectorizer for sentiment model
│
└── README.md
```

---

## ✅ Required Files (DO NOT DELETE)

| File | Purpose |
|------|---------|
| `main.py` | Flask application — the entry point |
| `main_data.csv` | Processed movie dataset for the ML similarity model |
| `nlp_model.pkl` | Trained NLP model for review sentiment analysis |
| `tranform.pkl` | TF-IDF vectorizer paired with `nlp_model.pkl` |
| `templates/` | All HTML pages |
| `static/` | JS, CSS, and carousel images |



---

## 🚀 How to Run Locally

### 1. Prerequisites

Make sure you have **Python 3.8 or higher** installed.

```bash
python --version
```

### 2. Clone or Download the Project

```bash
git clone <your-repo-url>
cd minorProject
```

### 3. Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install flask numpy pandas scikit-learn requests beautifulsoup4 lxml
```

**Optional** (for better IMDB review scraping):
```bash
pip install cloudscraper
```

**Full install in one command:**
```bash
pip install flask numpy pandas scikit-learn requests beautifulsoup4 lxml cloudscraper
```

### 5. Get Your Own OMDb API Key (Free) (Optional)

The app uses OMDb to fetch movie posters and details. The default key has a 1,000 req/day limit shared with others.

1. Go to [https://www.omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)
2. Register for the **FREE** tier (1,000 requests/day)
3. Open `main.py` and replace the key on line 27:

```python
OMDB_KEY = 'your_key_here'
```

### 6. Run the App

```bash
python main.py
```

You should see:
```
[Boot] Building similarity matrix…
[Boot] Done.
 * Running on http://127.0.0.1:5000
```

### 7. Open in Browser

Go to: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📦 All Dependencies at a Glance

```
flask
numpy
pandas
scikit-learn
requests
beautifulsoup4
lxml
cloudscraper       # optional
```

Or save as `requirements.txt` and run `pip install -r requirements.txt`.

---

## 🌐 API Keys Used

| API | Used For | Free Tier | Required? |
|-----|----------|-----------|-----------|
| [OMDb](https://www.omdbapi.com/) | Movie poster, plot, rating, runtime | 1,000/day | ✅ Yes |
| [TMDB](https://www.themoviedb.org/) | Cast images & bios | 1M/month | ⚠️ Optional (blocked in India without VPN) |

> **India users:** TMDB is blocked by most ISPs in India. The app works fully without it — I implemented multiple API fallback calls to handle regional API restrictions. If one endpoint fails, the system automatically retries with alternative endpoints and gracefully handles failure by returning a null response. So it can work without any use if VPN..

---

## 🧠 How the ML Model Works

1. **Dataset** — `main_data.csv` contains ~10,000 movies with columns: `movie_title`, `director_name`, `actor_1_name`, `actor_2_name`, `actor_3_name`, `genres`, `comb`
2. **Vectorization** — `CountVectorizer` converts the `comb` column (actors + director + genres) into a count matrix
3. **Similarity** — `cosine_similarity` computes a pairwise similarity score between all movies
4. **Recommendation** — Top 10 most similar movies are returned, filtered to avoid franchise repetition
5. **Sentiment** — User reviews from TMDB are classified as Good/Bad using a trained `MultinomialNB` model (`nlp_model.pkl`) with TF-IDF features (`tranform.pkl`)

---

## 🤝 Watch Together Feature

Enter two movie titles and the app blends their similarity vectors to find movies that satisfy both preferences, filtered to avoid movies from the same franchise as either input.

---

## 🐛 Common Issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: flask` | Run `pip install flask` |
| `FileNotFoundError: nlp_model.pkl` | Make sure you're running `python main.py` from the project root folder |
| Movie not found | The movie title must be in `main_data.csv` — use the autocomplete dropdown |
| No poster showing | Your OMDb API key may be rate-limited — get a free personal key at omdbapi.com |
| Cast not showing | TMDB is blocked on your network — change DNS or use a VPN |
| `AttributeError: 'Flask' object has no attribute 'before_first_request'` | You have an old `main.py` — replace it with the latest version |

---

## 📄 License

This project was built as a Minor Project / Capstone for academic submission.

---

## 👩‍💻 Made By

**Sanjana Nakum** — © 2026
