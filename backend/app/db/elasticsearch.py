"""
Elasticsearch client setup and index management.
Uses AsyncElasticsearch for non-blocking operations.
"""

import json
from typing import Optional

from elasticsearch import AsyncElasticsearch
from loguru import logger

from app.config import settings


# Elasticsearch index mapping for multilingual PDF content
PDF_INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "multilingual": {
                    "type": "custom",
                    "tokenizer": "icu_tokenizer",
                    "filter": ["icu_folding", "lowercase"],
                },
                "cjk_analyzer": {
                    "type": "custom",
                    "tokenizer": "icu_tokenizer",
                    "filter": ["cjk_width", "cjk_bigram", "lowercase"],
                },
                "autocomplete": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "edge_ngram_filter"],
                },
            },
            "filter": {
                "edge_ngram_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                }
            },
        },
        "number_of_shards": 2,
        "number_of_replicas": 0,
        "index.max_result_window": 50000,
    },
    "mappings": {
        "properties": {
            "document_id": {"type": "keyword"},
            "page_id": {"type": "keyword"},
            "filename": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "autocomplete": {"type": "text", "analyzer": "autocomplete"},
                },
            },
            "page_number": {"type": "integer"},
            "content": {
                "type": "text",
                "analyzer": "multilingual",
                "search_analyzer": "multilingual",
                "fields": {
                    "exact": {"type": "keyword", "ignore_above": 32766},
                    "cjk": {"type": "text", "analyzer": "cjk_analyzer"},
                    "standard": {"type": "text", "analyzer": "standard"},
                },
            },
            "language": {"type": "keyword"},
            "author": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "upload_date": {"type": "date"},
            "creation_date": {"type": "date"},
            "word_count": {"type": "integer"},
            "page_count": {"type": "integer"},
            "metadata": {"type": "object", "enabled": False},
            "embedding_vector": {
                "type": "dense_vector",
                "dims": settings.embedding_dimensions,
                "index": True,
                "similarity": "cosine",
            },
        }
    },
}


class ElasticsearchClient:
    """Singleton Elasticsearch client manager."""

    _instance: Optional[AsyncElasticsearch] = None

    @classmethod
    async def get_client(cls) -> AsyncElasticsearch:
        """Get or create the Elasticsearch client."""
        if cls._instance is None:
            cls._instance = AsyncElasticsearch(
                settings.elasticsearch_url,
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True,
            )
        return cls._instance

    @classmethod
    async def close(cls):
        """Close the Elasticsearch client."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None

    @classmethod
    async def init_index(cls):
        """Create the PDF index with mappings if it doesn't exist."""
        client = await cls.get_client()
        index_name = settings.elasticsearch_index

        try:
            exists = await client.indices.exists(index=index_name)
            if not exists:
                await client.indices.create(
                    index=index_name,
                    body=PDF_INDEX_MAPPING,
                )
                logger.info(f"Created Elasticsearch index: {index_name}")
            else:
                logger.info(f"Elasticsearch index already exists: {index_name}")
        except Exception as e:
            logger.warning(
                f"Could not create Elasticsearch index (ICU plugin may not be installed): {e}. "
                "Trying with standard tokenizer fallback..."
            )
            # Fallback mapping without ICU (for environments without the plugin)
            fallback_mapping = {
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "multilingual": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "asciifolding"],
                            },
                            "cjk_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["cjk_width", "cjk_bigram", "lowercase"],
                            },
                            "autocomplete": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "edge_ngram_filter"],
                            },
                        },
                        "filter": {
                            "edge_ngram_filter": {
                                "type": "edge_ngram",
                                "min_gram": 2,
                                "max_gram": 20,
                            }
                        },
                    },
                    "number_of_shards": 2,
                    "number_of_replicas": 0,
                },
                "mappings": PDF_INDEX_MAPPING["mappings"],
            }
            try:
                exists = await client.indices.exists(index=index_name)
                if not exists:
                    await client.indices.create(
                        index=index_name,
                        body=fallback_mapping,
                    )
                    logger.info(f"Created Elasticsearch index with fallback analyzer: {index_name}")
            except Exception as e2:
                logger.error(f"Failed to create Elasticsearch index: {e2}")

    @classmethod
    async def health_check(cls) -> dict:
        """Check Elasticsearch cluster health."""
        try:
            client = await cls.get_client()
            health = await client.cluster.health()
            return {"status": "healthy", "cluster": health}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
