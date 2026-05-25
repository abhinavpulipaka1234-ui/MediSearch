import os
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import spacy

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    nltk.download('punkt')

class Preprocessor:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.stemmer = PorterStemmer()
        try:
            self.nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
        except OSError:
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
            
    def process_text(self, text):
        if not text:
            return []
            
        # 1. Lowercase & clear punctuation
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        # 2. Tokenize (NLTK)
        tokens = nltk.word_tokenize(text)
        
        # 3. Stopwords
        filtered = [t for t in tokens if t not in self.stop_words]
        
        # 4. Lemmatization (spaCy)
        doc = self.nlp(" ".join(filtered))
        lemmatized = [token.lemma_ for token in doc]
        
        # 5. Stemming (NLTK)
        stemmed = [self.stemmer.stem(t) for t in lemmatized]
        
        return stemmed

    def extract_vocab_stats(self, corpus_series):
        vocab_freq = {}
        for text in corpus_series:
            tokens = self.process_text(text)
            for t in tokens:
                vocab_freq[t] = vocab_freq.get(t, 0) + 1
        return vocab_freq

if __name__ == "__main__":
    p = Preprocessor()
    sample_text = "Patient complains of severe throbbing headache with auras and vomiting."
    print("Original:", sample_text)
    print("Processed:", p.process_text(sample_text))
