"""
MongoDB Atlas Service for persistent knowledge base chunks and runtime uploaded datasets.
Provides zero-cost, persistent cloud storage across ephemeral container restarts.
"""

from __future__ import annotations
import time
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from app.config import MONGODB_URI, MONGODB_DB_NAME
from app.utils.logging import logger

_MONGO_CLIENT = None
_MONGO_DB = None


def get_mongo_db():
    """Retrieve or initialize MongoDB Atlas database connection."""
    global _MONGO_CLIENT, _MONGO_DB
    if _MONGO_DB is not None:
        return _MONGO_DB

    uri = MONGODB_URI
    if not uri:
        return None

    try:
        import pymongo
        _MONGO_CLIENT = pymongo.MongoClient(uri, serverSelectionTimeoutMS=4000)
        # Verify connection
        _MONGO_CLIENT.admin.command("ping")
        _MONGO_DB = _MONGO_CLIENT[MONGODB_DB_NAME]
        logger.info("MongoDB Atlas connected successfully to database: %s", MONGODB_DB_NAME)
        return _MONGO_DB
    except Exception as e:
        logger.warning("MongoDB Atlas connection failed: %s. Using local fallback.", e)
        _MONGO_CLIENT = None
        _MONGO_DB = None
        return None


def is_mongo_connected() -> bool:
    """Check if MongoDB Atlas is currently available."""
    db = get_mongo_db()
    return db is not None


# ═══════════════════════════════════════════════════════════════════
# Knowledge Base (Chunks & Embeddings) Persistence
# ═══════════════════════════════════════════════════════════════════

CHUNKS_COLLECTION = "knowledge_chunks"
DATASETS_COLLECTION = "uploaded_datasets"


def save_chunks_to_mongo(chunks_data: List[Dict[str, Any]]) -> int:
    """Save or update document chunks with embeddings in MongoDB Atlas."""
    db = get_mongo_db()
    if db is None or not chunks_data:
        return 0

    col = db[CHUNKS_COLLECTION]
    count = 0
    for chunk in chunks_data:
        chunk_id = chunk.get("chunk_id")
        if not chunk_id:
            continue
        col.update_one(
            {"chunk_id": chunk_id},
            {"$set": {
                **chunk,
                "updated_at": time.time(),
            }},
            upsert=True
        )
        count += 1
    logger.info("Saved %d document chunks to MongoDB Atlas.", count)
    return count


def load_all_chunks_from_mongo() -> List[Dict[str, Any]]:
    """Load all document chunks with embeddings from MongoDB Atlas."""
    db = get_mongo_db()
    if db is None:
        return []

    try:
        col = db[CHUNKS_COLLECTION]
        docs = list(col.find({}, {"_id": 0}))
        logger.info("Loaded %d document chunks from MongoDB Atlas.", len(docs))
        return docs
    except Exception as e:
        logger.warning("Failed to load chunks from MongoDB: %s", e)
        return []


def clear_chunks_in_mongo() -> bool:
    """Clear all document chunks in MongoDB Atlas (for rebuild)."""
    db = get_mongo_db()
    if db is None:
        return False
    try:
        db[CHUNKS_COLLECTION].delete_many({})
        return True
    except Exception as e:
        logger.warning("Failed to clear chunks in MongoDB: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════════
# Runtime Uploaded Dataset Persistence
# ═══════════════════════════════════════════════════════════════════

def save_uploaded_dataset_to_mongo(name: str, df: pd.DataFrame) -> bool:
    """Save user-uploaded tabular dataset to MongoDB Atlas for persistence."""
    db = get_mongo_db()
    if db is None:
        return False

    try:
        col = db[DATASETS_COLLECTION]
        records = df.to_dict(orient="records")
        # Store metadata + data
        col.update_one(
            {"dataset_name": name},
            {"$set": {
                "dataset_name": name,
                "total_rows": len(df),
                "columns": list(df.columns),
                "uploaded_at": time.time(),
                "records": records[:5000],  # store up to 5k sample records for fast cloud recall
            }},
            upsert=True
        )
        logger.info("Saved custom dataset '%s' (%d rows) to MongoDB Atlas.", name, len(df))
        return True
    except Exception as e:
        logger.warning("Failed to save dataset '%s' to MongoDB: %s", name, e)
        return False


def load_uploaded_dataset_from_mongo(name: str) -> Optional[pd.DataFrame]:
    """Retrieve saved custom dataset from MongoDB Atlas."""
    db = get_mongo_db()
    if db is None:
        return None

    try:
        col = db[DATASETS_COLLECTION]
        doc = col.find_one({"dataset_name": name})
        if doc and "records" in doc:
            df = pd.DataFrame(doc["records"])
            if "order_date" in df.columns:
                df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
            return df
        return None
    except Exception as e:
        logger.warning("Failed to load dataset '%s' from MongoDB: %s", name, e)
        return None
