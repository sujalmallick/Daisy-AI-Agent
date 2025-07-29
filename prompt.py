import requests  # For sending HTTP requests
import json      # For parsing JSON responses

API_URL = "http://localhost:8000/command"  # FastAPI backend endpoint

print("🎧 Spotify Agent CLI")
print("Type a command (e.g., play Starboy, pause, next). Type 'exit' to quit.\n")

while True:
    try:
        # Prompt user for input
        user_input = input("Your command: ").strip().lower()

        # Exit condition
        if user_input in ['exit', 'quit', 'q']:
            print("👋 Exiting. See you next vibe!")
            break

        # Send command to backend
        response = requests.post(API_URL, json={"prompt": user_input})

        # Parse the response JSON
        data = response.json()

        # Display relevant message
        if "response" in data:
            print("🎵", data["response"])
        elif "msg" in data:
            print("🎵", data["msg"])
        elif "error" in data:
            print("❌", data["error"])
        else:
            print("⚠️ Unexpected response format:", data)

    except requests.exceptions.RequestException as e:
        print("❌ Connection error:", str(e))
    except json.JSONDecodeError:
        print("⚠️ Failed to parse server response.")
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user.")
        break
