import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import urllib.request
from tmdbv3api import TMDb, Movie


def extract_data_from_wikipedia(url, year):
    """Extracts movie data from the specified Wikipedia URL for a given year.

    Args:
        url (str): URL of the Wikipedia page.
        year (int): Year of the films listed.

    Returns:
        pd.DataFrame: DataFrame containing extracted movie data.
    """

    try:
        source = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(source, 'lxml')
    except Exception as e:
        print(f"Error accessing Wikipedia page: {e}")
        return pd.DataFrame()

    tables = soup.find_all('table', class_='wikitable sortable')

    # Handle potential variations in table structure
    if not tables:
        print(f"Warning: No tables found for year {year} on Wikipedia page.")
        return pd.DataFrame()

    dfs = []
    for table in tables[:4]:  # Limit to relevant tables
        try:
            df = pd.read_html(str(table))[0]
            df['Release date'] = year  # Add year column directly
            dfs.append(df)
        except Exception as e:
            print(f"Error reading table for year {year}: {e}")
            continue

    if not dfs:
        return pd.DataFrame()  # Return empty DataFrame if all tables failed

    return pd.concat(dfs, ignore_index=True)  # Concatenate extracted DataFrames


def extract_movie_details(df, tmdb_api_key):
    """Extracts genres, director, and actors from the given DataFrame using TMDB API.

    Args:
        df (pd.DataFrame): DataFrame containing movie data.
        tmdb_api_key (str): TMDb API key.

    Returns:
        pd.DataFrame: DataFrame with enriched movie details.
    """

    tmdb = TMDb()
    tmdb.api_key = tmdb_api_key

    df['genres'] = df['movie_title'].apply(lambda x: get_genre(x, tmdb))
    df['director_name'] = df['Cast and crew'].apply(get_director)

    # Extract up to 3 actors with more robust handling
    def get_actors(crew_info):
        actors = crew_info.split("screenplay); ")[-1].split(", ")
        return [actor.strip() for actor in actors[:3]]

    df['actors'] = df['Cast and crew'].apply(get_actors)
    df[['actor_1_name', 'actor_2_name', 'actor_3_name']] = pd.DataFrame(df['actors'].tolist(), columns=['actor_1_name', 'actor_2_name', 'actor_3_name'])
    df.drop('actors', axis=1, inplace=True)  # Remove original 'actors' column

    return df


def get_genre(title, tmdb):
    """Fetches genres for a movie using TMDB API.

    Args:
        title (str): Movie title.
        tmdb (TMDb): TMDb API instance.

    Returns:
        str (or None): Comma-separated string of genres, or None if not found.
    """

    try:
        result = tmdb.movie().search(title)
        if not result:
            return np.nan
        movie_id = result[0].id
        response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb.api_key}')
        data_json = response.json()
        if data_json['genres']:
            genre_str = ", ".join([genre['name'] for genre in data_json['genres']])
            return genre_str
        else:
            return np.nan
    except Exception as e:
        print(f"Error fetching genre for {title}: {e}")
        return np.nan


def get_director(crew_info):
    """Extracts director name from the 'Cast and crew' column.

    Args:
        crew_info (str): String containing cast and crew information.
    """
