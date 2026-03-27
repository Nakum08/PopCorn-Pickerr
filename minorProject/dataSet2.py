import pandas as pd
import numpy as np

meta = pd.read_csv('movies_metadata.csv')

credits = pd.read_csv('credits.csv')

meta['release_date'] = pd.to_datetime(meta['release_date'], errors='coerce')
meta['year'] = meta['release_date'].dt.year
meta['year'].value_counts().sort_index()
new_meta = meta.loc[meta.year == 2017, ['genres', 'id', 'title', 'year']]
new_meta['id'] = new_meta['id'].astype(int)

data = pd.merge(new_meta, credits, on = 'id')

pd.set_option('display.max_colwidth', 75)

# conver the genre, cast, crew columns into list

import ast

data['genres'] = data['genres'].map(lambda x: ast.literal_eval(x))
data['cast'] = data['cast'].map(lambda x: ast.literal_eval(x))
data['crew'] = data['crew'].map(lambda x: ast.literal_eval(x))

# taking individual genres

def make_genreslist(x):
    gen = []
    st = " "
    for i in x:
        if i.get('name') == 'Science Fiction':
            scifi = 'Sci-Fi'
            gen.append(scifi)
        else:
            gen.append(i.get('name'))
    if gen == []:
        return np.nan
    else:
        return (st.join(gen))

# apply this function to genres column
data['genres_list'] = data['genres'].map(lambda x: make_genreslist(x))

# for cast

def get_actor(x):
    cast = []
    for i in x:
        cast.append(i.get('name'))
    if cast == []:
        return np.nan
    else:
        return (cast[0])

# apply function to cast column

data['actor_1_name'] = data['cast'].map(lambda x: get_actor(x))

def ger_actor2(x):
    cast = []
    for i in x:
        cast.append(i.get('name'))
    if cast == [] or len(cast) <= 1:
        return np.nan
    else:
        return cast[1]

data['actor_2_name'] = data['cast'].map(lambda x: get_actor(x))


def ger_actor3(x):
    cast = []
    for i in x:
        cast.append(i.get('name'))
    if cast == [] or len(cast) <= 1:
        return np.nan
    else:
        return cast[2]

data['actor_3_name'] = data['cast'].map(lambda x: get_actor(x))


def ger_directors(x):
    dt = []
    str = " "
    for i in x:
        if i.get('job') == 'Director':
            dt.append(i.get('name'))
    if dt == []:
        return np.nan
    else:
        return str.join(dt)

data['director_name'] = data['crew'].map(lambda x: ger_directors(x))

movie = data.loc[:, ['director_name', 'actor_1_name', 'actor_2_name', 'actor_3_name', 'genres_list', 'title']]

movie = movie.dropna(how = 'any')

# chnage the column name of two data to same name
movie = movie.rename(columns = {'genres_list' : 'genres'})
movie = movie.rename(columns = {'title' : 'movie_title'})

movie['movie_title'] = movie['movie_title'].str.lower()

movie['comb'] = movie['actor_1_name'] + ' ' + movie['actor_2_name'] + ' ' + movie['actor_3_name'] + ' ' + movie['director_name'] + ' ' + movie['genres']

old = pd.read_csv('data1.csv')

old['combs'] = old['actor_1_name'] + ' ' + old['actor_2_name'] + ' ' + old['actor_3_name'] + ' ' + old['director_name']

new = old._append(movie)

# delete duplicate values

new.drop_duplicates(subset = "movie_title", keep = 'last', inplace = True)

# saving all the data till 2017

new.to_csv('new_data.csv', index = False)