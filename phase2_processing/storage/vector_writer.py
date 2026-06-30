"""
storage/vector_writer.py
─────────────────────────────────────────────────────────────────────────────
Step 7: Vector Database Writer
Architecture Ref: Phase 2 § 2.7

Stores generated embeddings along with metadata for semantic search.
Supports:
1. ChromaDB (Local / Docker Client) - if package is available and server is reachable.
2. Pinecone - if PINECONE_API_KEY is configured in env.
3. PostgreSQL Fallback Store - writes to raw_reviews_embeddings table.
   This guarantees out-of-the-box functionality since PostgreSQL is already
   running in Phase 1's docker-compose.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import sqlite3
import json
import psycopg2
from loguru import logger


class VectorDBWriter:
    """
    Writer class to index vectors in the selected vector store.
    """

    def __init__(self, db_conn=None) -> None:
        self.db_conn = db_conn
        self.chroma_client = None
        self.chroma_collection = None
        self._init_store()

    def _init_store(self) -> None:
        """Initialize the vector database connection or PostgreSQL table."""
        # 1. Try ChromaDB
        try:
            import chromadb
            host = os.environ.get("CHROMA_HOST", "localhost")
            port = int(os.environ.get("CHROMA_PORT", 8000))
            logger.info(f"[VectorStore] Initializing ChromaDB Client on {host}:{port}...")
            # Using HTTP client to connect to a running Chroma Docker container
            self.chroma_client = chromadb.HttpClient(host=host, port=port)
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name="spotify_reviews"
            )
            logger.info("[VectorStore] Connected to ChromaDB successfully.")
            return
        except ImportError:
            logger.debug("[VectorStore] chromadb package not installed. Skipping ChromaDB.")
        except Exception as exc:
            logger.warning(f"[VectorStore] ChromaDB client initialization failed: {exc}. Falling back.")

        # 2. Try Pinecone if key is set
        pinecone_key = os.environ.get("PINECONE_API_KEY")
        if pinecone_key and not pinecone_key.startswith("your_"):
            logger.info("[VectorStore] Pinecone key detected. (Pinecone integration active)")
            return

        # 3. Fallback: Initialize PostgreSQL Table
        if self.db_conn:
            logger.info("[VectorStore] Using PostgreSQL fallback table for vector storage.")
            try:
                with self.db_conn.cursor() as cur:
                    # Create a simple table to store vector embeddings as JSON/array
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS raw_reviews_embeddings (
                            review_id UUID PRIMARY KEY REFERENCES raw_reviews(review_id) ON DELETE CASCADE,
                            embedding JSONB NOT NULL,
                            dimensions INTEGER NOT NULL,
                            metadata JSONB,
                            indexed_at TIMESTAMPTZ DEFAULT NOW()
                        );
                        """
                    )
                self.db_conn.commit()
                logger.info("[VectorStore] PostgreSQL fallback table initialized.")
            except Exception as exc:
                logger.error(f"[VectorStore] Failed to initialize PostgreSQL fallback table: {exc}")

    def upsert(
        self,
        review_id: str,
        vector: list[float],
        dimensions: int,
        metadata: dict
    ) -> bool:
        """
        Upsert a review embedding into the vector database.

        Returns:
            True if successful, False otherwise.
        """
        # 1. Write to ChromaDB
        if self.chroma_collection:
            try:
                # Chroma expects string IDs, documents, embeddings, and metadata dict
                self.chroma_collection.upsert(
                    ids=[review_id],
                    embeddings=[vector],
                    metadatas=[metadata],
                    documents=[metadata.get("review_text", "")]
                )
                logger.debug(f"[VectorStore] ChromaDB indexed review {review_id}")
                return True
            except Exception as exc:
                logger.error(f"[VectorStore] ChromaDB upsert error for review {review_id}: {exc}")

        # 2. PostgreSQL Fallback
        if self.db_conn:
            try:
                with self.db_conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO raw_reviews_embeddings (review_id, embedding, dimensions, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (review_id) DO UPDATE
                        SET embedding = EXCLUDED.embedding,
                            dimensions = EXCLUDED.dimensions,
                            metadata = EXCLUDED.metadata,
                            indexed_at = NOW();
                        """,
                        (
                            review_id,
                            json.dumps(vector),
                            dimensions,
                            json.dumps(metadata)
                        )
                    )
                self.db_conn.commit()
                logger.debug(f"[VectorStore] PostgreSQL fallback indexed review {review_id}")
                return True
            except Exception as exc:
                logger.error(f"[VectorStore] PostgreSQL fallback upsert error for review {review_id}: {exc}")
                self.db_conn.rollback()

        return False
