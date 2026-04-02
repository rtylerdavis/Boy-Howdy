# Compare incoming video with known faces
# Running in a local python instance to get around PATH issues

# Import time so we can start timing asap
import time

# Start timing
timings = {
	"st": time.time()
}

# Import required modules
import sys
import os
import json
import configparser
import cv2
from datetime import timezone, datetime
import atexit
import subprocess
import snapshot
import numpy as np
import threading
import paths_factory
from recorders.video_capture import VideoCapture
from i18n import _

def exit(code=None):
	"""Exit while closing howdy-gtk properly"""
	global gtk_proc

	# Exit the auth ui process if there is one
	if "gtk_proc" in globals():
		gtk_proc.terminate()

	# Exit compare
	if code is not None:
		sys.exit(code)


def init_detector(lock):
	"""Start face detector and recognizer in a new thread"""
	global face_detector, face_recognizer

	# Test if model files exist
	if not os.path.isfile(paths_factory.face_detector_path()):
		print(_("Model files have not been downloaded, please run the following commands:"))
		print("\n\tcd " + paths_factory.model_data_dir_path())
		print("\tsudo ./install.sh\n")
		lock.release()
		exit(1)

	# Initialize YuNet face detector
	face_detector = cv2.FaceDetectorYN.create(
		paths_factory.face_detector_path(),
		"",
		(320, 320),
		score_threshold=detection_threshold,
		nms_threshold=0.3,
		top_k=5000
	)

	# Initialize SFace face recognizer
	face_recognizer = cv2.FaceRecognizerSF.create(
		paths_factory.face_recognizer_path(),
		""
	)

	# Note the time it took to initialize detectors
	timings["ll"] = time.time() - timings["ll"]
	lock.release()


def make_snapshot(type):
	"""Generate snapshot after detection"""
	snapshot.generate(snapframes, [
		type + _(" LOGIN"),
		_("Date: ") + datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S UTC"),
		_("Scan time: ") + str(round(time.time() - timings["fr"], 2)) + "s",
		_("Frames: ") + str(frames) + " (" + str(round(frames / (time.time() - timings["fr"]), 2)) + "FPS)",
		_("Hostname: ") + os.uname().nodename,
		_("Best similarity: ") + str(round(best_similarity, 3))
	])


def send_to_ui(type, message):
	"""Send message to the auth ui"""
	global gtk_proc

	# Only execute of the process started
	if "gtk_proc" in globals():
		# Format message so the ui can parse it
		message = type + "=" + message + " \n"

		# Try to send the message to the auth ui, but it's okay if that fails
		try:
			if gtk_proc.poll() is None:
				gtk_proc.stdin.write(bytearray(message.encode("utf-8")))
				gtk_proc.stdin.flush()
		except IOError:
			pass


# Make sure we were given an username to test against
if len(sys.argv) < 2:
	exit(12)

# The username of the user being authenticated
user = sys.argv[1]
# The model file contents
models = []
# Encoded face models (numpy arrays)
encodings = []
# Amount of ignored 100% black frames
black_tries = 0
# Amount of ignored dark frames
dark_tries = 0
# Total amount of frames captured
frames = 0
# Captured frames for snapshot capture
snapframes = []
# Tracks the best (highest) cosine similarity in the loop
best_similarity = 0
# Face detection/recognition instances
face_detector = None
face_recognizer = None

# Try to load the face model from the models folder
try:
	models = json.load(open(paths_factory.user_model_path(user)))

	for model in models:
		for encoding in model["data"]:
			encodings.append(np.array(encoding, dtype=np.float32))
except FileNotFoundError:
	exit(10)

# Check if the file contains a model
if len(models) < 1:
	exit(10)

# Read config from disk
config = configparser.ConfigParser()
config.read(paths_factory.config_file_path())

# Get all config values needed
timeout = config.getint("video", "timeout", fallback=4)
dark_threshold = config.getfloat("video", "dark_threshold", fallback=50.0)
video_certainty = config.getfloat("video", "certainty", fallback=0.40)
detection_threshold = config.getfloat("video", "detection_threshold", fallback=0.9)
end_report = config.getboolean("debug", "end_report", fallback=False)
save_failed = config.getboolean("snapshots", "save_failed", fallback=False)
save_successful = config.getboolean("snapshots", "save_successful", fallback=False)
gtk_stdout = config.getboolean("debug", "gtk_stdout", fallback=False)
rotate = config.getint("video", "rotate", fallback=0)

