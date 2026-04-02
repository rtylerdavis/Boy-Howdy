# Show a window with the video stream and testing information

# Import required modules
import configparser
import builtins
import os
import json
import sys
import time
import cv2
import numpy as np
import paths_factory

from i18n import _
from recorders.video_capture import VideoCapture

# Read config from disk
config = configparser.ConfigParser()
config.read(paths_factory.config_file_path())

if config.get("video", "recording_plugin", fallback="opencv") != "opencv":
	print(_("Howdy has been configured to use a recorder which doesn't support the test command yet, aborting"))
	sys.exit(12)

video_capture = VideoCapture(config)

# Read config values to use in the main loop
video_certainty = config.getfloat("video", "certainty", fallback=0.40)
detection_threshold = config.getfloat("video", "detection_threshold", fallback=0.9)
exposure = config.getint("video", "exposure", fallback=-1)
dark_threshold = config.getfloat("video", "dark_threshold", fallback=60)

# Let the user know what's up
print(_("""
Opening a window with a test feed

Press ctrl+C in this terminal to quit
Click on the image to enable or disable slow mode
"""))


def mouse(event, x, y, flags, param):
	"""Handle mouse events"""
	global slow_mode

	# Toggle slowmode on click
	if event == cv2.EVENT_LBUTTONDOWN:
		slow_mode = not slow_mode


def print_text(line_number, text):
	"""Print the status text by line number"""
	cv2.putText(overlay, text, (10, height - 10 - (10 * line_number)), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 255, 0), 0, cv2.LINE_AA)


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

encodings = []
models = None

try:
	user = builtins.howdy_user
	models = json.load(open(paths_factory.user_model_path(user)))

	for model in models:
		for encoding in model["data"]:
			encodings.append(np.array(encoding, dtype=np.float32))
except FileNotFoundError:
	pass

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

# Open the window and attach a a mouse listener
cv2.namedWindow("Howdy Test")
cv2.setMouseCallback("Howdy Test", mouse)

# Enable a delay in the loop
slow_mode = False
# Count all frames ever
total_frames = 0
# Count all frames per second
sec_frames = 0
# Last secands FPS
fps = 0
# The current second we're counting
sec = int(time.time())
# recognition time
rec_tm = 0

