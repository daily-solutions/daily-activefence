from daily import *
import requests
import sys
import json
import os
import base64
import boto3
import botocore.session
from PIL import Image
import io
import time
import uuid
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import time

MID = '\033[93m'
HIGH = '\033[91m'
RESET = '\033[0m'
CYAN = '\033[96m'
BLUE = '\033[94m'

hostName = "localhost"
serverPort = 8080

# Change these values to use your own room and bot name.
ROOM_URL = "https://YOURDOMAIN.daily.co/YOURROOM"
NGROK_URL = "http://YOUR_NGROK.ngrok.io/activefence"
BOT_NAME = "Moderator"
ACTIVEFENCE_API_KEY = "YOUR_ACTIVEFENCE_KEY"

class MyHandler(BaseHTTPRequestHandler):
	def __init__(self, moderator, *args):
		self.moderator = moderator
		BaseHTTPRequestHandler.__init__(self, *args)
		
	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		self.end_headers()
			
	def do_HEAD(self):
		self._set_headers()
			
	def do_POST(self):
		length = int(self.headers.get('content-length'))
		message = json.loads(self.rfile.read(length))
		
		# Ignore "hate speech" results for now because it makes the logs noisy
		if not ('abusive_or_harmful.hate_speech' in message['analyzed_violations']):
			print(f"{CYAN}\n<<<<< POST received: {message}{RESET}")
			
			# Use the analyzed_violations from this response to set scores in the moderator.
			# `analyzed_violations` will contain all things that were analyzed, but `violations`
			# will only contain entries that were non-zero, so default everything to zero first
			if message['analyzed_violations']:
				new_scores = {}
				for v in message['analyzed_violations']:
					new_scores[v] = 0.0
				for v in message['violations']:
					new_scores[v['violation_type']] = v['risk_score']
				participant = message['entity_id']
				self.moderator.update_scores(participant, new_scores)

			self._set_headers()
			self.wfile.write(json.dumps({'hello': 'world', 'received': 'ok'}).encode('utf-8'))
	
	def do_GET(self):
		print("!!! GOT GET")
		
		self._set_headers()
		self.wfile.write(json.dumps({'hello': 'world', 'received': 'ok'}).encode('utf-8'))
	
	def log_message(self, format, *args):
		return

class Moderator(EventHandler):
	def __init__(self, room_url):
		self.room_url = room_url
		print(f"Joining room: {room_url}")
		
		# Specify how often to send a frame to ActiveFence. Standard
		# video tracks are 30fps, so set to 60 frames to send every 2 sec
		self.frame_cadence = 60
		
		# Count frames to know when to send one
		self.frame_count = 0
		
		# Set up violation type score tracking
		self.scores = {}
		
		Daily.init(virtual_devices=True)
		self.client = CallClient(event_handler = self)
		self.client.update_inputs({"camera": False, "microphone": False})
		self.client.set_user_name(BOT_NAME)
		self.client.join(room_url)
		
	def leave(self):
		self.client.leave()
		
	def pct_and_bar(self, pct):
		str = f"{pct:>3.0%} "
		str = str + ("█" * int(pct * 25.0))
		if pct >= 0.9:
			str = HIGH + str + RESET
		elif pct >= 0.5:
			str = MID + str + RESET
		
		return str
	
	def update_scores(self, participant, new_scores):
		# daily-python beta bug: remove quotes from participant id
		participant = participant.replace('"', '')
		if not participant in self.scores:
			self.scores[participant] = {}
			
		self.scores[participant].update(new_scores)

		# Send the updated scores to the Daily call.
		self.client.send_app_message({ "riskScores": self.scores })

		for k in self.scores.keys():
			pax = self.scores[k]
			print(f"\n>>>>> Sending scores to call: {datetime.now().isoformat()}")
			print(f"Participant: {k}")
			alc = self.pct_and_bar(pax['unauthorised_sales.alcohol'])
			wpn = self.pct_and_bar(pax['unauthorised_sales.weapons'])
			print(f"Alcohol: {alc}")
			print(f"Weapons: {wpn}")

	def on_participant_joined(self, participant):
		print(f"Participant joined: {participant}")
		print(f"Self: {self}")
		self.client.set_video_renderer(participant["id"], self.on_video_frame, 'camera', 'ABGR32')
	
	def async_post(self, url, headers, payload, participant):
		print(f"\n{BLUE}>>>>> Sending frame from participant {participant} to {url}{RESET}")
		response = requests.request("POST", url, headers=headers, data=payload)
		# Uncomment this line to check the initial response from ActiveFence.
		# You should see some categories in `analyzed_violations`. If this object
		# is empty, contact ActiveFence to turn on some content analyzers.
		
		print(f"{BLUE}ActiveFence POST response: {response.json()}{RESET}")
				
	def on_video_frame(self, participant, frame):
		self.frame_count += 1
		if self.frame_count >= self.frame_cadence:
			self.frame_count = 0
			
			IMAGE_WIDTH = frame.width
			IMAGE_HEIGHT = frame.height
			COLOR_FORMAT = frame.color_format
			a_image = Image.frombytes('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), frame.buffer)
			image = a_image.convert('RGB')
			
			# Uncomment these lines to write the frame to a jpg in the same directory.
			# current_path = os.getcwd()
			# image_path = os.path.join(current_path, "image.jpg")
			# image.save(image_path, format="JPEG")
			
			jpeg_buffer = io.BytesIO()
			
			image.save(jpeg_buffer, format='JPEG')
			
			jpeg_bytes = jpeg_buffer.getvalue()
			b64_image = base64.b64encode(jpeg_bytes).decode('utf-8')
			
			url = "https://apis.activefence.com/v3/content/image"
			
			payload = json.dumps({
				# shorthand way to associate scores with a participant for now
				"content_id": participant,
				"callback_url": NGROK_URL,
				"user_id": participant,
				"raw_media": b64_image,
				"mime_type": "image/jpeg"
			})
						
			headers = {
				'Content-Type': 'application/json',
				'af-api-key': ACTIVEFENCE_API_KEY
			}

			x = threading.Thread(target=self.async_post, args=(url, headers, payload, participant))

			x.start()			

def main():
	print("Server starting http://%s:%s" % (hostName, serverPort))

	moderator = Moderator(ROOM_URL)
	def handler(*args):
		MyHandler(moderator, *args)
	webserver = HTTPServer((hostName, serverPort), handler)

	try :
	  webserver.serve_forever()
	except KeyboardInterrupt:
		moderator.leave()
		webserver.server_close()
		print("Server stopped.")

if __name__ == '__main__':
	main()