# Send the gtk output to the terminal if enabled in the config
gtk_pipe = sys.stdout if gtk_stdout else subprocess.DEVNULL

# Start the auth ui, register it to be always be closed on exit
try:
	gtk_proc = subprocess.Popen(["howdy-gtk", "--start-auth-ui"], stdin=subprocess.PIPE, stdout=gtk_pipe, stderr=gtk_pipe)
	atexit.register(exit)
except FileNotFoundError:
	pass

# Write to the stdin to redraw ui
send_to_ui("M", _("Starting up..."))

# Save the time needed to start the script
timings["in"] = time.time() - timings["st"]

# Load face detection/recognition models, takes some time
timings["ll"] = time.time()

# Start threading and wait for init to finish
lock = threading.Lock()
lock.acquire()
threading.Thread(target=init_detector, args=(lock,), daemon=True).start()

# Start video capture on the IR camera
timings["ic"] = time.time()

video_capture = VideoCapture(config)

# Read exposure from config to use in the main loop
exposure = config.getint("video", "exposure", fallback=-1)

# Note the time it took to open the camera
timings["ic"] = time.time() - timings["ic"]

# wait for thread to finish
lock.acquire()
lock.release()
del lock

# Fetch the max frame height
max_height = config.getfloat("video", "max_height", fallback=320.0)

# Get the height of the image (which would be the width if screen is portrait oriented)
height = video_capture.internal.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1
if rotate == 2:
	height = video_capture.internal.get(cv2.CAP_PROP_FRAME_WIDTH) or 1
# Calculate the amount the image has to shrink
scaling_factor = (max_height / height) or 1

# Fetch config settings out of the loop
timeout = config.getint("video", "timeout", fallback=4)
dark_threshold = config.getfloat("video", "dark_threshold", fallback=60)
end_report = config.getboolean("debug", "end_report", fallback=False)

# Initiate histogram equalization
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

# Let the ui know that we're ready
send_to_ui("M", _("Identifying you..."))

# Start the read loop
frames = 0
valid_frames = 0
timings["fr"] = time.time()
dark_running_total = 0

