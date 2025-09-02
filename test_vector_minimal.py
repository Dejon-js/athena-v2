#!/usr/bin/env python3
"""
Minimal test for ATHENA v2.2 Vector Database System
"""

import asyncio
import os
import sys

async def test_minimal_vector():
    """Test basic vector functionality."""
    try:
        print("🔍 Testing Minimal Vector System...")

        # Test ChromaDB
        import chromadb
        print("✅ ChromaDB imported")

        # Test sentence transformers
        from sentence_transformers import SentenceTransformer
        print("✅ Sentence Transformers imported")

        # Create a simple client
        client = chromadb.PersistentClient(path="./test_chroma_db")
        print("✅ ChromaDB client created")

        # Create collection
        collection = client.get_or_create_collection(name="test_collection")
        print("✅ Collection created")

        # Test embedding model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded")

        # Test embedding generation
        test_text = ["This is a test document about football"]
        embeddings = model.encode(test_text)
        print(f"✅ Embeddings generated: shape {embeddings.shape}")

        # Test adding to collection
        collection.add(
            embeddings=[embeddings.tolist()[0]],
            documents=test_text,
            ids=["test_doc_1"]
        )
        print("✅ Document added to collection")

        # Test querying
        query_text = ["NFL football games"]
        query_embedding = model.encode(query_text)

        results = collection.query(
            query_embeddings=[query_embedding.tolist()[0]],
            n_results=1
        )
        print(f"✅ Query successful: found {len(results['documents'][0])} results")

        print("\n🎉 MINIMAL VECTOR TEST PASSED!")
        print("✅ ChromaDB: Working")
        print("✅ Sentence Transformers: Working")
        print("✅ Vector operations: Working")

        return True

    except Exception as e:
        print(f"❌ Minimal vector test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_minimal_vector())
    sys.exit(0 if success else 1)
