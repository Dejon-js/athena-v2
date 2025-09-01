import json
import os
from collections import defaultdict

def reorganize_podcasts_data():
    """
    Reorganize the podcasts_id.json file into a hierarchical structure
    where teams contain their players and coaches.
    """
    
    # Read the current data
    print("Reading podcasts_id.json...")
    with open(r'C:\Users\Dejon\Documents\podcasts_id.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} total entries")
    
    # Initialize the new structure
    new_structure = {
        "league": {
            "id": "3c6d318a-6164-4290-9bbc-bf9bb21cc4b8",
            "name": "National Football League",
            "alias": "NFL"
        },
        "teams": []
    }
    
    # Track teams and their data
    teams_data = defaultdict(lambda: {
        "players": [],
        "coaches": [],
        "team_info": None
    })
    
    # Process each entry
    for entry in data:
        # Check if this is a team entry (has podcast_id and team info)
        if "podcast_id" in entry or ("id" in entry and "team" in entry and isinstance(entry["team"], str)):
            # This is a team entry
            team_id = entry.get("team_id") or entry.get("id")
            team_name = entry.get("team")
            
            if team_id and team_name:
                teams_data[team_id]["team_info"] = {
                    "id": team_id,
                    "name": team_name,
                    "market": entry.get("market"),
                    "alias": entry.get("alias"),
                    "sr_id": entry.get("sr_id"),
                    "podcast_id": entry.get("id")  # This is the podcast ID
                }
        
        # Check if this is a player entry (has position and name)
        elif "position" in entry and "name" in entry:
            position = entry["position"]
            name = entry["name"]
            
            # Skip coaching positions
            if position in ["Head Coach", "Offensive Coordinator", "Defensive Coordinator", "Special Teams Coordinator"]:
                # This is a coach
                team_id = entry.get("team_id") or entry.get("team", {}).get("id")
                if team_id:
                    teams_data[team_id]["coaches"].append({
                        "id": entry.get("id"),
                        "name": name,
                        "position": position
                    })
            else:
                # This is a player
                team_id = entry.get("team_id") or entry.get("team", {}).get("id")
                if team_id:
                    player_data = {
                        "id": entry.get("id"),
                        "name": name,
                        "position": position
                    }
                    
                    # Add additional player fields if they exist
                    for field in ["jersey_number", "height", "weight", "age", "experience", "college"]:
                        if field in entry:
                            player_data[field] = entry[field]
                    
                    teams_data[team_id]["players"].append(player_data)
    
    # Build the final structure
    for team_id, team_data in teams_data.items():
        if team_data["team_info"]:
            team_entry = team_data["team_info"].copy()
            team_entry["players"] = team_data["players"]
            team_entry["coaches"] = team_data["coaches"]
            new_structure["teams"].append(team_entry)
    
    # Sort teams alphabetically by name
    new_structure["teams"].sort(key=lambda x: x["name"])
    
    # Sort players and coaches within each team
    for team in new_structure["teams"]:
        team["players"].sort(key=lambda x: x["name"])
        team["coaches"].sort(key=lambda x: x["name"])
    
    # Write the reorganized data
    output_file = "podcasts_id_reorganized.json"
    print(f"Writing reorganized data to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(new_structure, f, indent=2, ensure_ascii=False)
    
    # Print summary
    total_teams = len(new_structure["teams"])
    total_players = sum(len(team["players"]) for team in new_structure["teams"])
    total_coaches = sum(len(team["coaches"]) for team in new_structure["teams"])
    
    print(f"\nReorganization complete!")
    print(f"Teams: {total_teams}")
    print(f"Total Players: {total_players}")
    print(f"Total Coaches: {total_coaches}")
    print(f"Output file: {output_file}")
    
    # Show sample structure
    if new_structure["teams"]:
        sample_team = new_structure["teams"][0]
        print(f"\nSample team structure ({sample_team['name']}):")
        print(f"  - Players: {len(sample_team['players'])}")
        print(f"  - Coaches: {len(sample_team['coaches'])}")
        print(f"  - Podcast ID: {sample_team.get('podcast_id', 'N/A')}")

if __name__ == "__main__":
    reorganize_podcasts_data()
