import pandas as pd
import numpy as np
import nltk
from nltk.corpus import stopwords
from sklearn import naive_bayes
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB  # Import MultinomialNB
from sklearn.metrics import roc_auc_score, accuracy_score
import pickle

# Load data
dataset = pd.read_csv('reviews.txt', sep='\t', names=['Reviews', 'Comments'])

# Option 1: Using built-in English stopwords
# This uses the default English stopwords list.
stopset = set(stopwords.words('english'))

# Option 2: Creating a custom stopword list (optional)
# Add your desired stopwords here (e.g., "very", "not")
custom_stopwords = ["very", "not"]
stopset = list(stopwords.words('english')) + custom_stopwords  # Combine with built-in (convert set to list)

vectorizer = TfidfVectorizer(use_idf=True, lowercase=True, strip_accents='ascii', stop_words=stopset)
X = vectorizer.fit_transform(dataset.Comments)
y = dataset.Reviews
pickle.dump(vectorizer, open('tranform.pkl', 'wb'))

# ... rest of your code (train-test split, model training, etc.)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
clf = naive_bayes.MultinomialNB()
clf.fit(X_train,y_train)
accuracy_score(y_test,clf.predict(X_test))*100

clf = naive_bayes.MultinomialNB()
clf.fit(X,y)
accuracy_score(y_test,clf.predict(X_test))*100

filename = 'nlp_model.pkl'
pickle.dump(clf, open(filename, 'wb'))















