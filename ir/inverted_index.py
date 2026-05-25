import os
import sqlite3
import pyarrow.parquet as pq
import json
import math
from concurrent.futures import ProcessPoolExecutor
from .preprocessor import Preprocessor

DATA_DIR = "data/cases/"
INDEX_DB = "ir/inverted_index.db"
os.makedirs("ir", exist_ok=True)

class IndexBuilder:
    def __init__(self, db_path=INDEX_DB):
        self.db_path = db_path
        self.prep = Preprocessor()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, val TEXT);
            CREATE TABLE IF NOT EXISTS docs (doc_id TEXT PRIMARY KEY, length INTEGER, condition_label TEXT);
            CREATE TABLE IF NOT EXISTS vocab (term TEXT PRIMARY KEY, df INTEGER);
            CREATE TABLE IF NOT EXISTS postings (term TEXT, doc_id TEXT, tf INTEGER, positions TEXT,
                PRIMARY KEY (term, doc_id));
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_postings_term ON postings(term);")
        conn.commit()
        return conn

    def index_batch(self, cases):
        # Local mini-index just for this batch
        local_docs = {}
        local_df = {}
        local_postings = {}
        
        for case in cases:
            doc_id = case['case_id']
            text = case['symptoms']
            condition = case['condition_label']
            
            tokens = self.prep.process_text(text)
            local_docs[doc_id] = (len(tokens), condition)
            
            # Position tracking
            term_pos = {}
            for pos, term in enumerate(tokens):
                if term not in term_pos:
                    term_pos[term] = []
                term_pos[term].append(pos)
                
            for term, positions in term_pos.items():
                if term not in local_df:
                    local_df[term] = 1
                else:
                    local_df[term] += 1
                    
                if term not in local_postings:
                    local_postings[term] = []
                local_postings[term].append((doc_id, len(positions), json.dumps(positions)))
                
        return local_docs, local_df, local_postings

    def build(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        print("Initializing Index Database...")
        conn = self._init_db()
        cur = conn.cursor()

        dataset = pq.ParquetDataset(DATA_DIR)
        fragments = dataset.fragments
        
        total_docs = 0
        global_df = {}
        
        print(f"Processing {len(fragments)} Parquet fragments...")
        for count, frag in enumerate(fragments):
            df = frag.to_table().to_pandas()
            cases = df[['case_id', 'symptoms', 'condition_label']].to_dict(orient='records')
            
            # Process block
            l_docs, l_df, l_postings = self.index_batch(cases)
            
            # Insert Docs
            cur.executemany("INSERT INTO docs VALUES (?, ?, ?)",
                            [(k, v[0], v[1]) for k, v in l_docs.items()])
            total_docs += len(l_docs)
            
            # Aggregate DF
            for term, df_val in l_df.items():
                global_df[term] = global_df.get(term, 0) + df_val
                
            # Insert Postings
            postings_inserts = []
            for term, pl in l_postings.items():
                for doc_id, tf, positions in pl:
                    postings_inserts.append((term, doc_id, tf, positions))
            cur.executemany("INSERT INTO postings VALUES (?, ?, ?, ?)", postings_inserts)
            
            print(f"Indexed fragment {count+1}/{len(fragments)} using vocabulary size {len(global_df)}")
            conn.commit()

        # Finalize meta and vocab
        print(" Finalizing vocab and meta data...")
        cur.executemany("INSERT INTO vocab VALUES (?, ?)", [(k, v) for k, v in global_df.items()])
        
        avg_len = cur.execute("SELECT AVG(length) FROM docs").fetchone()[0]
        cur.execute("INSERT INTO meta VALUES (?, ?)", ("TOTAL_DOCS", str(total_docs)))
        cur.execute("INSERT INTO meta VALUES (?, ?)", ("AVG_DOC_LEN", str(avg_len)))
        
        conn.commit()
        conn.close()
        print(f"Index built! Total documents: {total_docs}, Vocab terms: {len(global_df)}")

if __name__ == "__main__":
    builder = IndexBuilder()
    builder.build()
