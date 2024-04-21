
# ? VIEWS.PY

# Importing dependencies.
from flask import Flask, Blueprint, render_template, request, jsonify
from decouple import config
from transformers import AutoTokenizer, AutoModelForSequenceClassification,AutoConfig
from scipy.special import softmax
from goose3 import Goose
from werkzeug.utils import secure_filename
import numpy as np
import os
import mimetypes

# Creating a blueprint for views to use for routing.
app = Flask(__name__)
views = Blueprint(__name__, "views")

# Cache Directory
HUGGINGFACE_CACHE_DIR = config("HUGGINGFACE_CACHE_DIR", '')
TORCH_CACHE_DIR = config("TORCH_CACHE_DIR", '')
os.environ['TORCH_HOME'] = TORCH_CACHE_DIR

# Importing pre-trained model for Sentiment Analysis.
SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment"


config = AutoConfig.from_pretrained(SENTIMENT_MODEL)
config.num_labels = 3

tokenizer = AutoTokenizer.from_pretrained(
    SENTIMENT_MODEL, cache_dir=HUGGINGFACE_CACHE_DIR)
sentiment_model = AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL, config=config)



# * Routing for Home Page.
@views.route('/', methods=["GET", "POST"])
def home():
    # When opening the page, render the webpage.
    if request.method == "GET":
        return render_template("index.html")
    # When a form input is received, show the sentiment based on the input.
    elif request.method == "POST":
        input_type = request.form.get("type")

        # Find the input text from different types.
        input_text = ''

        if (input_type == "text"):
            input_text = request.form.get("input")
        elif (input_type == "url"):
            url = request.form.get("input")
            g = Goose()
            article = g.extract(url=url)
            input_text = article.cleaned_text
        elif (input_type == "media"):
            file = request.files.get("input")
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(
                    app.root_path, 'static', 'files', filename)
                file.save(file_path)
                input_media = process_files(file_path)

        # Find the sentiment values.
        sentiment_analysis = find_text_sentiment_analysis(input_text)

        return jsonify(sentiment_analysis)


# * Chunk the text into pieces of 510 characters.
def chunk_text(text, max_len=510):
    sentences = text.split(". ")
    chunks = []
    current_chunk = ''
    for sentence in sentences:
        # If the chunk is less than max length.
        if len(current_chunk) + len(sentence) < max_len:
            if current_chunk:
                # Add a space for continuing sentences.
                current_chunk += ' '
            current_chunk += sentence
        # If the chunk is more than max length.
        else:
            chunks.append(current_chunk)
            current_chunk = sentence

        # Adding the last chunk to chunks.
        chunks.append(current_chunk)

        return chunks


# * Process Media Files for analysis.
def process_files(file_path):
    mime_type, encoding = mimetypes.guess_type(file_path)
    type, subtype = mime_type.split('/', 1)


# * Find the polarity scores of the input.
def find_text_sentiment_analysis(input_text):
    chunks = chunk_text(input_text)
    sentiment_dicts = []

    for chunk in chunks:
        encoded_text = tokenizer.encode_plus(
            text=chunk,
            add_special_tokens=True,
            max_length=512,
            return_tensors="pt"
        )

        # Get model output
        output = sentiment_model(**encoded_text)

        # Assume logits are the first element of the tuple
        logits = output[0]

        # Detach and convert to numpy
        scores = softmax(logits.detach().numpy())

        # Calculate scores for each sentiment category
        val_neg = str(scores[0][0])
        val_neu = str(scores[0][1])
        val_pos = str(scores[0][2])

        # Determine the prominent sentiment
        if (val_neg > val_pos) and (val_neg > val_neu):
            prominent_sentiment = "NEGATIVE"
        elif (val_pos > val_neg) and (val_pos > val_neu):
            prominent_sentiment = "POSITIVE"
        else:
            prominent_sentiment = "NEUTRAL"

        # Create a dictionary for the sentiment analysis result
        sentiment_dict = {
            'score_negative': val_neg,
            'score_neutral': val_neu,
            'score_positive': val_pos,
            'prominent_sentiment': prominent_sentiment
        }

        sentiment_dicts.append(sentiment_dict)

    # Aggregate the list of chunks to find average sentiment
    avg_sentiment_dict = {
        'score_negative': str(np.mean([float(d['score_negative']) for d in sentiment_dicts])),
        'score_neutral': str(np.mean([float(d['score_neutral']) for d in sentiment_dicts])),
        'score_positive': str(np.mean([float(d['score_positive']) for d in sentiment_dicts])),
        'prominent_sentiment': max(set([d['prominent_sentiment'] for d in sentiment_dicts]), key=lambda x: [d['prominent_sentiment'] for d in sentiment_dicts].count(x))
    }

    return avg_sentiment_dict



