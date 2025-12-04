from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import re
import nltk
from nltk.corpus import stopwords
import pymorphy2
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI()

model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models/rf_classifier.pkl')
tfidf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models/tfidf_vectorizer.pkl')

model = joblib.load(model_path)
tfidf = joblib.load(tfidf_path)

morph = pymorphy2.MorphAnalyzer()
nltk.download('stopwords')
stop_words = set(stopwords.words('russian'))

def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'[^а-яё\s]', '', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    tokens = text.split()
    tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    tokens = [morph.parse(t)[0].normal_form for t in tokens]
    
    return ' '.join(tokens)

class Request(BaseModel):
    text: str
#предикт запрос
@app.post("/predict")
def predict(request: Request):
    processed = preprocess(request.text)
    vector = tfidf.transform([processed])
    
    category = model.predict(vector)[0]
    probabilities = model.predict_proba(vector)[0]
    confidence = float(np.max(probabilities))
    
    return {
        "text": request.text,
        "category": category,
        "confidence": confidence,
        "all_probas": dict(zip(model.classes_, probabilities.round(3)))
    }
#дефолтный запрос
@app.get("/")
def root():
    return {"message": "Support Ticket Classifier API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)