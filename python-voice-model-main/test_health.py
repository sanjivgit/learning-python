#!/usr/bin/env python3
"""
Health Check Test Script
Tests the health endpoint of the voice service
"""

import requests
import json
import sys
from typing import Dict, Any

def test_health_endpoint(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test the health endpoint"""

    print(f"Testing health endpoint at: {base_url}/health")
    print("-" * 50)

    try:
        response = requests.get(f"{base_url}/health", timeout=5)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Health check successful!")
            print(f"Overall Status: {data.get('status')}")
            print(f"Database: {data.get('database')}")
            print(f"Message: {data.get('message')}")

            # Determine if everything is working
            if data.get('status') == 'healthy' and data.get('database') == 'static-json':
                print("\n✅ All systems operational!")
                return {"success": True, "data": data}
            else:
                print("\n⚠️ Service is running but there are issues:")
                if data.get('database') != 'static-json':
                    print("  - Static dataset unavailable or invalid")
                return {"success": False, "data": data}
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return {"success": False, "error": response.text}

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - Is the server running?")
        return {"success": False, "error": "Connection failed"}
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"success": False, "error": str(e)}

def test_root_endpoint(base_url: str = "http://localhost:8000") -> bool:
    """Test the root endpoint"""

    print(f"\nTesting root endpoint at: {base_url}/")
    print("-" * 50)

    try:
        response = requests.get(base_url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint working!")
            print(f"Message: {data.get('message')}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error testing root endpoint: {e}")
        return False

def main():
    """Main test function"""
    print("🏥 Voice Service Health Check Test")
    print("=" * 50)

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

    # Test root endpoint
    root_ok = test_root_endpoint(base_url)

    # Test health endpoint
    health_result = test_health_endpoint(base_url)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"  Root Endpoint: {'✅ OK' if root_ok else '❌ FAILED'}")
    print(f"  Health Check: {'✅ OK' if health_result['success'] else '❌ FAILED'}")

    if health_result['success']:
        print("\n🎉 Your voice service is ready!")
        print("\nNext steps:")
        print("  1. Open test_voice_client.html in your browser")
        print("  2. Click 'Start session' to test voice functionality")
        print("  3. Allow microphone access when prompted")
    else:
        print("\n⚠️ Issues found. Please check:")
        print("  1. Is the server running? (uvicorn main:app --reload)")
        print("  2. Is the static dataset accessible under service/data/store.json?")
        print("  3. Are environment variables set correctly?")

    return health_result['success']

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)