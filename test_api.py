import requests
import json

# API Base URL
BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_ask_question(question):
    """Test ask question endpoint"""
    print(f"\n=== Testing Ask Question ===")
    print(f"Question: {question}")
    
    payload = {
        "question": question,
        "user_id": "test_user_123",
        "platform": "test"
    }
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Knowledge Assistant API - Test Script")
    print("=" * 60)
    
    try:
        # Test 1: Root endpoint
        test_root()
        
        # Test 2: Health check
        test_health()
        
        # Test 3: Ask a greeting
        test_ask_question("hi")
        
        # Test 4: Ask a real question
        test_ask_question("What information do you have?")
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the API.")
        print("Make sure the API is running with: uvicorn api:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
