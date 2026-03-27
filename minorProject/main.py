import numpy as np
import pandas as pd
from flask import Flask, render_template, request
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import bs4 as bs
import urllib.request
import pickle
import http.client
from urllib.parse import urlparse

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
    cast_details = {cast_names[i]: [cast_ids[i], cast_profiles[i], cast_bdays[i], cast_places[i], cast_bios[i]] for i in range(len(cast_places))}

    # Web scraping to get user reviews from IMDb site using http.client
    parsed_url = urlparse(f'https://www.imdb.com/title/{imdb_id}/reviews?ref_=tt_ov_rt')
    conn = http.client.HTTPSConnection(parsed_url.netloc)
    conn.request("GET", parsed_url.path)

    movie_reviews = {}

    response = conn.getresponse()
    if response.status == 200:
        sauce = response.read()
        soup = bs.BeautifulSoup(sauce, 'lxml')
        soup_result = soup.find_all("div", {"class": "text show-more__control"})

        reviews_list = []  # List of reviews
        reviews_status = []  # List of comments (good or bad)
        for reviews in soup_result:
            if reviews.string:
                reviews_list.append(reviews.string)
                # Passing the review to our model
                movie_review_list = np.array([reviews.string])
                movie_vector = vectorizer.transform(movie_review_list)
                pred = clf.predict(movie_vector)
                reviews_status.append('Good' if pred else 'Bad')

        # Combining reviews and comments into a dictionary
        movie_reviews = {reviews_list[i]: reviews_status[i] for i in range(len(reviews_list))}

    conn.close()

    # Passing all the data to the HTML file
    return render_template('recommend.html', title=title, poster=poster, overview=overview, vote_average=vote_average,
                           vote_count=vote_count, release_date=release_date, runtime=runtime, status=status,
                           genres=genres,
                           movie_cards=movie_cards, reviews=movie_reviews, casts=casts, cast_details=cast_details)


if __name__ == '__main__':
    app.run(debug=True)
