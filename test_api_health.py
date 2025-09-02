#!/usr/bin/env python3
"""
Quick test for API health endpoint
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api_health():
    """Test the API health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health/apis", timeout=10)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("API Health Response:")
            print(json.dumps(data, indent=2))

            # Check configured keys
            if "api_keys_configured" in data:
                configured = data["api_keys_configured"]
                total = data.get("total_keys_configured", 0)

                print(f"\nTotal API Keys Configured: {total}/5")

                for api, is_configured in configured.items():
                    status = "✅" if is_configured else "❌"
                    print(f"  {api}: {status}")

                # Check specifically for SportRadar
                if "sportradar" in configured:
                    sportradar_status = "✅ CONFIGURED" if configured["sportradar"] else "❌ MISSING"
                    print(f"\nSportRadar API Key: {sportradar_status}")

                if "sportsdata" in configured:
                    sportsdata_status = "✅ CONFIGURED" if configured["sportsdata"] else "❌ MISSING"
                    print(f"SportsData API Key: {sportsdata_status}")

        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_health()
