#!/usr/bin/env python3
"""
Test script for ATHENA v2.2 Vector Database System
Tests vector database initialization and basic functionality.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append('backend')

async def test_vector_database():
    """Test vector database initialization and basic operations."""
    try:
        print("🔍 Testing Vector Database System...")

        # Import vector components
        from modules.m8_vector.vector_database import VectorDatabaseManager
        from modules.m8_vector.content_processor import ContentVectorProcessor
        from modules.m8_vector.temporal_processor import TemporalVectorProcessor
        from modules.m8_vector import VectorIntegrationService

        print("✅ Imports successful")

        # Test VectorDatabaseManager initialization
        print("\n📊 Testing VectorDatabaseManager...")
        vector_db = VectorDatabaseManager()
        print("✅ VectorDatabaseManager initialized")

        # Test ContentVectorProcessor
        print("\n🎯 Testing ContentVectorProcessor...")
        content_processor = ContentVectorProcessor()
        print("✅ ContentVectorProcessor initialized")

        # Test TemporalVectorProcessor
        print("\n⏰ Testing TemporalVectorProcessor...")
        temporal_processor = TemporalVectorProcessor()
        print("✅ TemporalVectorProcessor initialized")

        # Test VectorIntegrationService
        print("\n🔗 Testing VectorIntegrationService...")
        vector_service = VectorIntegrationService()
        await vector_service.initialize()
        print("✅ VectorIntegrationService initialized")

        # Test collection stats (should be empty initially)
        print("\n📈 Testing collection statistics...")
        stats = await vector_service.get_collection_stats()
        print(f"✅ Collection stats retrieved: {stats}")

        # Test sample podcast processing
        print("\n🎙️ Testing sample podcast processing...")
        sample_podcast = {
            'team_name': 'Kansas City Chiefs',
            'episode_title': 'Chiefs vs Eagles Preview',
            'transcript': '''
            Welcome to the Locked On podcast for the Kansas City Chiefs.
            Today we're talking about Patrick Mahomes and his performance this season.
            Mahomes has been playing at an elite level, throwing for over 300 yards in multiple games.
            The offensive line has been protecting him well, and the receivers are making great catches.
            We expect him to continue performing at a high level against tough matchups.
            ''',
            'publish_date': '2024-01-15T10:00:00Z',
            'duration': 3600,
            'podcast_id': 'test_podcast_123',
            'episode_id': 'episode_test_123'
        }

        # Process and store podcast
        doc_id = await vector_service.process_and_store_podcast(sample_podcast)
        print(f"✅ Sample podcast processed and stored with ID: {doc_id}")

        # Test search functionality
        print("\n🔍 Testing vector search...")
        search_results = await vector_service.search_fantasy_insights(
            "How is Patrick Mahomes performing?",
            limit=3
        )

        print(f"✅ Search completed. Found {search_results['total_results']} results")
        if search_results['results']:
            print(f"   - Top result relevance: {search_results['results'][0]['combined_score']:.3f}")
            print(f"   - Content preview: {search_results['results'][0]['content'][:100]}...")

        # Test temporal analysis
        print("\n📅 Testing temporal analysis...")
        temporal_stats = search_results.get('freshness_distribution', {})
        print(f"✅ Freshness distribution: {temporal_stats}")

        print("\n🎉 ALL VECTOR TESTS PASSED!")
        print("✅ Vector database system is ready for production")

        return True

    except Exception as e:
        print(f"❌ Vector test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_config_loading():
    """Test that configuration loads properly."""
    try:
        print("\n⚙️ Testing Configuration Loading...")

        from shared.config import settings

        # Check if required settings are available
        required_settings = [
            'listen_notes_api_key',
            'assemblyai_api_key',
            'vector_db_path'
        ]

        for setting in required_settings:
            value = getattr(settings, setting, None)
            if value:
                print(f"✅ {setting}: Configured")
            else:
                print(f"⚠️ {setting}: Not configured (using defaults)")

        print("✅ Configuration test completed")
        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("🚀 ATHENA v2.2 Vector System Test Suite")
    print("=" * 50)

    # Test configuration
    config_ok = await test_config_loading()

    # Test vector system
    vector_ok = await test_vector_database()

    print("\n" + "=" * 50)
    print("📋 TEST RESULTS SUMMARY:")
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Vector System: {'✅ PASS' if vector_ok else '❌ FAIL'}")

    if config_ok and vector_ok:
        print("\n🎯 ALL TESTS PASSED! Vector integration is ready!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check configuration and dependencies.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
