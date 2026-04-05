import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import requests as req
from concurrent.futures import ThreadPoolExecutor
import threading
import re

# ── Cloudscraper (optional, used only if available to bypass some scraping restrictions) ─────────────────
try:
    import cloudscraper
    # Create a scraper that behaves like a normal browser
    _scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    USE_CLOUDSCRAPER = True
except ImportError:
    # If not installed, just skip it and fall back to normal requests
    USE_CLOUDSCRAPER = False

# ── Load trained NLP model and vectorizer (used for review sentiment classification) ─────────────────
clf        = pickle.load(open('nlp_model.pkl', 'rb'))
vectorizer = pickle.load(open('tranform.pkl', 'rb'))

# ── API Keys (these power movie data + images) ──────────────────────────────────────────────────
OMDB_KEY    = '9e1d1948'  # Free OMDb API (limited requests per day)
TMDB_KEY    = 'e7d0426c5b557ced5863b495eea3ffc5'  # Used mainly for cast details/images
IMG_BASE    = 'https://image.tmdb.org/t/p/original'
PLACEHOLDER = 'https://via.placeholder.com/300x450?text=No+Poster'  # Fallback if no poster found

# ── Shared HTTP session (reuses connections, faster than creating new ones every time) ─────────────────
_session = req.Session()
_session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})

# ── Similarity matrix cache (expensive to compute, so we store it once and reuse) ────────────
_sim_lock  = threading.Lock()
_sim_cache = {}

def get_similarity():
    # Thread-safe loading so multiple requests don’t rebuild the matrix
    with _sim_lock:
        if not _sim_cache:
            print("[Boot] Building similarity matrix…")
            data   = pd.read_csv('main_data.csv')
            cv     = CountVectorizer()
            # Convert text into vectors and compute similarity between all movies
            matrix = cosine_similarity(cv.fit_transform(data['comb']))
            _sim_cache['data']   = data
            _sim_cache['matrix'] = matrix
            print("[Boot] Done.")
        return _sim_cache['data'], _sim_cache['matrix']

def get_suggestions():
    # Used for autocomplete suggestions on frontend
    data, _ = get_similarity()
    return list(data['movie_title'].str.capitalize())

# ── OMDb API helpers (main movie info source, works without VPN in India) ────────────────────────────
def omdb_get(params):
    try:
        params['apikey'] = OMDB_KEY
        r = _session.get('https://www.omdbapi.com/', params=params, timeout=8)
        if r.status_code == 200:
            d = r.json()
            if d.get('Response') == 'True':
                return d
    except Exception as e:
        print(f"[OMDb] failed: {e}")
    return {}

def omdb_search(title):
    # Fetch full movie details using title
    return omdb_get({'t': title, 'plot': 'full', 'type': 'movie'})

def fetch_rec_poster(title):
    # Get poster for recommended movies
    d = omdb_search(title)
    p = d.get('Poster', '')
    return p if (p and p != 'N/A') else PLACEHOLDER

def parse_runtime(rt):
    # Convert runtime like "142 min" → "2 hour(s) 22 min(s)"
    try:
        mins = int(re.sub(r'[^\d]', '', rt))
        return f"{mins//60} hour(s) {mins%60} min(s)" if mins % 60 else f"{mins//60} hour(s)"
    except Exception:
        return rt  # fallback if parsing fails

# ── TMDB helpers (used mainly for cast + reviews, might be blocked without VPN) ──
TMDB_BASES = ['https://api.themoviedb.org/3', 'https://api.tmdb.org/3']

def tmdb_get(path, extra=None):
    # Try multiple base URLs in case one fails
    params = {'api_key': TMDB_KEY}
    if extra:
        params.update(extra)
    for base in TMDB_BASES:
        try:
            fetch = _scraper.get if USE_CLOUDSCRAPER else _session.get
            r = fetch(f'{base}{path}', params=params, timeout=2)  # short timeout to avoid delays
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return {}

