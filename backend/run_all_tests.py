import subprocess
import sys

def run_tests():
    print("\n" + "="*70)
    print("🏃 RUNNING COMPLETE AUTHENTICATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("test_auth_complete.py", "Complete Authentication Tests"),
        ("test_rbac.py", "Role-Based Access Control Tests"),
        ("test_jwt.py", "JWT Token Tests"),
        ("test_sessions.py", "Session Management Tests"),
        ("test_performance.py", "Performance Tests")
    ]
    
    results = []
    
    for test_file, test_name in tests:
        print(f"\n{'='*70}")
        print(f"Running: {test_name}")
        print(f"{'='*70}")
        
        try:
            result = subprocess.run([sys.executable, test_file], 
                                  capture_output=True, 
                                  text=True)
            
            if result.returncode == 0:
                print(f"✅ {test_name} completed successfully")
                results.append(True)
            else:
                print(f"❌ {test_name} failed")
                print(result.stderr)
                results.append(False)
        except Exception as e:
            print(f"❌ Error running {test_name}: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "="*70)
    print("📊 OVERALL TEST SUMMARY")
    print("="*70)
    
    for (_, test_name), success in zip(tests, results):
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED! Authentication system is fully functional!")
        print("\n✨ You can now proceed to the next module with confidence!")
    else:
        print("\n⚠️  Some tests failed. Please review the output above and fix the issues.")

if __name__ == "__main__":
    run_tests()