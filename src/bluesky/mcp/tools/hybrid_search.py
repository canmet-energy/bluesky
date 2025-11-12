"""
NECB Hybrid Search Engine

Combines SQLite FTS5 (keyword) + ChromaDB (semantic) using Reciprocal Rank Fusion.

Query Flow:
1. User query: "What's the max window area for a 3-story office in Calgary?"
2. Keyword search (FTS5): Matches "window area", "office"
3. Semantic search (ChromaDB): Understands "max window area" → FDWR concept
4. RRF merge: Combines rankings, boosts documents in both results
5. Return: Deduplicated ranked results

RRF Algorithm:
    RRF_score(doc) = sum over rankings (1 / (k + rank(doc)))
    where k = 60 (constant), rank = position in result list (1-indexed)

Example:
    Doc A in FTS5 rank 1, ChromaDB rank 3:
        RRF = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323
    Doc B in FTS5 rank 2 only:
        RRF = 1/(60+2) = 0.0161
    Doc A ranks higher (appears in both, better positions)
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import chromadb
from sentence_transformers import SentenceTransformer

from bluesky.mcp.tools.model_config import get_optimal_embedding_model
from bluesky.mcp.tools.vector_indexer import NECBVectorIndexer

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result with metadata and scoring."""

    id: str  # Unique document ID
    content: str  # Document text
    vintage: str  # NECB vintage (2011, 2015, 2017, 2020)
    content_type: str  # "section" or "table"
    title: str  # Document title
    page_number: int  # Page in PDF
    section_number: Optional[str] = None  # For sections
    table_number: Optional[str] = None  # For tables

    # Scoring
    fts_rank: Optional[int] = None  # Rank in FTS5 results (1-indexed)
    semantic_rank: Optional[int] = None  # Rank in ChromaDB results (1-indexed)
    semantic_distance: Optional[float] = None  # ChromaDB distance score
    rrf_score: float = 0.0  # Final RRF score

    # Metadata
    metadata: Dict = field(default_factory=dict)


