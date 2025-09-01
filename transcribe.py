import assemblyai as aai 
import json
import requests
import os
import time
from datetime import datetime
from listennotes import podcast_api

# Initialize the ListenNotes API client
client = podcast_api.Client(api_key='9fffa86a38254ff990c33e7acdca2cd0')

# Initialize AssemblyAI
aai.settings.api_key = "5a512fcff0e44dd5921da66e6a87b18e"

def load_podcast_ids():
    """Load podcast IDs from the JSON file"""
    try:
        with open('podcasts_id.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Error: podcasts_id.json file not found")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in podcasts_id.json")
        return []

def create_batches(podcasts, batch_size=8):
    """Create 4 batches of 8 teams each"""
    batches = []
    for i in range(0, len(podcasts), batch_size):
        batch = podcasts[i:i + batch_size]
        batches.append(batch)
    return batches

def fetch_podcast_batch(podcast_batch):
    """Fetch podcast data for a batch of 8 podcasts using the batch endpoint"""
    try:
        # Extract podcast IDs from the batch
        podcast_ids = [podcast['id'] for podcast in podcast_batch]
        ids_param = ','.join(podcast_ids)
        
        print(f"   🔄 Fetching batch with IDs: {ids_param[:50]}...")
        
        # Use the batch endpoint with show_latest_episodes=1
        response = client.fetch_podcasts(
            ids=ids_param,
            show_latest_episodes=1
        )
        
        return response.json()
    except Exception as e:
        print(f"Error fetching podcast batch: {e}")
        return None

def transcribe_audio(audio_url):
    """Transcribe audio using AssemblyAI"""
    try:
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.universal,
            language_code="en"
        )
        transcript = aai.Transcriber(config=config).transcribe(audio_url)
        
        if transcript.status == "error":
            raise RuntimeError(f"Transcription failed: {transcript.error}")
        
        return transcript.text
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None

def save_transcript(team_name, episode_title, transcript, output_dir="transcripts"):
    """Save transcript to a file"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create team directory
        team_dir = os.path.join(output_dir, team_name.replace(" ", "_"))
        os.makedirs(team_dir, exist_ok=True)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length
        filename = f"{timestamp}_{safe_title}.txt"
        filepath = os.path.join(team_dir, filename)
        
        # Save transcript
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Team: {team_name}\n")
            f.write(f"Episode: {episode_title}\n")
            f.write(f"Transcribed: {datetime.now().isoformat()}\n")
            f.write("-" * 50 + "\n\n")
            f.write(transcript)
        
        print(f"   💾 Transcript saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving transcript: {e}")
        return None

def process_latest_episode(podcast_data, team_name):
    """Process the latest episode from podcast data"""
    if not podcast_data or 'latest_episodes' not in podcast_data:
        print(f"   ❌ No episodes found in podcast data for {team_name}")
        return False
    
    episodes = podcast_data['latest_episodes']
    if not episodes:
        print(f"   ❌ No episodes available for {team_name}")
        return False
    
    # Get the latest episode (first in the array)
    latest_episode = episodes[0]
    episode_title = latest_episode.get('title', 'Latest Episode')
    audio_url = latest_episode.get('audio')
    
    print(f"   📻 Latest episode: {episode_title[:60]}...")
    
    if not audio_url:
        print(f"   ⚠️  No audio URL for latest episode: {episode_title}")
        return False
    
    # Transcribe the latest episode
    print(f"   🎤 Transcribing latest episode...")
    transcript = transcribe_audio(audio_url)
    
    if transcript:
        print(f"   ✅ Transcription completed ({len(transcript)} characters)")
        
        # Save transcript
        save_transcript(team_name, episode_title, transcript)
        return True
    else:
        print(f"   ❌ Transcription failed for: {episode_title}")
        return False

def process_batch(batch, batch_num, total_batches):
    """Process a batch of 8 podcasts"""
    print(f"\n�� Processing Batch {batch_num}/{total_batches} ({len(batch)} teams)")
    print("=" * 60)
    
    # Fetch podcast data for the entire batch
    print("🔄 Fetching podcast data for batch...")
    batch_response = fetch_podcast_batch(batch)
    
    if not batch_response or 'podcasts' not in batch_response:
        print("❌ Failed to fetch batch data")
        return 0
    
    podcasts_data = batch_response['podcasts']
    successful_transcriptions = 0
    
    # Process each podcast in the batch
    for i, podcast_data in enumerate(podcasts_data):
        team_name = batch[i].get('team', 'Unknown Team')
        podcast_id = batch[i].get('id')
        
        print(f"\n[{i+1}/{len(podcasts_data)}] Processing {team_name} (ID: {podcast_id})")
        
        if podcast_data:
            print(f"✅ Successfully fetched data for {team_name}")
            print(f"   Title: {podcast_data.get('title', 'N/A')}")
            print(f"   Total Episodes: {podcast_data.get('total_episodes', 'N/A')}")
            
            # Process the latest episode
            if process_latest_episode(podcast_data, team_name):
                successful_transcriptions += 1
        else:
            print(f"❌ Failed to fetch data for {team_name}")
    
    # Add delay between batches to respect rate limits
    if batch_num < total_batches:
        print(f"\n⏳ Waiting 3 seconds before next batch...")
        time.sleep(3)
    
    return successful_transcriptions

def main():
    """Main function to process podcasts in batches"""
    print("🎧 NFL Podcast Transcription Tool - Latest Episodes")
    print("=" * 60)
    print("Processing 32 teams in 4 batches of 8 teams each")
    print("Transcribing the latest episode from each team")
    print("=" * 60)
    
    print("\nLoading podcast IDs from podcasts_id.json...")
    podcasts = load_podcast_ids()
    
    if not podcasts:
        print("No podcasts found. Exiting.")
        return
    
    print(f"Found {len(podcasts)} podcasts to process")
    
    # Create 4 batches of 8 teams each
    batches = create_batches(podcasts, batch_size=8)
    print(f"Created {len(batches)} batches of 8 teams each")
    
    total_successful = 0
    
    # Process each batch
    for batch_num, batch in enumerate(batches, 1):
        successful = process_batch(batch, batch_num, len(batches))
        total_successful += successful
    
    print(f"\n🎉 Processing complete!")
    print(f"Successfully transcribed {total_successful}/{len(podcasts)} teams")
    print(f"Check the 'transcripts' directory for results.")

if __name__ == "__main__":
    main()