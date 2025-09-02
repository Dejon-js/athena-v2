#!/usr/bin/env python3
"""
Simple Diagnostic for ATHENA v2.2
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, method="GET", data=None):
    print(f"\n🔍 Testing {name}...")
    start_time = time.time()
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)

        response_time = time.time() - start_time
        success = response.status_code == 200

        print(f"   Status: {response.status_code}")
        print(f"   Response Time: {response_time:.3f}s")
        print(f"   Success: {'✅' if success else '❌'}")

        if success:
            try:
                content = response.json()
                return True, content, response_time
            except:
                return True, response.text, response_time
        else:
            return False, response.text, response_time

    except Exception as e:
        response_time = time.time() - start_time
        print(f"   Error: {str(e)}")
        return False, str(e), response_time

def main():
    print("🚨 ATHENA v2.2 SIMPLE DIAGNOSTIC")
    print("=" * 40)

    # Test all endpoints
    endpoints = [
        ("Basic Health", f"{BASE_URL}/health"),
        ("Detailed Health", f"{BASE_URL}/api/v1/health/detailed"),
        ("API Configuration", f"{BASE_URL}/api/v1/health/apis"),
        ("Database Health", f"{BASE_URL}/api/v1/health/databases"),
    ]

    results = {}
    for name, url in endpoints:
        results[name] = test_endpoint(name, url)

    # Test podcast ingestion
    results["Podcast Ingestion"] = test_endpoint(
        "Podcast Ingestion",
        f"{BASE_URL}/api/v1/data/ingest?data_type=podcast_data",
        method="POST"
    )

    # Test chat
    chat_data = {"query": "What do the podcasts say about Patrick Mahomes?"}
    results["Chat Query"] = test_endpoint(
        "Chat Query",
        f"{BASE_URL}/api/v1/chat/query",
        method="POST",
        data=chat_data
    )

    # Summary
    print("\n📊 SUMMARY")
    print("=" * 40)

    working = sum(1 for result in results.values() if result[0])
    total = len(results)

    print(f"Working Endpoints: {working}/{total}")

    # Check API keys
    if results["API Configuration"][0]:
        api_data = results["API Configuration"][1]
        if isinstance(api_data, dict) and "total_keys_configured" in api_data:
            keys = api_data["total_keys_configured"]
            print(f"API Keys Configured: {keys}/4")
            if keys < 4:
                print(f"⚠️  Missing {4 - keys} API keys")

    # Check databases
    if results["Database Health"][0]:
        db_data = results["Database Health"][1]
        if isinstance(db_data, dict):
            healthy = sum(1 for db in db_data.values()
                         if isinstance(db, dict) and db.get("status") == "healthy")
            total_dbs = len(db_data)
            print(f"Healthy Databases: {healthy}/{total_dbs}")

    # Check podcast processing
    if results["Podcast Ingestion"][0]:
        podcast_data = results["Podcast Ingestion"][1]
        if isinstance(podcast_data, dict):
            result = podcast_data.get("result", {})
            episodes = result.get("episodes_processed", 0)
            transcripts = result.get("transcripts_generated", 0)
            print(f"Podcast Processing: {episodes} episodes, {transcripts} transcripts")

    # Performance
    response_times = [result[2] for result in results.values() if result[2] > 0]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        print(f"Average Response Time: {avg_time:.3f}s")
        print(f"Max Response Time: {max_time:.3f}s")

    # Readiness assessment
    success_rate = (working / total) * 100
    print("\n🎯 READINESS ASSESSMENT:")    if success_rate >= 90:
        print("   ✅ EXCELLENT - Ready for deployment")
    elif success_rate >= 75:
        print("   ⚠️ GOOD - Minor issues to resolve")
    elif success_rate >= 60:
        print("   🟡 FAIR - Needs attention")
    else:
        print("   ❌ POOR - Critical issues")

    print(f"   Success Rate: {success_rate:.1f}%")

if __name__ == "__main__":
    main()