def fetch_trailer(title, year=''):
    # Scrapes YouTube search results to extract trailer video ID (no API key needed)
    try:
        from urllib.parse import quote
        query = f"{title} {year} official trailer"
        url   = f"https://www.youtube.com/results?search_query={quote(query.strip())}"
        r     = _session.get(url, timeout=5)
        if r.status_code == 200:
            match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"[Trailer] failed: {e}")
    return None

def fetch_tmdb_data(movie_title):
    """
    Fetch cast, cast bios, and reviews for a movie using TMDB.
    Uses parallel requests to keep things fast.
    """
    try:
        d       = tmdb_get('/search/movie', {'query': movie_title})
        results = d.get('results', [])
        if not results:
            return {}, {}, {}

        movie_id = results[0]['id']

        # Fetch credits and reviews in parallel
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_credits = ex.submit(tmdb_get, f'/movie/{movie_id}/credits')
            f_reviews = ex.submit(tmdb_get, f'/movie/{movie_id}/reviews')
            credits_data = f_credits.result()
            reviews_data = f_reviews.result()

        cast_list = credits_data.get('cast', [])[:10]

        # Fetch additional details for each cast member
        def get_bio(person_id):
            p = tmdb_get(f'/person/{person_id}')
            bday = p.get('birthday') or ''
            try:
                bday = pd.Timestamp(bday).strftime('%b %d, %Y') if bday else 'N/A'
            except Exception:
                bday = 'N/A'
            return {'bday': bday, 'bio': p.get('biography',''), 'place': p.get('place_of_birth','N/A') or 'N/A'}

        bios = {}
        if cast_list:
            # Parallel fetch for all cast bios
            with ThreadPoolExecutor(max_workers=10) as ex:
                bio_futures = {ex.submit(get_bio, c['id']): i for i, c in enumerate(cast_list)}
                bios = {idx: f.result() for f, idx in bio_futures.items()}

        # Build structured cast data
        casts, cast_details = {}, {}
        for i, c in enumerate(cast_list):
            name    = c['name']
            char    = c.get('character', '')
            profile = (IMG_BASE + c['profile_path']) if c.get('profile_path') else PLACEHOLDER
            b       = bios.get(i, {})
            casts[name]        = [str(c['id']), char, profile]
            cast_details[name] = [str(c['id']), profile, b.get('bday','N/A'), b.get('place','N/A'), b.get('bio','')]

        # Process reviews and classify sentiment using ML model
        reviews = {}
        for r in reviews_data.get('results', [])[:10]:
            text = r.get('content', '').strip()
            if len(text) > 30:
                pred = clf.predict(vectorizer.transform(np.array([text])))
                reviews[text] = 'Good' if pred else 'Bad'
        print(f"[Reviews] {len(reviews)} from TMDB")

        return casts, cast_details, reviews

    except Exception as e:
        print(f"[TMDB fetch] failed: {e}")
        return {}, {}, {}

# ── Recommendation logic using cosine similarity ────────────────────────────────────────
def rcmd(m):
    data, sim = get_similarity()
    m = m.lower()
    if m not in data['movie_title'].unique():
        return None
    i   = data.loc[data['movie_title'] == m].index[0]
    lst = sorted(enumerate(sim[i]), key=lambda x: x[1], reverse=True)[1:11]
    return [data['movie_title'][a] for a, _ in lst]

def dual_rcmd(m1, m2):
    # Combine recommendations from two movies
    data, sim = get_similarity()
    m1, m2    = m1.lower(), m2.lower()
    if m1 not in data['movie_title'].values or m2 not in data['movie_title'].values:
        return []
    i1, i2   = data[data['movie_title']==m1].index[0], data[data['movie_title']==m2].index[0]
    s1, s2   = sim[i1], sim[i2]
    combined = (s1 + s2) / 2

    lst = sorted(enumerate(combined), key=lambda x: (-x[1], abs(s1[x[0]]-s2[x[0]])))
    result, used = [], set()
    for idx, _ in lst:
        name = data.iloc[idx].movie_title.lower()
        if name in [m1, m2]: continue
        kw = name.split()[0]
        if kw in m1 or kw in m2 or kw in used: continue
        used.add(kw); result.append(name)
        if len(result) == 10: break
    return result

