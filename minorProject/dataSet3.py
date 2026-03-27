import pandas as pd
import numpy as np
import requests
from tmdbv3api import TMDb, Movie

tmdb = TMDb()
tmdb.api_key = 'e7d0426c5b557ced5863b495eea3ffc5'  # Replace with your TMDB API key
tmdb_movie = Movie()


def get_genre(title):
    try:
        result = tmdb_movie.search(title)
        movie_id = result[0].id
        response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb.api_key}')
        data_json = response.json()
        if data_json['genres']:
            genres_str = ", ".join([genre['name'] for genre in data_json['genres']])
            return genres_str
        else:
            return np.nan
    except Exception as e:  # Handle potential errors from the API call
        print(f"Error fetching genre for {title}: {e}")
        return np.nan


def get_director(crew_info):
    if " (director)" in crew_info:
        return crew_info.split(" (director)")[0]
    elif " (directors)" in crew_info:
        return crew_info.split(" (directors)")[0]
    else:
        return np.nan


def get_actors(crew_info):
    actors = crew_info.split("screenplay); ")[-1].split(", ")
    return [actor.strip() for actor in actors]  # Get all actors


def process_year(year):
    link = f"https://en.wikipedia.org/wiki/List_of_American_films_of_{year}"
    # df = pd.concat(pd.read_html(link, header=0)[2:6], ignore_index=True)
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(link, headers=headers)
    tables = pd.read_html(response.text)

    df = pd.concat(tables[2:6], ignore_index=True)

    # Print the number of rows for debugging
    print(f"Number of rows before processing: {len(df)}")

    df['genres'] = df['Title'].map(get_genre)
    df['director_name'] = df['Cast and crew'].map(get_director)
    df['actors'] = df['Cast and crew'].map(get_actors)

    # Handle missing values
    df['director_name'] = df['director_name'].fillna('unknown')

    # Create empty lists for actors (to handle varying lengths)
    df['actor_1_name'] = [''] * len(df)
    df['actor_2_name'] = [''] * len(df)
    df['actor_3_name'] = [''] * len(df)

    # Fill actor columns (use enumerate for index access)
    for i, actors in enumerate(df['actors']):
        for j, actor in enumerate(actors[:3]):  # Limit to 3 actors
            if j == 0:
                df.at[i, 'actor_1_name'] = actor
            elif j == 1:
                df.at[i, 'actor_2_name'] = actor
            elif j == 2:
                df.at[i, 'actor_3_name'] = actor

    # Drop the original 'actors' column after processing
    df.drop(columns='actors', inplace=True)

    df['movie_title'] = df['Title'].str.lower()
    df['comb'] = df[['actor_1_name', 'actor_2_name', 'actor_3_name', 'director_name', 'genres']].agg(' '.join, axis=1)
    return df[['movie_title', 'director_name', 'actor_1_name', 'actor_2_name', 'actor_3_name', 'genres', 'comb']]


df_2018 = process_year(2018)
df_2019 = process_year(2019)

my_df = pd.concat([df_2018, df_2019], ignore_index=True)

# **Corrected line using concat for combining DataFrames**
old_df = pd.read_csv('new_data.csv')
final_df = old_df._append(my_df, ignore_index=True)

final_df = final_df.dropna(how='any')

final_df.to_csv('final_data.csv', index=False)

