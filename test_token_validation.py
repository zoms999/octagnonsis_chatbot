#!/usr/bin/env python3
"""
Test token validation directly
"""

import os
import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_token_validation():
    """Test JWT token validation"""
    
    # Get JWT secret from environment
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    print(f"JWT Secret loaded: {'Yes' if jwt_secret else 'No'}")
    if jwt_secret:
        print(f"JWT Secret length: {len(jwt_secret)}")
    
    # Test token from the curl request
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTI5NDgwMmMtMjIxOS00NjUxLWE0YTUtYTlhNWRhZTc1NDZmIiwidXNlcl90eXBlIjoicGVyc29uYWwiLCJhY19pZCI6InRlc3Q5OTkiLCJleHAiOjE3NTUxNTg4ODMsImlhdCI6MTc1NTA3MjQ4M30.Ni3uaM6qLM2iL-v-tubECX-oGofQ39omW2j-tSmTj-0"
    
    try:
        # Decode without verification first to see the payload
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        print(f"Unverified payload: {unverified_payload}")
        
        # Check expiration
        import time
        current_time = int(time.time())
        exp_time = unverified_payload.get('exp', 0)
        print(f"Current time: {current_time}")
        print(f"Token exp time: {exp_time}")
        print(f"Token expired: {current_time > exp_time}")
        
        if jwt_secret:
            # Try to decode with verification
            try:
                verified_payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
                print(f"✅ Token verification successful: {verified_payload}")
                return True
            except jwt.ExpiredSignatureError:
                print("❌ Token has expired")
                return False
            except jwt.InvalidTokenError as e:
                print(f"❌ Token validation failed: {e}")
                return False
        else:
            print("❌ No JWT secret found in environment")
            return False
            
    except Exception as e:
        print(f"❌ Error testing token: {e}")
        return False

if __name__ == "__main__":
    test_token_validation()