# ── Main data builder (ties everything together) ──────────────────────────────
def build_movie_data(title):
    data, _ = get_similarity()

    # Normalize input
    title_lower = title.lower().strip()
    matched_title = None

    # Try exact match first
    if title_lower in data['movie_title'].values:
        matched_title = title_lower
    else:
        # If not exact, try partial match
        matches = data[data['movie_title'].str.contains(title_lower, case=False, na=False)]
        if not matches.empty:
            matched_title = matches.iloc[0]['movie_title']

    # Get recommendations
    rec_list = []
    if matched_title:
        rec_list = rcmd(matched_title) or []

    # Fetch movie details
    display_title = matched_title.title() if matched_title else title
    movie_data = omdb_search(display_title) or omdb_search(title) or {}

    poster_url  = movie_data.get('Poster', PLACEHOLDER)
    if not poster_url or poster_url == 'N/A':
        poster_url = PLACEHOLDER

    imdb_id = movie_data.get('imdbID', '')

    # If nothing found at all
    if not movie_data and not matched_title:
        return None

    # Parallel fetching (posters, cast, trailer)
    with ThreadPoolExecutor(max_workers=20) as ex:
        f_posters  = {ex.submit(fetch_rec_poster, m): m for m in rec_list}
        f_tmdb     = ex.submit(fetch_tmdb_data, display_title)
        f_trailer  = ex.submit(fetch_trailer, display_title, movie_data.get('Year', ''))

        rec_posters_map                    = {movie: fut.result() for fut, movie in f_posters.items()}
        casts, cast_details, movie_reviews = f_tmdb.result()
        try:
            trailer_id = f_trailer.result(timeout=6)
        except Exception:
            trailer_id = None

    movie_cards = {rec_posters_map.get(m, PLACEHOLDER): m for m in rec_list}

    # Final structured response sent to frontend
    return {
        'title':        movie_data.get('Title', display_title),
        'poster':       poster_url,
        'overview':     movie_data.get('Plot', 'N/A'),
        'vote_average': movie_data.get('imdbRating', 'N/A'),
        'vote_count':   movie_data.get('imdbVotes', 'N/A'),
        'release_date': movie_data.get('Released', movie_data.get('Year', 'N/A')),
        'runtime':      parse_runtime(movie_data.get('Runtime', '')),
        'status':       'Released' if movie_data.get('Year') else 'N/A',
        'genres':       movie_data.get('Genre', 'N/A'),
        'movie_cards':  movie_cards,
        'reviews':      movie_reviews,
        'casts':        casts,
        'cast_details': cast_details,
        'trailer_id':   trailer_id,
    }

# ── Flask app setup ─────────────────────────────────────────────────────
app = Flask(__name__)

# Preload similarity matrix in background so first request isn’t slow
with app.app_context():
    threading.Thread(target=get_similarity, daemon=True).start()

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', suggestions=get_suggestions())

@app.route("/dual")
def dual_page():
    return render_template("dual.html", suggestions=get_suggestions())

@app.route("/search", methods=["POST"])
def search():
    title = request.form.get('title', '').strip()
    if not title:
        return "NOT_FOUND", 200
    data = build_movie_data(title)
    if not data:
        return "NOT_FOUND", 200
    return render_template('recommend.html', **data)

@app.route("/dual_recommend", methods=["POST"])
def dual_recommend():
    m1 = request.form.get('movie1', '')
    m2 = request.form.get('movie2', '')
    rc = dual_rcmd(m1, m2)
    return "---".join(rc) if rc else "NOT_FOUND"

@app.route("/poster")
def poster():
    title = request.args.get('title', '')
    return jsonify({'poster': fetch_rec_poster(title)})

if __name__ == '__main__':
    # Debug mode on for development (don’t use in production unless you enjoy chaos)
    app.run(debug=True)