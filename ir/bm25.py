import os
import sqlite3
import math
import numpy as np
from .preprocessor import Preprocessor

class BM25Ranker:
    def __init__(self, db_path="ir/inverted_index.db", k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.db_path = db_path
        self.disabled = False

        # If the on-disk index isn't present, disable BM25 cleanly.
        if not os.path.exists(db_path):
            self.disabled = True
            self.prep = None
            self.conn = None
            self.N = 1
            self.avg_dl = 1.0
            self.idf = {}
            return

        try:
            self.prep = Preprocessor()
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
        except Exception:
            # Any initialization error should not crash the API; chatbot will fall back to keywords.
            self.disabled = True
            self.prep = None
            self.conn = None
            self.N = 1
            self.avg_dl = 1.0
            self.idf = {}
            return
        
        # Load Metas
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT val FROM meta WHERE key='TOTAL_DOCS'")
            res = cur.fetchone()
            self.N = int(res[0]) if res else 1
            
            cur.execute("SELECT val FROM meta WHERE key='AVG_DOC_LEN'")
            res = cur.fetchone()
            self.avg_dl = float(res[0]) if res else 1.0
            
            # Preload vocab IDFs to memory for very fast lookup
            self.idf = {}
            cur.execute("SELECT term, df FROM vocab")
            for term, df in cur.fetchall():
                # BM25 IDF formula
                idf_val = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
                self.idf[term] = idf_val
        except Exception:
            # If schema/tables are missing, disable BM25 gracefully.
            self.disabled = True
            self.idf = {}
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def score_query(self, query):
        if self.disabled or not self.conn or not self.prep:
            return []

        try:
            tokens = self.prep.process_text(query)
        except Exception:
            return []
        if not tokens:
            return []
            
        try:
            cur = self.conn.cursor()
        except Exception:
            return []
        
        doc_scores = {}
        
        for term in tokens:
            if term not in self.idf:
                continue
                
            idf_t = self.idf[term]
            # Fetch postings for this term
            try:
                cur.execute("SELECT doc_id, tf FROM postings WHERE term=?", (term,))
                postings = cur.fetchall()
            except Exception:
                return []

            for doc_id, tf in postings:
                # Length we fetch from docs table on demand, or optimize by fetching all relevant docs
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = 0.0
                    
                try:
                    cur.execute("SELECT length FROM docs WHERE doc_id=?", (doc_id,))
                    dl_res = cur.fetchone()
                except Exception:
                    dl_res = None
                dl = dl_res[0] if dl_res else self.avg_dl
                
                # BM25 Term Score
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (dl / self.avg_dl))
                doc_scores[doc_id] += idf_t * (numerator / denominator)
                
        # Sort and return top
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_docs[:10]:
            try:
                cur.execute("SELECT condition_label FROM docs WHERE doc_id=?", (doc_id,))
                lbl_row = cur.fetchone()
                lbl = lbl_row[0] if lbl_row else "Unknown"
            except Exception:
                lbl = "Unknown"
            results.append({"case_id": doc_id, "score": score, "condition_label": lbl})
            
        return results

def evaluate_metrics(ranker, test_queries):
    """
    Evaluates engine using Precision@5, MAP, and NDCG@5 based on matching Condition Labels.
    test_queries: list of tuples (query_text, true_condition_label)
    """
    p_at_5_total = 0
    ap_total = 0
    ndcg_total = 0
    k = 5
    
    for q_text, true_label in test_queries:
        res = ranker.score_query(q_text)
        
        # Relevance Array: 1 if matched label, 0 if not
        rels = [1 if r['condition_label'] == true_label else 0 for r in res]
        
        # P@5
        p_at_5 = sum(rels[:k]) / k
        p_at_5_total += p_at_5
        
        # AP
        num_hits = 0.0
        score = 0.0
        for i, rel in enumerate(rels):
            if rel == 1:
                num_hits += 1.0
                score += num_hits / (i + 1.0)
        ap_total += score / max(1.0, num_hits) if num_hits > 0 else 0
        
        # NDCG@5
        dcg = 0.0
        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(k, sum(rels)))) # Ideal
        for i, rel in enumerate(rels[:k]):
            if rel == 1:
                dcg += 1.0 / math.log2(i + 2)
        ndcg_total += dcg / idcg if idcg > 0 else 0.0

    n = len(test_queries)
    return {
        "P@5": p_at_5_total / n,
        "MAP": ap_total / n,
        "NDCG@5": ndcg_total / n
    }

if __name__ == "__main__":
    r = BM25Ranker()
    test_q = [
        ("Patient has severe sharp left arm pain and crushing chest pressure", "Myocardial Infarction"),
        ("I have a throbbing headache with an aura and vomiting", "Migraine"),
        ("Burning sensation during urination", "UTI"),
        ("Very high fever with night sweats and body aches", "Malaria")
    ]
    
    print("Evaluating custom BM25 Engine...")
    metrics = evaluate_metrics(r, test_q)
    print("Results:", metrics)
