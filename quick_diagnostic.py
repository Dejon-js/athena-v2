#!/usr/bin/env python3
"""
Quick Diagnostic for ATHENA v2.2 Critical Issues
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, method="GET", data=None):
    """Test an endpoint and return results"""
    print(f"\n🔍 Testing {name}...")
    print(f"   URL: {url}")

    start_time = time.time()
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)

        response_time = time.time() - start_time

        print(f"   Status: {response.status_code}")
        print(f"   Response Time: {response_time:.3f}s")
        print(f"   Success: {'✅' if response.status_code == 200 else '❌'}")

        if response.status_code == 200:
            try:
                content = response.json()
                print(f"   Response: {json.dumps(content, indent=2)[:200]}...")
                return True, content, response_time
            except:
                print(f"   Response: {response.text[:200]}...")
                return True, response.text, response_time
        else:
            print(f"   Error: {response.text}")
            return False, response.text, response_time

    except Exception as e:
        response_time = time.time() - start_time
        print(f"   Error: {str(e)}")
        print(f"   Response Time: {response_time:.3f}s")
        return False, str(e), response_time

def main():
    print("🚨 ATHENA v2.2 CRITICAL ISSUE DIAGNOSTIC")
    print("=" * 50)

    results = {}

    # 1. Basic Health
    results["health"] = test_endpoint("Basic Health", f"{BASE_URL}/health")

    # 2. Detailed Health
    results["detailed_health"] = test_endpoint("Detailed Health", f"{BASE_URL}/api/v1/health/detailed")

    # 3. API Configuration
    results["api_config"] = test_endpoint("API Configuration", f"{BASE_URL}/api/v1/health/apis")

    # 4. Database Health
    results["database"] = test_endpoint("Database Health", f"{BASE_URL}/api/v1/health/databases")

    # 5. Podcast Data Ingestion
    results["podcast_ingestion"] = test_endpoint("Podcast Ingestion",
                                                f"{BASE_URL}/api/v1/data/ingest?data_type=podcast_data",
                                                method="POST")

    # 6. Chat Query
    chat_data = {"query": "What do the podcasts say about Patrick Mahomes?"}
    results["chat_query"] = test_endpoint("Chat Query",
                                         f"{BASE_URL}/api/v1/chat/query",
                                         method="POST",
                                         data=chat_data)

    # 7. Data Status
    results["data_status"] = test_endpoint("Data Status", f"{BASE_URL}/api/v1/data/status")

    # Analyze Results
    print("\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    working_endpoints = sum(1 for result in results.values() if result[0])
    total_endpoints = len(results)

    print(f"Working Endpoints: {working_endpoints}/{total_endpoints}")

    # Check API keys
    if results["api_config"][0]:
        api_data = results["api_config"][1]
        if isinstance(api_data, dict) and "total_keys_configured" in api_data:
            keys_configured = api_data["total_keys_configured"]
            print(f"API Keys Configured: {keys_configured}/4")

    # Check databases
    if results["database"][0]:
        db_data = results["database"][1]
        if isinstance(db_data, dict):
            healthy_dbs = sum(1 for db in db_data.values() if isinstance(db, dict) and db.get("status") == "healthy")
            total_dbs = len(db_data)
            print(f"Healthy Databases: {healthy_dbs}/{total_dbs}")

    # Check podcast processing
    if results["podcast_ingestion"][0]:
        podcast_data = results["podcast_ingestion"][1]
        if isinstance(podcast_data, dict):
            result = podcast_data.get("result", {})
            episodes = result.get("episodes_processed", 0)
            transcripts = result.get("transcripts_generated", 0)
            print(f"Podcast Processing: {episodes} episodes, {transcripts} transcripts")

    # Performance analysis
    response_times = [result[2] for result in results.values() if result[2] > 0]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        print(f"Average Response Time: {avg_time:.3f}s")
        print(f"Max Response Time: {max_time:.3f}s")
    # Issue identification
    print("\n🚨 IDENTIFIED ISSUES:")    critical_issues = []
    warnings = []

    # Check API keys
    if results["api_config"][0]:
        api_data = results["api_config"][1]
        if isinstance(api_data, dict):
            total_keys = api_data.get("total_keys_configured", 0)
            if total_keys < 4:
                critical_issues.append(f"Missing {4 - total_keys} API keys")

    # Check database health
    if results["database"][0]:
        db_data = results["database"][1]
        if isinstance(db_data, dict):
            unhealthy_dbs = [name for name, db in db_data.items()
                           if isinstance(db, dict) and db.get("status") != "healthy"]
            if unhealthy_dbs:
                critical_issues.append(f"Unhealthy databases: {unhealthy_dbs}")

    # Check response times
    if response_times:
        slow_endpoints = [name for name, result in results.items()
                         if result[2] > 5.0]  # Over 5 seconds
        if slow_endpoints:
            warnings.append(f"Slow endpoints: {slow_endpoints}")

    # Check failed endpoints
    failed_endpoints = [name for name, result in results.items() if not result[0]]
    if failed_endpoints:
        critical_issues.append(f"Failed endpoints: {failed_endpoints}")

    if critical_issues:
        print("   CRITICAL:")
        for issue in critical_issues:
            print(f"   • {issue}")

    if warnings:
        print("   WARNINGS:")
        for warning in warnings:
            print(f"   • {warning}")

    if not critical_issues and not warnings:
        print("   ✅ No major issues detected!")

    print("\n🎯 DEPLOYMENT READINESS:")    success_rate = (working_endpoints / total_endpoints) * 100

    if success_rate >= 90:
        print("   ✅ READY FOR DEPLOYMENT")
    elif success_rate >= 70:
        print("   ⚠️ MOSTLY READY - Minor fixes needed")
    else:
        print("   ❌ NOT READY - Critical issues must be resolved")

if __name__ == "__main__":
    main()
