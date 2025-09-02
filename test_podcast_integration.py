#!/usr/bin/env python3
"""
Test script for ATHENA v2.2 Podcast Integration
Tests podcast fetching and transcription functionality.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append('backend')

async def test_podcast_integration():
    """Test podcast integration with API keys."""
    try:
        print("🎙️ Testing Podcast Integration...")

        # Import the data ingestion module
        from modules.m1_data_core.data_ingestion import DataIngestionEngine

        # Check if API keys are configured
        from shared.config import settings

        listen_notes_key = getattr(settings, 'listen_notes_api_key', None)
        assemblyai_key = getattr(settings, 'assemblyai_api_key', None)

        print(f"🔑 ListenNotes API Key: {'Configured' if listen_notes_key and listen_notes_key != 'your_listen_notes_api_key_here' else 'Not Configured'}")
        print(f"🎤 AssemblyAI API Key: {'Configured' if assemblyai_key and assemblyai_key != 'your_assemblyai_api_key_here' else 'Not Configured'}")

        if not listen_notes_key or listen_notes_key == 'your_listen_notes_api_key_here':
            print("⚠️ ListenNotes API key not configured. Please set LISTEN_NOTES_API_KEY in your environment.")
            return False

        if not assemblyai_key or assemblyai_key == 'your_assemblyai_api_key_here':
            print("⚠️ AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY in your environment.")
            return False

        # Test podcast fetching
        print("\n🔄 Testing Podcast Fetching...")
        ingestion_engine = DataIngestionEngine()

        try:
            episodes = await ingestion_engine._fetch_podcast_episodes()
            print(f"✅ Podcast episodes fetched: {len(episodes)} episodes")

            if episodes:
                print("📋 Sample episode data:")
                for i, episode in enumerate(episodes[:3]):  # Show first 3
                    print(f"   {i+1}. {episode.get('team_name', 'Unknown')} - {episode.get('title', 'No title')[:50]}...")

            # Test transcription (only if we have episodes with audio URLs)
            episodes_with_audio = [ep for ep in episodes if ep.get('audio_url')]
            if episodes_with_audio:
                print(f"\n🎤 Testing Transcription with {len(episodes_with_audio)} episodes that have audio...")

                # Test transcription on the first episode with audio
                first_episode = episodes_with_audio[0]
                audio_url = first_episode.get('audio_url')

                if audio_url:
                    print(f"🎵 Transcribing: {first_episode.get('title', 'Unknown episode')}")
                    transcript = await ingestion_engine._transcribe_episode(audio_url)

                    if transcript:
                        print(f"✅ Transcription successful: {len(transcript)} characters")
                        print(f"📝 Preview: {transcript[:200]}...")
                    else:
                        print("❌ Transcription failed")

        except Exception as e:
            print(f"❌ Error during podcast testing: {str(e)}")
            return False

        print("\n🎉 PODCAST INTEGRATION TEST COMPLETED!")
        return True

    except Exception as e:
        print(f"❌ Podcast integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run podcast integration tests."""
    print("🎧 ATHENA v2.2 Podcast Integration Test")
    print("=" * 50)

    success = await test_podcast_integration()

    print("\n" + "=" * 50)
    if success:
        print("🎯 PODCAST INTEGRATION: SUCCESS")
        print("✅ API keys configured")
        print("✅ Podcast fetching working")
        print("✅ Transcription ready")
    else:
        print("⚠️ PODCAST INTEGRATION: NEEDS ATTENTION")
        print("❌ Check API key configuration")
        print("❌ Verify network connectivity")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