class NECBHybridSearchEngine:
    """Hybrid search combining keyword (FTS5) and semantic (ChromaDB) search."""

    def __init__(
        self,
        db_path: Path,
        chroma_path: Path,
        model: Optional[SentenceTransformer] = None,
        rrf_k: int = 60,
    ):
        """
        Initialize hybrid search engine.

        Args:
            db_path: Path to necb.db SQLite database
            chroma_path: Path to ChromaDB storage
            model: Pre-loaded embedding model (optional)
            rrf_k: RRF constant (default: 60, higher = less emphasis on rank)
        """
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.rrf_k = rrf_k

        # Load embedding model
        if model is None:
            logger.info("Loading embedding model for semantic search...")
            self.model, self.model_config = get_optimal_embedding_model()
        else:
            self.model = model
            self.model_config = {"model_name": "custom", "device": "unknown"}

        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))

        logger.info(
            f"Hybrid search initialized: {self.model_config['model_name']} on {self.model_config['device']}"
        )

    def search(
        self,
        query: str,
        vintage: str = "2020",
        top_k: int = 10,
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5,
        min_rrf_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Hybrid search combining keyword and semantic results.

        Args:
            query: Natural language query
            vintage: NECB vintage to search (2011, 2015, 2017, 2020)
            top_k: Number of results to return
            keyword_weight: Weight for FTS5 results (0-1)
            semantic_weight: Weight for semantic results (0-1)
            min_rrf_score: Minimum RRF score to include (filter low-quality matches)

        Returns:
            List of SearchResult objects, ranked by RRF score
        """
        logger.info(f"Hybrid search: '{query}' in NECB {vintage}")

        # Run both searches in parallel (conceptually)
        fts_results = self._keyword_search(query, vintage, top_k=top_k * 2)
        semantic_results = self._semantic_search(query, vintage, top_k=top_k * 2)

        logger.info(f"Found {len(fts_results)} keyword, {len(semantic_results)} semantic results")

        # Merge using RRF
        merged_results = self._reciprocal_rank_fusion(
            fts_results=fts_results,
            semantic_results=semantic_results,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
        )

        # Filter and rank
        filtered = [r for r in merged_results if r.rrf_score >= min_rrf_score]
        ranked = sorted(filtered, key=lambda r: r.rrf_score, reverse=True)

        logger.info(f"RRF merged to {len(ranked)} results (top {top_k} returned)")

        return ranked[:top_k]

    def _keyword_search(self, query: str, vintage: str, top_k: int) -> List[SearchResult]:
        """SQLite FTS5 keyword search."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        results = []

        try:
            # FTS5 query - wrap in quotes to handle special characters
            # Convert multi-word queries to phrase match
            fts_query = f'"{query}"' if ' ' in query else query

            cursor.execute(
                """
                SELECT vintage, content_type, title, content
                FROM necb_search
                WHERE necb_search MATCH ? AND vintage = ?
                ORDER BY rank
                LIMIT ?
            """,
                (fts_query, vintage, top_k),
            )

            for rank, row in enumerate(cursor.fetchall(), start=1):
                vintage_val, content_type, title, content = row

                # Create result
                result = SearchResult(
                    id=f"{vintage_val}_{content_type}_{rank}",
                    content=content,
                    vintage=vintage_val,
                    content_type=content_type,
                    title=title or "",
                    page_number=0,  # Not in FTS table
                    fts_rank=rank,
                )
                results.append(result)

        except sqlite3.OperationalError as e:
            # FTS5 syntax error - log and continue with empty results
            # Semantic search will still work
            logger.warning(f"FTS5 keyword search failed (using semantic only): {e}")

        conn.close()
        return results

    def _semantic_search(self, query: str, vintage: str, top_k: int) -> List[SearchResult]:
        """ChromaDB semantic search."""
        collection_name = f"necb_{vintage}"

        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception as e:
            logger.warning(f"Collection {collection_name} not found: {e}")
            return []

        # Generate query embedding
        if "e5" in self.model_config.get("model_name", "").lower():
            query_text = f"query: {query}"  # e5 prefix
        else:
            query_text = query

        query_embedding = self.model.encode([query_text])[0]

        # Search ChromaDB
        chroma_results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # Parse results
        results = []
        if not chroma_results["ids"]:
            return results

        for rank, (doc_id, doc, metadata, distance) in enumerate(
            zip(
                chroma_results["ids"][0],
                chroma_results["documents"][0],
                chroma_results["metadatas"][0],
                chroma_results["distances"][0],
            ),
            start=1,
        ):
            result = SearchResult(
                id=doc_id,
                content=doc,
                vintage=metadata.get("vintage", vintage),
                content_type=metadata.get("content_type", "unknown"),
                title=metadata.get("title", ""),
                page_number=metadata.get("page_number", 0),
                section_number=metadata.get("section_number"),
                table_number=metadata.get("table_number"),
                semantic_rank=rank,
                semantic_distance=distance,
                metadata=metadata,
            )
            results.append(result)

        return results

    def _reciprocal_rank_fusion(
        self,
        fts_results: List[SearchResult],
        semantic_results: List[SearchResult],
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5,
    ) -> List[SearchResult]:
        """
        Merge results using Reciprocal Rank Fusion.

        RRF formula: score = sum over rankings (weight / (k + rank))
        """
        # Build unified result dict
        all_results: Dict[str, SearchResult] = {}

        # Add FTS results
        for result in fts_results:
            # Use content-based key for deduplication (not ID, which may differ)
            key = self._make_result_key(result)

            if key not in all_results:
                all_results[key] = result

            # Calculate FTS contribution
            if result.fts_rank:
                fts_contribution = keyword_weight / (self.rrf_k + result.fts_rank)
                all_results[key].rrf_score += fts_contribution

        # Add semantic results
        for result in semantic_results:
            key = self._make_result_key(result)

            if key not in all_results:
                all_results[key] = result

            # Calculate semantic contribution
            if result.semantic_rank:
                semantic_contribution = semantic_weight / (self.rrf_k + result.semantic_rank)
                all_results[key].rrf_score += semantic_contribution

                # Store semantic metadata if not already present
                if all_results[key].semantic_rank is None:
                    all_results[key].semantic_rank = result.semantic_rank
                    all_results[key].semantic_distance = result.semantic_distance

        return list(all_results.values())

    def _make_result_key(self, result: SearchResult) -> str:
        """Create deduplication key for a result."""
        # Use vintage + content_type + title + page for deduplication
        return f"{result.vintage}_{result.content_type}_{result.title}_{result.page_number}"


def main():
    """CLI for testing hybrid search."""
    import sys
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    parser = argparse.ArgumentParser(description="Test NECB hybrid search")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--vintage",
        default="2020",
        choices=["2011", "2015", "2017", "2020"],
        help="NECB vintage",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of results",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("src/bluesky/mcp/data/necb.db"),
        help="Path to necb.db",
    )
    parser.add_argument(
        "--chroma",
        type=Path,
        default=Path("src/bluesky/mcp/data/chroma"),
        help="Path to ChromaDB",
    )

    args = parser.parse_args()

    # Verify paths
    if not args.db.exists():
        print(f"❌ Database not found: {args.db}")
        sys.exit(1)

    if not args.chroma.exists():
        print(f"❌ ChromaDB not found: {args.chroma}")
        print("Run: python -m bluesky.mcp.tools.vector_indexer")
        sys.exit(1)

    # Initialize search engine
    print("=" * 80)
    print("NECB Hybrid Search")
    print("=" * 80)
    print(f"\nQuery: {args.query}")
    print(f"Vintage: {args.vintage}")
    print(f"Top K: {args.top_k}")
    print()

    engine = NECBHybridSearchEngine(db_path=args.db, chroma_path=args.chroma)

    # Search
    results = engine.search(query=args.query, vintage=args.vintage, top_k=args.top_k)

    # Display results
    print("\n" + "=" * 80)
    print(f"Results ({len(results)} found)")
    print("=" * 80)

    for i, result in enumerate(results, start=1):
        print(f"\n{i}. [{result.content_type.upper()}] {result.title}")
        print(f"   Vintage: {result.vintage}, Page: {result.page_number}")
        print(f"   RRF Score: {result.rrf_score:.4f}")

        if result.fts_rank:
            print(f"   Keyword Rank: {result.fts_rank}")
        if result.semantic_rank:
            print(f"   Semantic Rank: {result.semantic_rank} (distance: {result.semantic_distance:.4f})")

        if result.section_number:
            print(f"   Section: {result.section_number}")
        if result.table_number:
            print(f"   Table: {result.table_number}")

        # Show content preview
        preview = result.content[:200].replace("\n", " ")
        print(f"   Preview: {preview}...")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
