#!/usr/bin/env python3
"""
Test server JWT configuration directly by importing the auth module
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

def test_server_jwt_config():
    """Test server JWT configuration"""
    
    print("=== Testing Server JWT Configuration ===")
    
    # Test environment loading
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    print(f"Environment JWT Secret: {'Found' if jwt_secret else 'Not Found'}")
    if jwt_secret:
        print(f"Environment JWT Secret length: {len(jwt_secret)}")
    
    # Test importing auth module
    try:
        from api.auth_endpoints import get_current_user
        print("✅ Successfully imported get_current_user")
        
        # Check if auth module has loaded environment
        import api.auth_endpoints as auth_module
        
        # Try to access the JWT secret from the auth module
        if hasattr(auth_module, 'JWT_SECRET_KEY'):
            auth_secret = auth_module.JWT_SECRET_KEY
            print(f"Auth module JWT Secret: {'Found' if auth_secret else 'Not Found'}")
            if auth_secret:
                print(f"Auth module JWT Secret length: {len(auth_secret)}")
                print(f"Secrets match: {jwt_secret == auth_secret}")
        else:
            print("❌ Auth module doesn't have JWT_SECRET_KEY attribute")
            
        # Test token validation using the auth module's method
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTI5NDgwMmMtMjIxOS00NjUxLWE0YTUtYTlhNWRhZTc1NDZmIiwidXNlcl90eXBlIjoicGVyc29uYWwiLCJhY19pZCI6InRlc3Q5OTkiLCJleHAiOjE3NTUxNTg4ODMsImlhdCI6MTc1NTA3MjQ4M30.Ni3uaM6qLM2iL-v-tubECX-oGofQ39omW2j-tSmTj-0"
        
        # Simulate what the server does
        try:
            # This would normally be called by FastAPI dependency injection
            # but we can't easily test that without running the full server
            print("Token validation would need to be tested with running server")
            
        except Exception as e:
            print(f"❌ Error testing token with auth module: {e}")
            
    except ImportError as e:
        print(f"❌ Failed to import auth module: {e}")
    except Exception as e:
        print(f"❌ Error testing auth module: {e}")

if __name__ == "__main__":
    test_server_jwt_config()