import os
import glob
import sqlite3
import numpy as np
import functools
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
DB_PATH = 'vectors.db'
DATA_DIR = 'data'

class RAGSystem:
    def __init__(self):
        print(f"Loading embedding model {EMBEDDING_MODEL_NAME}...")
        self.encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.init_db()
        self.client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama"),
            timeout=float(os.getenv("LLM_TIMEOUT", 120.0))
        )
        self.llm_model = os.getenv("LLM_MODEL", "llama3")
        self.build_index_if_needed()

    def init_db(self):
        """Initializes the SQLite database."""
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                text TEXT,
                embedding BLOB
            )
        ''')
        # New persistent history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def build_index_if_needed(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        if cursor.fetchone()[0] > 0:
            print("Database already populated. Skipping indexing.")
            return

        print("Populating database from data/ directory...")
        files = glob.glob(os.path.join(DATA_DIR, "*.md"))
        for file_path in files:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            parts = text.split("## ")
            source = os.path.basename(file_path)
            for part in parts:
                chunk_text = part.strip()
                if not chunk_text:
                    continue
                if not text.startswith(chunk_text) and "##" in text:
                    chunk_text = "## " + chunk_text
                embedding = self.encoder.encode(chunk_text)
                embedding_bytes = embedding.astype(np.float32).tobytes()
                cursor.execute(
                    "INSERT INTO chunks (source, text, embedding) VALUES (?, ?, ?)",
                    (source, chunk_text, embedding_bytes)
                )
        self.conn.commit()
        print("Database populated successfully.")

    @functools.lru_cache(maxsize=1000)
    def cached_embed(self, text: str):
        """Basic caching: Returns embedding from cache if query has been seen before."""
        return self.encoder.encode(text).astype(np.float32)

    def search(self, query: str, top_k: int = 3):
        query_embedding = self.cached_embed(query)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, source, text, embedding FROM chunks")
        rows = cursor.fetchall()
        results = []
        for row in rows:
            row_id, source, text, emb_bytes = row
            chunk_embedding = np.frombuffer(emb_bytes, dtype=np.float32)
            similarity = np.dot(query_embedding, chunk_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
            )
            results.append((similarity, source, text))
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    def save_interaction(self, user_id: str, role: str, content: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
        self.conn.commit()

    def get_history(self, user_id: str, limit: int = 6):
        """Retrieves the last `limit` interactions for a user (e.g. 3 questions and 3 answers)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    def summarize_history(self, user_id: str) -> str:
        history = self.get_history(user_id, limit=6)
        if not history:
            return "You don't have any recent interactions for me to summarize!"
            
        history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
        prompt = f"Summarize the following recent conversation into a short, single concise paragraph:\n\n{history_text}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Failed to summarize history: {e}"

    def ask(self, query: str, user_id: str = "guest") -> str:
        # Prompt Injection Guard
        forbidden_phrases = ["ignore all", "system prompt", "administrator", "bypass instructions"]
        if any(phrase in query.lower() for phrase in forbidden_phrases):
            return "Safety Guard Violation: I cannot fulfill this request as it triggers safety filters."

        # Check retrieval DB
        retrieved_chunks = self.search(query, top_k=3)
        if not retrieved_chunks:
            return "I couldn't find any relevant information to answer your query."
            
        context = "\n\n".join([f"Source ({source}):\n{text}" for _sim, source, text in retrieved_chunks])
        
        # Load user history specifically
        past_messages = self.get_history(user_id, limit=4)
        
        prompt = f"""You are a helpful assistant. Answer the user's question accurately based ONLY on the provided context.
### Context:
{context}

### Question:
{query}

### Answer:
"""
        messages = [{"role": "system", "content": "You are a helpful assistant. Use context provided to answer questions."}]
        messages.extend(past_messages)
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2, 
            )
            answer = response.choices[0].message.content
            
            # Formatting "Source Snippets" nicely
            sources_used = list(set([source for _sim, source, _text in retrieved_chunks]))
            final_reply = f"{answer}\n\n📝 *Sources attached: {', '.join(sources_used)}*"
            
            # Save to persistent history
            self.save_interaction(user_id, "user", query)
            self.save_interaction(user_id, "assistant", answer)
            
            return final_reply
        except Exception as e:
            return f"An error occurred while generating the response: {str(e)}"
