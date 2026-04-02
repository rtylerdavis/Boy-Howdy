import time
import cv2

from i18n import _

# Import the root rubberstamp class
from rubberstamps import RubberStamp


class nod(RubberStamp):
	def declare_config(self):
		"""Set the default values for the optional arguments"""
		self.options["min_distance"] = 6
		self.options["min_directions"] = 2

	def run(self):
		"""Track a users nose to see if they nod yes or no"""
		self.set_ui_text(_("Nod to confirm"), self.UI_TEXT)
		self.set_ui_text(_("Shake your head to abort"), self.UI_SUBTEXT)

		# Stores relative distance between the 2 eyes in the last frame
		# Used to calculate the distance of the nose traveled in relation to face size in the frame
		last_reldist = -1
		# Last point the nose was at
		last_nosepoint = {"x": -1, "y": -1}
		# Contains booleans recording successful nods and their directions
		recorded_nods = {"x": [], "y": []}

		starttime = time.time()

		# Keep running the loop while we have not hit timeout yet
		while time.time() < starttime + self.options["timeout"]:
			# Read a frame from the camera
			ret, frame = self.video_capture.read_frame()

			# Apply CLAHE to get a better picture
			frame = self.clahe.apply(frame)

			# YuNet needs BGR input
			bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

			# Set detector input size to match frame
			h, w = bgr_frame.shape[:2]
			self.face_detector.setInputSize((w, h))

			# Detect all faces in the frame
			retval, faces = self.face_detector.detect(bgr_frame)

			# Only continue if exactly 1 face is visible in the frame
			if faces is None or len(faces) != 1:
				continue

			face = faces[0]

			# YuNet detection output format (15 values per face):
			# [x, y, w, h, right_eye_x, right_eye_y, left_eye_x, left_eye_y,
			#  nose_tip_x, nose_tip_y, right_mouth_x, right_mouth_y,
			#  left_mouth_x, left_mouth_y, score]

			# Get the position of the eyes and tip of the nose
			right_eye_x = face[4]
			left_eye_x = face[6]
			nose_x = face[8]
			nose_y = face[9]

			# Calculate the relative distance between the 2 eyes
			reldist = right_eye_x - left_eye_x
			# Average this out with the distance found in the last frame to smooth it out
			avg_reldist = (last_reldist + reldist) / 2

			# Calculate horizontal movement (shaking head) and vertical movement (nodding)
			for axis in ["x", "y"]:
				# Get the location of the nose on the active axis
				nosepoint = nose_x if axis == "x" else nose_y

				# If this is the first frame set the previous values to the current ones
				if last_nosepoint[axis] == -1:
					last_nosepoint[axis] = nosepoint
					last_reldist = reldist

				mindist = self.options["min_distance"]
				# Get the relative movement by taking the distance traveled and dividing it by eye distance
				movement = (nosepoint - last_nosepoint[axis]) * 100 / max(avg_reldist, 1)

				# If the movement is over the minimal distance threshold
				if movement < -mindist or movement > mindist:
					# If this is the first recorded nod, add it to the array
					if len(recorded_nods[axis]) == 0:
						recorded_nods[axis].append(movement < 0)

					# Otherwise, only add this nod if the previous nod with in the other direction
					elif recorded_nods[axis][-1] != (movement < 0):
						recorded_nods[axis].append(movement < 0)

				# Check if we have nodded enough on this axis
				if len(recorded_nods[axis]) >= self.options["min_directions"]:
					# If nodded yes, show confirmation in ui
					if (axis == "y"):
						self.set_ui_text(_("Confirmed authentication"), self.UI_TEXT)
					# If shaken no, show abort message
					else:
						self.set_ui_text(_("Aborted authentication"), self.UI_TEXT)

					# Remove subtext
					self.set_ui_text("", self.UI_SUBTEXT)

					# Return true for nodding yes and false for shaking no
					time.sleep(0.8)
					return axis == "y"

				# Save the relative distance and the nosepoint for next loop
				last_reldist = reldist
				last_nosepoint[axis] = nosepoint

		# We've fallen out of the loop, so timeout has been hit
		return not self.options["failsafe"]