while True:
	# Increment the frame count every loop
	frames += 1

	# Form a string to let the user know we're real busy
	ui_subtext = "Scanned " + str(valid_frames - dark_tries) + " frames"
	if (dark_tries > 1):
		ui_subtext += " (skipped " + str(dark_tries) + " dark frames)"
	# Show it in the ui as subtext
	send_to_ui("S", ui_subtext)

	# Stop if we've exceeded the time limit
	if time.time() - timings["fr"] > timeout:
		# Create a timeout snapshot if enabled
		if save_failed:
			make_snapshot(_("FAILED"))

		if dark_tries == valid_frames:
			print(_("All frames were too dark, please check dark_threshold in config"))
			print(_("Average darkness: {avg}, Threshold: {threshold}").format(avg=str(dark_running_total / max(1, valid_frames)), threshold=str(dark_threshold)))
			exit(13)
		else:
			exit(11)

	# Grab a single frame of video
	frame, gsframe = video_capture.read_frame()
	gsframe = clahe.apply(gsframe)

	# If snapshots have been turned on
	if save_failed or save_successful:
		# Start capturing frames for the snapshot
		if len(snapframes) < 3:
			snapframes.append(frame)

	# Create a histogram of the image with 8 values
	hist = cv2.calcHist([gsframe], [0], None, [8], [0, 256])
	# All values combined for percentage calculation
	hist_total = np.sum(hist)

	# Calculate frame darkness
	darkness = (hist[0] / hist_total * 100)

	# If the image is fully black due to a bad camera read,
	# skip to the next frame
	if (hist_total == 0) or (darkness == 100):
		black_tries += 1
		continue

	dark_running_total += darkness
	valid_frames += 1

	# If the image exceeds darkness threshold due to subject distance,
	# skip to the next frame
	if (darkness > dark_threshold):
		dark_tries += 1
		continue

	# If the height is too high
	if scaling_factor != 1:
		# Apply that factor to the frame
		frame = cv2.resize(frame, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_AREA)
		gsframe = cv2.resize(gsframe, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_AREA)

	# If camera is configured to rotate = 1, check portrait in addition to landscape
	if rotate == 1:
		if frames % 3 == 1:
			frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
			gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_COUNTERCLOCKWISE)
		if frames % 3 == 2:
			frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
			gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_CLOCKWISE)

	# If camera is configured to rotate = 2, check portrait orientation
	elif rotate == 2:
		if frames % 2 == 0:
			frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
			gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_COUNTERCLOCKWISE)
		else:
			frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
			gsframe = cv2.rotate(gsframe, cv2.ROTATE_90_CLOCKWISE)

	# Set the detector input size to match the current frame
	h, w = frame.shape[:2]
	face_detector.setInputSize((w, h))

	# Detect faces in the frame (YuNet expects BGR input)
	retval, faces = face_detector.detect(frame)

	# Skip if no faces detected
	if faces is None:
		continue

	# Loop through each detected face
	for face in faces:
		# Align and crop the face for recognition
		aligned_face = face_recognizer.alignCrop(frame, face)
		# Get the face embedding
		face_encoding = face_recognizer.feature(aligned_face)

		# Compare against each stored encoding using cosine similarity
		for enc_idx, stored_encoding in enumerate(encodings):
			similarity = face_recognizer.match(
				face_encoding, stored_encoding.reshape(1, -1),
				cv2.FaceRecognizerSF_FR_COSINE
			)

			# Update best similarity if this is higher
			if similarity > best_similarity:
				best_similarity = similarity

			# Check if similarity exceeds our threshold
			if similarity >= video_certainty:
				timings["tt"] = time.time() - timings["st"]
				timings["fl"] = time.time() - timings["fr"]

				# Determine which model this encoding belongs to
				match_index = 0
				enc_count = 0
				for mi, model in enumerate(models):
					enc_count += len(model["data"])
					if enc_idx < enc_count:
						match_index = mi
						break

				# If set to true in the config, print debug text
				if end_report:
					def print_timing(label, k):
						"""Helper function to print a timing from the list"""
						print(f"  {label}: {round(timings[k] * 1000)}ms")

					# Print a nice timing report
					print(_("Time spent"))
					print_timing(_("Starting up"), "in")
					print(_("  Open cam + load models: {}ms").format(round(max(timings["ll"], timings["ic"]) * 1000)))
					print_timing(_("  Opening the camera"), "ic")
					print_timing(_("  Loading recognition models"), "ll")
					print_timing(_("Searching for known face"), "fl")
					print_timing(_("Total time"), "tt")

					print(_("\nResolution"))
					width = video_capture.fw or 1
					print(_("  Native: {}x{}").format(height, width))
					# Save the new size for diagnostics
					scale_height, scale_width = frame.shape[:2]
					print(_("  Used: {}x{}").format(scale_height, scale_width))

					# Show the total number of frames and calculate the FPS by dividing it by the total scan time
					print(_("Frames searched: {} ({:.2f} fps)").format(frames, frames / timings["fl"]))
					print(_("Black frames ignored: {} ").format(black_tries))
					print(_("Dark frames ignored: {} ").format(dark_tries))
					print(_("Similarity of winning frame: {:.3f}").format(similarity))

					print(_("Winning model: {} (\"{}\")").format(match_index, models[match_index]["label"]))

				# Make snapshot if enabled
				if save_successful:
					make_snapshot(_("SUCCESSFUL"))

				# Run rubberstamps if enabled
				if config.getboolean("rubberstamps", "enabled", fallback=False):
					import rubberstamps

					send_to_ui("S", "")

					if "gtk_proc" not in vars():
						gtk_proc = None

					rubberstamps.execute(config, gtk_proc, {
						"video_capture": video_capture,
						"face_detector": face_detector,
						"clahe": clahe
					})

				# End peacefully
				exit(0)

	if exposure != -1:
		# For a strange reason on some cameras (e.g. Lenoxo X1E) setting manual exposure works only after a couple frames
		# are captured and even after a delay it does not always work. Setting exposure at every frame is reliable though.
		video_capture.internal.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0)  # 1 = Manual
		video_capture.internal.set(cv2.CAP_PROP_EXPOSURE, float(exposure))