# Wrap everything in an keyboard interrupt handler
try:
	while True:
		frame_tm = time.time()

		# Increment the frames
		total_frames += 1
		sec_frames += 1

		# Id we've entered a new second
		if sec != int(frame_tm):
			# Set the last seconds FPS
			fps = sec_frames

			# Set the new second and reset the counter
			sec = int(frame_tm)
			sec_frames = 0

		# Grab a single frame of video
		orig_frame, frame = video_capture.read_frame()

		frame = clahe.apply(frame)
		# Make a frame to put overlays in
		overlay = frame.copy()
		overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

		# Fetch the frame height and width
		height, width = frame.shape[:2]

		# Create a histogram of the image with 8 values
		hist = cv2.calcHist([frame], [0], None, [8], [0, 256])
		# All values combined for percentage calculation
		hist_total = int(sum(hist)[0])
		# Fill with the overall containing percentage
		hist_perc = []

		# Loop though all values to calculate a percentage and add it to the overlay
		for index, value in enumerate(hist):
			value_perc = float(value[0]) / hist_total * 100
			hist_perc.append(value_perc)

			# Top left point, 10px margins
			p1 = (20 + (10 * index), 10)
			# Bottom right point makes the bar 10px thick, with an height of half the percentage
			p2 = (10 + (10 * index), int(value_perc / 2 + 10))
			# Draw the bar in green
			cv2.rectangle(overlay, p1, p2, (0, 200, 0), thickness=cv2.FILLED)

		# Print the statis in the bottom left
		print_text(0, _("RESOLUTION: {}x{}").format(height, width))
		print_text(1, _("FPS: {}").format(fps))
		print_text(2, _("FRAMES: {}").format(total_frames))
		print_text(3, _("RECOGNITION: {}ms").format(round(rec_tm * 1000)))

		# Show that slow mode is on, if it's on
		if slow_mode:
			cv2.putText(overlay, _("SLOW MODE"), (width - 66, height - 10), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 255), 0, cv2.LINE_AA)

		# Ignore dark frames
		if hist_perc[0] > dark_threshold:
			# Show that this is an ignored frame in the top right
			cv2.putText(overlay, _("DARK FRAME"), (width - 68, 16), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 255), 0, cv2.LINE_AA)
		else:
			# Show that this is an active frame
			cv2.putText(overlay, _("SCAN FRAME"), (width - 68, 16), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 255, 0), 0, cv2.LINE_AA)

			rec_tm = time.time()

			# Set detector input size to match frame
			face_detector.setInputSize((width, height))

			# Detect faces using YuNet (needs BGR input, convert from grayscale)
			bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
			retval, face_locations = face_detector.detect(bgr_frame)
			rec_tm = time.time() - rec_tm

			# Loop though all faces and paint a circle around them
			if face_locations is not None:
				for face in face_locations:
					# By default the circle around the face is red for no match
					color = (0, 0, 230)

					# Get bounding box
					fx, fy, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])

					# Get the center X and Y from the bounding box
					x = fx + fw // 2
					y = fy + fh // 2

					# Get the radius from the width of the bounding box
					r = fw // 2
					# Add 20% padding
					r = int(r + (r * 0.2))

					# If we have models defined for the current user
					if models and encodings:
						# Align and crop face, get encoding
						aligned_face = face_recognizer.alignCrop(orig_frame, face)
						face_encoding = face_recognizer.feature(aligned_face)

						# Match against each stored encoding
						best_match_similarity = 0
						best_match_index = 0
						enc_count = 0
						for enc_idx, stored_enc in enumerate(encodings):
							similarity = face_recognizer.match(
								face_encoding, stored_enc.reshape(1, -1),
								cv2.FaceRecognizerSF_FR_COSINE
							)
							if similarity > best_match_similarity:
								best_match_similarity = similarity
								best_match_index = enc_idx

						# Determine which model this belongs to
						match_model_index = 0
						running_count = 0
						for mi, model in enumerate(models):
							running_count += len(model["data"])
							if best_match_index < running_count:
								match_model_index = mi
								break

						# If a model matches
						if best_match_similarity >= video_certainty:
							# Turn the circle green
							color = (0, 230, 0)

							# Print the name of the model next to the circle
							circle_text = "{} (similarity: {})".format(models[match_model_index]["label"], round(best_match_similarity, 3))
							cv2.putText(overlay, circle_text, (int(x + r / 3), y - r), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 255, 0), 0, cv2.LINE_AA)
						# If no approved matches, show red text
						else:
							cv2.putText(overlay, "no match", (int(x + r / 3), y - r), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 255), 0, cv2.LINE_AA)

					# Draw the Circle in green
					cv2.circle(overlay, (x, y), r, color, 2)

		# Add the overlay to the frame with some transparency
		alpha = 0.65
		frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
		cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

		# Show the image in a window
		cv2.imshow("Howdy Test", frame)

		# Quit on any keypress
		if cv2.waitKey(1) != -1:
			raise KeyboardInterrupt()

		frame_time = time.time() - frame_tm

		# Delay the frame if slowmode is on
		if slow_mode:
			time.sleep(max([.5 - frame_time, 0.0]))

		if exposure != -1:
			# For a strange reason on some cameras (e.g. Lenoxo X1E)
			# setting manual exposure works only after a couple frames
			# are captured and even after a delay it does not
			# always work. Setting exposure at every frame is
			# reliable though.
			video_capture.internal.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0)  # 1 = Manual
			video_capture.internal.set(cv2.CAP_PROP_EXPOSURE, float(exposure))

# On ctrl+C
except KeyboardInterrupt:
	# Let the user know we're stopping
	print(_("\nClosing window"))

	# Release handle to the webcam
	cv2.destroyAllWindows()
