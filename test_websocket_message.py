#!/usr/bin/env python3
"""
Test WebSocket message sending to debug the chat system
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    user_id = "5294802c-2219-4651-a4a5-a9a5dae7546f"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTI5NDgwMmMtMjIxOS00NjUxLWE0YTUtYTlhNWRhZTc1NDZmIiwidXNlcl90eXBlIjoicGVyc29uYWwiLCJhY19pZCI6InRlc3Q5OTkiLCJleHAiOjE3NTU1ODU4NTMsImlhdCI6MTc1NTQ5OTQ1M30.K2OHSu82GGtjCHURniVapItq0XHycft4cqssrnF0eEQ"
    
    uri = f"ws://localhost:8000/api/chat/ws/{user_id}?token={token}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Send a test question
            message = {
                "type": "question",
                "question": "내 적성에 맞는 직업은 무엇인가요?",
                "timestamp": "2025-08-18T16:00:00.000Z"
            }
            
            await websocket.send(json.dumps(message))
            print("Sent question:", message["question"])
            
            # Wait for responses
            timeout = 30  # 30 seconds timeout
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    data = json.loads(response)
                    print(f"Received {data['type']}: {data}")
                    
                    if data['type'] == 'response':
                        print("Got response! Breaking...")
                        break
                    elif data['type'] == 'error':
                        print("Got error! Breaking...")
                        break
                        
            except asyncio.TimeoutError:
                print(f"Timeout after {timeout} seconds")
                
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())