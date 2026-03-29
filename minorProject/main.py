import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import bs4 as bs
import urllib.request
import pickle
import http.client
from urllib.parse import urlparse
import requests as req
import os

# Force requests to use Cloudflare DNS-over-HTTPS to bypass ISP-level DNS blocking
# This helps when api.themoviedb.org is blocked in India
os.environ['REQUESTS_CA_BUNDLE'] = ''  # Use system certs

# Load the NLP model and TF-IDF vectorizer from disk
filename = 'nlp_model.pkl'
clf = pickle.load(open(filename, 'rb'))
vectorizer = pickle.load(open('tranform.pkl', 'rb'))


def create_similarity():
    data = pd.read_csv('main_data.csv')
    # Creating a count matrix
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(data['comb'])
    # Creating a similarity score matrix
    similarity = cosine_similarity(count_matrix)
    return data, similarity


def rcmd(m, data=None, similarity=None):
    m = m.lower()
    try:
        data.head()
        similarity.shape
    except:
        data, similarity = create_similarity()
    if m not in data['movie_title'].unique():
        return (
            'Sorry! The movie you requested is not in our database. Please check the spelling or try with some other movies')
    else:
        i = data.loc[data['movie_title'] == m].index[0]
        lst = list(enumerate(similarity[i]))
        lst = sorted(lst, key=lambda x: x[1], reverse=True)
        lst = lst[1:11]  # Excluding first item since it is the requested movie itself
        l = []
        for i in range(len(lst)):
            a = lst[i][0]
            l.append(data['movie_title'][a])
        return l


def dual_rcmd(m1, m2):
    data, similarity = create_similarity()

    m1 = m1.lower()
    m2 = m2.lower()

    if m1 not in data['movie_title'].values or m2 not in data['movie_title'].values:
        return ["One or both movies not found"]

    i1 = data[data['movie_title'] == m1].index[0]
    i2 = data[data['movie_title'] == m2].index[0]

    sim1 = similarity[i1]
    sim2 = similarity[i2]

    combined = (sim1 + sim2) / 2

    lst = list(enumerate(combined))

    # 🔥 NEW SORTING LOGIC (balance + relevance)
    lst = sorted(lst, key=lambda x: (-x[1], abs(sim1[x[0]] - sim2[x[0]])))

    result = []
    used_keywords = set()

    for i in range(len(lst)):
        idx = lst[i][0]
        movie_name = data.iloc[idx].movie_title.lower()

        # ❌ skip same movies
        if movie_name in [m1, m2]:
            continue

        # 🔥 get first word (simple franchise detector)
        keyword = movie_name.split()[0]

        # ❌ skip if same franchise keyword
        if keyword in m1 or keyword in m2:
            continue

        # ❌ avoid repeating same type again
        if keyword in used_keywords:
            continue

        used_keywords.add(keyword)
        result.append(movie_name)

        if len(result) == 10:
            break
        if len(result) == 10:
            break

    return result


# Converting list of strings to list (e.g., "["abc","def"]" to ["abc","def"])
def convert_to_list(my_list):
    my_list = my_list.split('","')
    my_list[0] = my_list[0].replace('["', '')
    my_list[-1] = my_list[-1].replace('"]', '')
    return my_list


def get_suggestions():
    data = pd.read_csv('main_data.csv')
    return list(data['movie_title'].str.capitalize())


app = Flask(__name__)


@app.route("/")
@app.route("/home")
def home():
    suggestions = get_suggestions()
    return render_template('home.html', suggestions=suggestions)


@app.route("/similarity", methods=["POST"])
def similarity():
    movie = request.form['name']
    rc = rcmd(movie)
    if type(rc) == type('string'):
        return rc
    else:
        m_str = "---".join(rc)
        return m_str


@app.route("/test_dual")
def test_dual():
    result = dual_rcmd(
        "avengers: age of ultron",
        "harry potter and the half-blood prince"
    )
    return str(result)


@app.route("/dual")
def dual_page():
    suggestions = get_suggestions()
    return render_template("dual.html", suggestions=suggestions)


@app.route("/dual_recommend", methods=["POST"])
def dual_recommend():
    movie1 = request.form['movie1']
    movie2 = request.form['movie2']

    rc = dual_rcmd(movie1, movie2)

    return "---".join(rc)


