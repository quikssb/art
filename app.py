from flask import Flask, render_template, request
from flaskwebgui import FlaskUI

from string import Template
from SPARQLWrapper import SPARQLWrapper, JSON

from fuzzywuzzy import fuzz

from rdflib import graph

def parseRdfToJson():
    rdf_url = r"C:\Users\pizza\Desktop\machinelearning\uni\projekt\aai_app_askart\static\knowledge_graph\art.ttl"
    graph.parse(rdf_url, format='application/rdf+xml')

parseRdfToJson()

sparql = SPARQLWrapper("http://localhost:3030/Art_Graph/sparql")
#TODO Rework the querys and the keywords, so it matches
#TODO Make the second Page look better, maybe rerout so that the result shows only when a result is active
#TODO Make a perceptual hash for the input file and then get all the files from the painter or the art itself and compare them

prefixes = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX : <http://h-da.de/fbi/art/>

"""

arts_of_artist_query = prefixes + """
SELECT ?artworklabel
WHERE {
	?artwork a :artwork;
		rdfs:label ?artworklabel;
		:artist/rdfs:label "$artist".
}
"""

# ---- old Queries

"""
#query to get the picture by the name
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX : <http://h-da.de/fbi/art/>

SELECT Distinct ?name ?property
WHERE {
?p a :artwork;
  rdfs:label "Mona Lisa";
  :image ?name.
}

#Query if author is known
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX : <http://h-da.de/fbi/art/>

SELECT Distinct ?name ?property
WHERE {
?p a :artwork;
  :image ?name;
  :artist ?m .
}
LIMIT 10000

