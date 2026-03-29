import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import bs4 as bs
import pickle
import requests as req
from concurrent.futures import ThreadPoolExecutor
import threading
import re

# ── Cloudscraper (optional, for IMDB reviews) ─────────────────
try:
    import cloudscraper
    _scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    USE_CLOUDSCRAPER = True
except ImportError:
    USE_CLOUDSCRAPER = False

# ── NLP model ─────────────────────────────────────────────────
clf        = pickle.load(open('nlp_model.pkl', 'rb'))
vectorizer = pickle.load(open('tranform.pkl', 'rb'))

# ── API Keys ──────────────────────────────────────────────────
OMDB_KEY    = '9e1d1948'  # ⚠️ Get your own FREE key at https://www.omdbapi.com/apikey.aspx (1000 req/day free)
TMDB_KEY    = 'e7d0426c5b557ced5863b495eea3ffc5'  # for cast images only (browser fetches these)
IMG_BASE    = 'https://image.tmdb.org/t/p/original'
PLACEHOLDER = 'https://via.placeholder.com/300x450?text=No+Poster'

# ── HTTP session ──────────────────────────────────────────────
_session = req.Session()
_session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})

# ── Similarity matrix — built once, kept in memory ────────────
_sim_lock  = threading.Lock()
_sim_cache = {}

def get_similarity():
    with _sim_lock:
        if not _sim_cache:
            print("[Boot] Building similarity matrix…")
            data   = pd.read_csv('main_data.csv')
            cv     = CountVectorizer()
            matrix = cosine_similarity(cv.fit_transform(data['comb']))
            _sim_cache['data']   = data
            _sim_cache['matrix'] = matrix
            print("[Boot] Done.")
        return _sim_cache['data'], _sim_cache['matrix']

def get_suggestions():
    data, _ = get_similarity()
    return list(data['movie_title'].str.capitalize())

# ── OMDb (works in India, no VPN) ────────────────────────────
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
    return omdb_get({'t': title, 'plot': 'full', 'type': 'movie'})

def fetch_rec_poster(title):
    d = omdb_search(title)
    p = d.get('Poster', '')
    return p if (p and p != 'N/A') else PLACEHOLDER

def parse_runtime(rt):
    try:
        mins = int(re.sub(r'[^\d]', '', rt))
        return f"{mins//60} hour(s) {mins%60} min(s)" if mins % 60 else f"{mins//60} hour(s)"
    except Exception:
        return rt

# ── TMDB — only for cast (blocked in India — skipped to keep response fast) ──
TMDB_BASES = ['https://api.themoviedb.org/3', 'https://api.tmdb.org/3']

def tmdb_get(path, extra=None):
    params = {'api_key': TMDB_KEY}
    if extra:
        params.update(extra)
    for base in TMDB_BASES:
        try:
            fetch = _scraper.get if USE_CLOUDSCRAPER else _session.get
            r = fetch(f'{base}{path}', params=params, timeout=2)  # 2s max — fail fast
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return {}

def fetch_cast_and_bios(movie_title):
    """Try TMDB for cast — returns empty instantly if blocked (India)."""
    try:
        d = tmdb_get('/search/movie', {'query': movie_title})
        results = d.get('results', [])
        if not results:
            return {}, {}
        movie_id  = results[0]['id']
        credits   = tmdb_get(f'/movie/{movie_id}/credits')
        cast_list = credits.get('cast', [])[:10]
        if not cast_list:
            return {}, {}

        # Fetch all bios in parallel with tight timeout
        def get_bio(person_id):
            p = tmdb_get(f'/person/{person_id}')
            bday = p.get('birthday') or ''
            try:
                bday = pd.Timestamp(bday).strftime('%b %d, %Y') if bday else 'N/A'
            except Exception:
                bday = 'N/A'
            return {'bday': bday, 'bio': p.get('biography',''), 'place': p.get('place_of_birth','N/A') or 'N/A'}

        with ThreadPoolExecutor(max_workers=10) as ex:
            bio_futures = {ex.submit(get_bio, c['id']): i for i, c in enumerate(cast_list)}
            bios = {idx: f.result() for f, idx in bio_futures.items()}

        casts, cast_details = {}, {}
        for i, c in enumerate(cast_list):
            name    = c['name']
            char    = c.get('character', '')
            profile = (IMG_BASE + c['profile_path']) if c.get('profile_path') else PLACEHOLDER
            b       = bios.get(i, {})
            casts[name]        = [str(c['id']), char, profile]
            cast_details[name] = [str(c['id']), profile, b.get('bday','N/A'), b.get('place','N/A'), b.get('bio','')]

        return casts, cast_details
    except Exception:
        return {}, {}

