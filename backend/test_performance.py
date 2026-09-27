import requests
import time
import concurrent.futures
import statistics

BASE_URL = "http://localhost:8000/api"

def test_login_performance():
    print("\n" + "="*60)
    print("⚡ PERFORMANCE TESTING")
    print("="*60)
    
    # Test with multiple concurrent requests
    def make_request():
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "admin@university.edu",
            "password": "admin123"
        })
        end_time = time.time()
        return end_time - start_time, response.status_code
    
    # Run 10 concurrent requests
    print("\n📊 Testing with 10 concurrent login requests...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    times = [r[0] for r in results]
    status_codes = [r[1] for r in results]
    
    print(f"✅ Successful requests: {status_codes.count(200)}/10")
    print(f"⏱️  Average response time: {statistics.mean(times):.3f} seconds")
    print(f"⏱️  Fastest response: {min(times):.3f} seconds")
    print(f"⏱️  Slowest response: {max(times):.3f} seconds")
    
    # Test token validation performance
    print("\n📊 Testing token validation performance...")
    
    # First get a token
    login_response = requests.post(f"{BASE_URL}/auth/login/", json={
        "email": "admin@university.edu",
        "password": "admin123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()['token']
        
        def validate_token():
            start_time = time.time()
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{BASE_URL}/auth/me/", headers=headers)
            end_time = time.time()
            return end_time - start_time, response.status_code
        
        # Run 20 token validations
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(validate_token) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        times = [r[0] for r in results]
        status_codes = [r[1] for r in results]
        
        print(f"✅ Successful validations: {status_codes.count(200)}/20")
        print(f"⏱️  Average validation time: {statistics.mean(times):.3f} seconds")
        print(f"⏱️  Fastest validation: {min(times):.3f} seconds")
        print(f"⏱️  Slowest validation: {max(times):.3f} seconds")

if __name__ == "__main__":
    test_login_performance()