@app.route("/recommend", methods=["POST"])
def recommend():
    # Getting data from AJAX request
    title = request.form['title']
    cast_ids = request.form['cast_ids']
    cast_names = request.form['cast_names']
    cast_chars = request.form['cast_chars']
    cast_bdays = request.form['cast_bdays']
    cast_bios = request.form['cast_bios']
    cast_places = request.form['cast_places']
    cast_profiles = request.form['cast_profiles']
    imdb_id = request.form['imdb_id']
    poster = request.form['poster']
    genres = request.form['genres']
    overview = request.form['overview']
    vote_average = request.form['rating']
    vote_count = request.form['vote_count']
    release_date = request.form['release_date']
    runtime = request.form['runtime']
    status = request.form['status']
    rec_movies = request.form['rec_movies']
    rec_posters = request.form['rec_posters']

    # Get movie suggestions for auto-complete
    suggestions = get_suggestions()

    # Call the convert_to_list function for every string that needs to be converted to list
    rec_movies = convert_to_list(rec_movies)
    rec_posters = convert_to_list(rec_posters)
    cast_names = convert_to_list(cast_names)
    cast_chars = convert_to_list(cast_chars)
    cast_profiles = convert_to_list(cast_profiles)
    cast_bdays = convert_to_list(cast_bdays)
    cast_bios = convert_to_list(cast_bios)
    cast_places = convert_to_list(cast_places)

    # Convert string to list (e.g., "[1,2,3]" to [1,2,3])
    cast_ids = cast_ids.split(',')
    cast_ids[0] = cast_ids[0].replace("[", "")
    cast_ids[-1] = cast_ids[-1].replace("]", "")

    # Rendering the string to python string
    for i in range(len(cast_bios)):
        cast_bios[i] = cast_bios[i].replace(r'\n', '\n').replace(r'\"', '\"')

    # Combining multiple lists as a dictionary which can be passed to the HTML file
    movie_cards = {rec_posters[i]: rec_movies[i] for i in range(len(rec_posters))}
    casts = {cast_names[i]: [cast_ids[i], cast_chars[i], cast_profiles[i]] for i in range(len(cast_profiles))}
    cast_details = {cast_names[i]: [cast_ids[i], cast_profiles[i], cast_bdays[i], cast_places[i], cast_bios[i]] for i in
                    range(len(cast_places))}

    # Web scraping to get user reviews from IMDb using requests with headers
    movie_reviews = {}
    try:
        imdb_url = f'https://www.imdb.com/title/{imdb_id}/reviews?ref_=tt_ov_rt'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        response = req.get(imdb_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = bs.BeautifulSoup(response.content, 'lxml')
            # Try new IMDB structure first, fallback to old
            soup_result = soup.find_all("div", {"class": "text show-more__control"})
            if not soup_result:
                soup_result = soup.find_all("div", {"class": "ipc-html-content-inner-div"})

            reviews_list = []
            reviews_status = []
            for review in soup_result:
                text = review.get_text(strip=True)
                if text and len(text) > 20:
                    reviews_list.append(text)
                    movie_review_list = np.array([text])
                    movie_vector = vectorizer.transform(movie_review_list)
                    pred = clf.predict(movie_vector)
                    reviews_status.append('Good' if pred else 'Bad')

            movie_reviews = {reviews_list[i]: reviews_status[i] for i in range(len(reviews_list))}
    except Exception as e:
        print(f"Review scraping failed: {e}")
        movie_reviews = {}

    # Passing all the data to the HTML file
    return render_template('recommend.html', title=title, poster=poster, overview=overview, vote_average=vote_average,
                           vote_count=vote_count, release_date=release_date, runtime=runtime, status=status,
                           genres=genres,
                           movie_cards=movie_cards, reviews=movie_reviews, casts=casts, cast_details=cast_details)


# ══════════════════════════════════════════════════════════
#  TMDB PROXY ROUTES
#  Uses alternative hostnames + custom DNS to bypass blocks
# ══════════════════════════════════════════════════════════

TMDB_KEY = 'e7d0426c5b557ced5863b495eea3ffc5'

# TMDB has multiple accessible base URLs - try each until one works
TMDB_BASES = [
    'https://api.themoviedb.org/3',
    'https://api.tmdb.org/3',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}


def tmdb_get(path, params=None):
    """Try each TMDB base URL until one succeeds."""
    if params is None:
        params = {}
    params['api_key'] = TMDB_KEY

    last_error = None
    for base in TMDB_BASES:
        try:
            r = req.get(
                f'{base}{path}',
                params=params,
                headers=HEADERS,
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            last_error = e
            continue

    # All bases failed — return empty structure so frontend handles gracefully
    print(f"TMDB unreachable: {last_error}")
    return {'results': [], 'error': 'TMDB unreachable'}


@app.route('/tmdb/search')
def tmdb_search():
    query = request.args.get('query', '')
    data = tmdb_get('/search/movie', {'query': query})
    return jsonify(data)


@app.route('/tmdb/movie/<int:movie_id>')
def tmdb_movie(movie_id):
    data = tmdb_get(f'/movie/{movie_id}')
    return jsonify(data)


@app.route('/tmdb/movie/<int:movie_id>/credits')
def tmdb_credits(movie_id):
    data = tmdb_get(f'/movie/{movie_id}/credits')
    return jsonify(data)


@app.route('/tmdb/person/<int:person_id>')
def tmdb_person(person_id):
    data = tmdb_get(f'/person/{person_id}')
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)