# ── IMDB reviews ──────────────────────────────────────────────
def scrape_reviews(imdb_id):
    if not imdb_id:
        return {}
    try:
        url   = f'https://www.imdb.com/title/{imdb_id}/reviews'
        hdrs  = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        fetch = _scraper.get if USE_CLOUDSCRAPER else req.get
        r     = fetch(url, headers=hdrs, timeout=4)
        if r.status_code != 200:
            return {}
        soup   = bs.BeautifulSoup(r.content, 'lxml')
        blocks = (
            soup.find_all("div", {"class": "text show-more__control"})
            or soup.find_all("div", {"class": "ipc-html-content-inner-div"})
            or soup.find_all("div", {"data-testid": "review-overflow"})
        )
        reviews = {}
        for b in blocks:
            text = b.get_text(separator=' ', strip=True)
            if len(text) > 30:
                pred = clf.predict(vectorizer.transform(np.array([text])))
                reviews[text] = 'Good' if pred else 'Bad'
        print(f"[Reviews] {len(reviews)} scraped")
        return reviews
    except Exception as e:
        print(f"[Reviews] failed: {e}")
        return {}

# ── ML recommendations ────────────────────────────────────────
def rcmd(m):
    data, sim = get_similarity()
    m = m.lower()
    if m not in data['movie_title'].unique():
        return None
    i   = data.loc[data['movie_title'] == m].index[0]
    lst = sorted(enumerate(sim[i]), key=lambda x: x[1], reverse=True)[1:11]
    return [data['movie_title'][a] for a, _ in lst]

def dual_rcmd(m1, m2):
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

# ── Core builder ──────────────────────────────────────────────
def build_movie_data(title):
    data, _ = get_similarity()

    # Step 1: find the movie title in CSV (lowercase match)
    title_lower = title.lower().strip()
    matched_title = None

    # Exact match first
    if title_lower in data['movie_title'].values:
        matched_title = title_lower
    else:
        # Partial / fuzzy match — find closest title in CSV
        matches = data[data['movie_title'].str.contains(title_lower, case=False, na=False)]
        if not matches.empty:
            matched_title = matches.iloc[0]['movie_title']

    # Step 2: get recommendations from CSV (works 100% offline)
    rec_list = []
    if matched_title:
        rec_list = rcmd(matched_title) or []

    # Step 3: try OMDb for poster/details — gracefully degrade if it fails
    display_title = matched_title.title() if matched_title else title
    movie_data = omdb_search(display_title) or omdb_search(title) or {}

    poster_url  = movie_data.get('Poster', PLACEHOLDER)
    if not poster_url or poster_url == 'N/A':
        poster_url = PLACEHOLDER

    imdb_id = movie_data.get('imdbID', '')

    # If OMDb failed entirely but we found the movie in CSV, still proceed
    if not movie_data and not matched_title:
        return None

    # Step 4: fetch rec posters, cast, reviews in parallel
    with ThreadPoolExecutor(max_workers=20) as ex:
        f_posters = {ex.submit(fetch_rec_poster, m): m for m in rec_list}
        f_cast    = ex.submit(fetch_cast_and_bios, display_title)
        f_reviews = ex.submit(scrape_reviews, imdb_id)

        rec_posters_map     = {movie: fut.result() for fut, movie in f_posters.items()}
        casts, cast_details = f_cast.result()
        movie_reviews       = f_reviews.result()

    movie_cards = {rec_posters_map.get(m, PLACEHOLDER): m for m in rec_list}

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
    }

# ── Flask ─────────────────────────────────────────────────────
app = Flask(__name__)

# Warm up similarity matrix on startup (Flask 2.3+ compatible)
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
    app.run(debug=True)