"""

actor_query = """
PREFIX : <https://www.themoviedb.org/kaggle-export/>
SELECT ?$topic
WHERE{?m a :Movie ; :title "$title" ; :$topics ?$topic .}"""

movies_of_actor = """
PREFIX : <https://www.themoviedb.org/kaggle-export/>
SELECT Distinct ?title
WHERE {?m a :Movie; :cast/:name "$actor"; :title ?title .}
"""

cast_query = """
PREFIX : <https://www.themoviedb.org/kaggle-export/>
SELECT Distinct ?cast 
WHERE {?m a :Movie; :cast/:name ?cast .}
"""

movie_query = """
PREFIX : <https://www.themoviedb.org/kaggle-export/>
SELECT DISTINCT ?title
WHERE{?m a :Movie; :title ?title .}"""

result_string = """
Results for $title:
"""

result_movies_of_actor = """
All movies $title played in:
"""

no_result_string = """
No result found for question: $title"""

keywords = {
    'overview': ["overview", "summary", "abstract"],
    'genres/:name': ["genre", "category", "kind"],
    'cast/:name': ["cast", "actor", "actress"],
    'crew/:name': ["crew", "staff"],
    'release_date': ["release date", "release", "date"],
    'runtime': ["runtime", "length", "duration"],
    'revenue': ["revenue", "return", "roi"],
    'budget': ["budget", "money spent", "cost"],
    'homepage': ["homepage", "website"],
    'original_language': ["language"],
    'production_companies/:name': ["company", "corporation"],
    'production_countries/:name': ["countries", "land"],
    'tagline': ["tagline", "tags"],
    'movies': ["movies", "movie", "film"]
}

# get the SPARQL keyword construct to the input keyword
def get_SPARQL_keyword(search):
    for key in keywords:
        if search in keywords[key]:
            break
    return key

# return an array of all keywords
def all_keys():
    all_keys = []
    for key in keywords:
        for word in keywords[key]:
            all_keys.append(word)
    return all_keys

def query_arts_of_artist(artist):
    query_string = Template(arts_of_artist_query).substitute(artist=artist)
    sparql.setQuery(query_string)
    sparql.setReturnFormat(JSON)
    results_dict = sparql.query().convert()
    results = [row['artworklabel']['value'] for row in results_dict['results']['bindings']]
    return results

# Old Movie queries -----
# TODO: Remove them at some point

def query_movies_of_actor(actor):
    query_string = Template(movies_of_actor).substitute(actor=actor)
    sparql.setQuery(query_string)
    sparql.setReturnFormat(JSON)
    results_dict = sparql.query().convert()
    results = [row['title']['value'] for row in results_dict['results']['bindings']]
    return results

def query_all_movie_names():
    sparql.setQuery(movie_query)
    sparql.setReturnFormat(JSON)
    results_dict = sparql.query().convert()
    results = [row['title']['value'] for row in results_dict['results']['bindings']]
    return results

def query_all_actors():
    sparql.setQuery(cast_query)
    sparql.setReturnFormat(JSON)
    results_dict = sparql.query().convert()
    results = [row['cast']['value'] for row in results_dict['results']['bindings']]
    return results

def query(title, keyword, keyword1):
    query_string = Template(actor_query).substitute(title=title, topic=keyword, topics=keyword1)
    sparql.setQuery(query_string)
    sparql.setReturnFormat(JSON)
    results_dict = sparql.query().convert()
    results = [row[keyword]['value'] for row in results_dict['results']['bindings']]
    print(results)
    return results

def find_keyword(question):
    question = question.lower()
    list_of_words = question.split(" ")     # string to list
    list_of_keywords = all_keys()

    print(question)

    highest_value = 0
    keyword = ''
    for word in list_of_keywords:
        value = fuzz.token_set_ratio(list_of_words, word.lower())
        if value > highest_value and value > 50:
            highest_value = value
            keyword = word

    print(f" keyword found: \"{keyword}\" with ratio of {highest_value}")
    return keyword

def find_actor_name(sentence, allactors):
    valuetmp = 0
    actor_name = ""
    for entry in allactors:
        value = fuzz.ratio(sentence.lower(), entry.lower())
        if value > valuetmp and value > 80:  # update value and title if higher similarity than before
            valuetmp = value
            actor_name = entry
        if value >= 100:  # at full similarity we can stop searching to safe time
            actor_name = entry
            break
    return actor_name

def find_title_name(sentence, allmovies):
    valuetmp = 0
    title = ""
    print("we get to the find title func")
    for entry in allmovies:
        # compare similarity using all lowercase versions of the input
        value = fuzz.ratio(sentence.lower(), entry.lower())
        #print(f"fuzzy rating is: {value} for title {entry}")
        if value > valuetmp and value > 50:  # update value and title if higher similarity than before
            valuetmp = value
            title = entry
        if value >= 100:  # at full similarity we can stop searching to safe time
            title = entry
            break
    print(f"returning movie name \"{title}\"")
    return title

# End of queries ---

app = Flask(__name__)
ui = FlaskUI(app)

# Methods for communication with UI

@app.route("/", methods=('GET', 'POST'))
def index():
    # TODO: Rework this method
    # For now the website can only receive the name of an artist and queries their artworks

    while(True):
        if request.method == 'POST':
            artist = request.form['title']
            result_query_arts_of_artist = query_arts_of_artist(artist)
            if len(result_query_arts_of_artist) == 0:
                result_of_question = Template(no_result_string).substitute(title=request.form['title'])
                return render_template('index.html', result_label = result_of_question)
            result_of_question = Template(result_string).substitute(title=request.form['title'])
            return render_template('index.html', artists=query_arts_of_artist(artist), result_label=result_of_question)
        else:
            return render_template('index.html', artists=[], result_label="Results")

# TODO: remove this method at some point
# Left the method untouched for now, because it contains useful logic we can learn from
def old_index():
    while(True):
        result = query_all_movie_names()
        resultallactors = query_all_actors()
        if request.method == 'POST':
            title = request.form['title']
            keyword = find_keyword(title)
            keyword1 = get_SPARQL_keyword(keyword)
            if keyword == "" or keyword == 'movies':
                title = title.replace(keyword, '')
                if title[0] == " ":
                    title = title[1:]
                actor_name = find_actor_name(title, resultallactors)
                if actor_name == "":
                    result_of_question = Template(no_result_string).substitute(title=request.form['title'])
                    return render_template('index.html', actors=[], result_question=result_of_question)
                else:
                    result_of_question = Template(result_movies_of_actor).substitute(title=actor_name)
                    return render_template('index.html', actors=query_movies_of_actor(actor_name), result_question=result_of_question)
            else:
                print(f"SPARQL keyword is \"{keyword1}\"")
                title = title.replace(keyword, '')
                if title[0] == " ":
                    title = title[1:]
                print(title)
                title = find_title_name(title, result)
                if title != "":
                    result_of_question = Template(result_string).substitute(title=title, keyword=keyword)
                    return render_template('index.html', actors=query(title, keyword, keyword1), result_question=result_of_question)
                else:
                    result_of_question = Template(no_result_string).substitute(title=request.form['title'])
                    return render_template('index.html', actors=[], result_question=result_of_question)
        else:
            return render_template('index.html', actors=[], result_question="Results")

@app.route("/uploadimage", methods=('GET', 'POST'))
def uploadimage():
    # TODO: Add initial return to make App runnable
    # TODO: Rework this method
    return render_template('uploadimage.html', actors=[], result_question="Results")

    while (True):
        result = query_all_movie_names()
        resultallactors = query_all_actors()
        if request.method == 'POST':
            title = request.form['title']
            image = request.files['image']
            keyword = find_keyword(title)

            keyword1 = get_SPARQL_keyword(keyword)
            if keyword == "" or keyword == 'movies':
                title = title.replace(keyword, '')
                if title[0] == " ":
                    title = title[1:]
                actor_name = find_actor_name(title, resultallactors)
                if actor_name == "":
                    result_of_question = Template(no_result_string).substitute(title=request.form['title'])
                    return render_template('uploadimage.html', actors=[], result_question=result_of_question)
                else:
                    result_of_question = Template(result_movies_of_actor).substitute(title=actor_name)
                    return render_template('uploadimage.html', actors=query_movies_of_actor(actor_name),
                                           result_question=result_of_question)
            else:
                print(f"SPARQL keyword is \"{keyword1}\"")
                title = title.replace(keyword, '')
                if title[0] == " ":
                    title = title[1:]
                print(title)
                title = find_title_name(title, result)
                if title != "":
                    result_of_question = Template(result_string).substitute(title=title, keyword=keyword)
                    return render_template('uploadimage.html', actors=query(title, keyword, keyword1),
                                           result_question=result_of_question)
                else:
                    result_of_question = Template(no_result_string).substitute(title=request.form['title'])
                    return render_template('uploadimage.html', actors=[], result_question=result_of_question)
        else:
            return render_template('uploadimage.html', actors=[], result_question="Results")

app.run(debug=True)