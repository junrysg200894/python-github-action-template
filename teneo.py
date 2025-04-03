import websockets
import asyncio
import json
import random
import time
import cloudscraper
from urllib.parse import quote_plus
from datetime import datetime, timedelta

webAppUrl = "https://dashboard.teneo.pro"
websocketUrl = "secure.ws.teneo.pro"
wsConnectionString = f"wss://{websocketUrl}/websocket"

scraper = cloudscraper.create_scraper(browser={
    'browser': 'chrome',
    'platform': 'windows',
    'desktop': True
})

def get_access_token():
    try:
        with open('token.txt', 'r') as file:
            access_token = file.read().strip()
            return access_token
    except Exception as e:
        print(f"Error reading access token from file: {e}")
        return None

potential_points = 0
countdown = "Calculating..."
last_updated = None
ping_interval = 10
ping_task = None

def update_countdown_and_points():
    global countdown, potential_points, last_updated
    try:
        if last_updated:
            next_heartbeat = last_updated + timedelta(minutes=15)
            now = datetime.now()
            diff = next_heartbeat - now

            if diff > timedelta(0):
                minutes = diff.seconds // 60
                seconds = diff.seconds % 60
                countdown = f"{minutes}m {seconds}s"

                max_points = 25
                time_elapsed = now - last_updated
                time_elapsed_minutes = time_elapsed.total_seconds() / 60
                new_points = min(max_points, (time_elapsed_minutes / 15) * max_points)
                new_points = round(new_points, 2)

                if random.random() < 0.1:
                    bonus = random.random() * 2
                    new_points = min(max_points, new_points + bonus)
                    new_points = round(new_points, 2)

                potential_points = new_points
            else:
                countdown = "Calculating..."
                potential_points = 25
        else:
            countdown = "Calculating..."
            potential_points = 0

        print(f"Countdown: {countdown}, Potential Points: {potential_points}")

    except Exception as e:
        print(f"Error updating countdown and points: {e}")

async def connect_websocket():
    global ping_task
    try:
        access_token = get_access_token()
        if not access_token:
            print("Access token is missing or invalid.")
            return
        
        version = "v0.2"
        
        ws_url = f"{wsConnectionString}?accessToken={quote_plus(access_token)}&version={quote_plus(version)}"
        
        print(f"Connecting to WebSocket: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            print("WebSocket connected")

            global last_updated
            last_updated = datetime.now()

            await websocket.send(json.dumps({"type": "PING"}))
            print("Sent Ping")

            countdown_interval = 1  # Update countdown every second
            countdown_task = asyncio.create_task(start_countdown_and_points(countdown_interval))

            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Received message: {data}")

                if 'pointsTotal' in data and 'pointsToday' in data:
                    points_total = data['pointsTotal']
                    points_today = data['pointsToday']
                    print(f"Points Total: {points_total}, Points Today: {points_today}")
                
    except Exception as e:
        print(f"Error connecting WebSocket: {e}")
        await reconnect_websocket()
    
# Function to start pinging the server
async def start_pinging(websocket, interval):
    global last_updated
    while True:
        await asyncio.sleep(interval)
        if websocket.open:
            await websocket.send(json.dumps({"type": "PING"}))
            last_updated = datetime.now()
            print(f"Sent Ping at {last_updated}")

async def start_countdown_and_points(interval):
    global countdown, potential_points, ping_task
    while True:
        update_countdown_and_points()  # Run immediately

        if countdown == "Calculating..." and not ping_task:
            print("Countdown finished, starting pinging...")
            ping_task = asyncio.create_task(start_pinging(websocket, ping_interval))  # Start pinging task

        await asyncio.sleep(interval)

async def reconnect_websocket():
    retry_interval = 20 
    print(f"Reconnecting in {retry_interval} seconds...")
    await asyncio.sleep(retry_interval)
    await connect_websocket()

# Function to start the bot
async def start_bot():
    await connect_websocket()

# Run the bot
asyncio.run(start_bot())
