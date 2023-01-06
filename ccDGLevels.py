from ccDGGeom import np, Point, Rectangle, Line, Circle

def maskToString(mask : np.array) -> str:
	"""
	Convert a 2D boolean array into a string using unicode block element characters
	"""
	if mask.shape[0] % 2 != 0:
		mask = np.vstack((mask, np.zeros(mask.shape[1], bool)))

	summer = np.array([1, 2]).reshape(2, 1)
	converter = lambda n : [' ', '\u2580', '\u2584', '\u2588'][n]
	s = ''

	for i in range(0, mask.shape[0], 2):
		row = np.sum(mask.astype(int)[i:i + 2] * summer, axis = 0)
		s += ''.join(map(converter, row)) + '\n'

	return s

class Catacombs:
	"""Nethack style dungeon"""
	def __init__(
		self, w : int, h : int,
		rct : int, raap : float,
		varix : int, variy : int,
		conn : int, doShift : bool,
		padx : int = 0, pady : int = 0,
		thick : int = 1, varih : int = 0
	):
		"""
		Requires a width & height in cells, a room count, an average area per room
		expressed as a percentage (0.0 -> 1.0), absolute deviations in room size
		in the x and y directions, how many connections each room should have
		at minimum, and whether to shift the midpoint of hallways or not.
		
		Optionally, padding widths in the x and y directions,
		a hallway thickness, and an absolute deviation in hallway thickness
		can be specified.
		"""
		self.size = Point(w, h)
		self.roomCount = rct
		self.roomAvgAreaPercent = raap
		self.variance = Point(varix, variy)
		self.padding = Point(padx, pady)
		# Average dimension of each room
		adim = (self.size.npar * np.sqrt(self.roomAvgAreaPercent)).astype(int)
		self.roomAvgDim = Point(adim[1], adim[0])

		self.hallAvgCount = conn
		self.doHallShifting = doShift
		self.hallThickness = thick
		self.varianceHall = varih
		# Store the rooms and halls in these lists, must generate them separately
		self.rooms = []
		self.halls = []
		self.hallCounts = []
	
	def __str__(self) -> str:
		"""String representation"""
		return (
			"A {} wide by {} tall dungeon,\n"
			+ "with {} rooms of about {:02.0f}% average area each,\n"
			+ "or of average dimension {} wide by {} tall,\n"
			+ "with an average of {} hallways out of each room;\n"
			+ "Rooms are padded by at least {} East-West & {} North-South,\n"
			+ "and have a length variance of +/-{} wide and +/- {} tall."
		).format(
			self.size.x, self.size.y,
			self.roomCount, self.roomAvgAreaPercent * 100.,
			self.roomAvgDim.x, self.roomAvgDim.y,
			self.hallAvgCount,
			self.padding.x, self.padding.y,
			self.variance.x, self.variance.y
		)
	
	def __repr__(self) -> str:
		"""Generic representation"""
		return self.__str__()

	def genRooms(self, reset : bool, attemptsOverride : int = 0):
		"""Randomly generate rooms"""
		if not reset:
			return
		# Clear old rooms and halls
		self.rooms = []
		self.halls = []
		self.hallCounts = [0 for i in range(len(self.rooms))]
		# Cap how many times rectangles are generated
		attempts = 0
		if attemptsOverride > 0:
			maxAttempts = attemptsOverride
		else: # $$ n_{rooms} \times \max(x_{pad} * y_{pad}, 1)
			maxAttempts = int( # \times 10^{-\ln(1 - n_{rooms} \times a_{avg})}
				round( # \times e^{1 + n_{rooms} \times a_{avg}} $$
					self.roomCount * max(self.padding.x * self.padding.y, 1) \
					* 10. ** (
						-np.log(1. - self.roomCount * self.roomAvgAreaPercent)
					) * np.e ** (
						1. + self.roomCount * self.roomAvgAreaPercent
					)
				)
			) # Allows for more filled dungeons to have more attempts
		# Try to generate valid rooms
		while len(self.rooms) < self.roomCount:
			attempts += 1
			noise = np.random.randint(
				-self.variance.npar[::-1], self.variance.npar[::-1] + 1, 2
			)
			newSize = Point(*np.maximum(
				self.roomAvgDim.npar[::-1] + noise,
				np.zeros(2, int) + 4
			))
			originSpace = self.size - newSize # Cannot place an origin beyond this point
			newOrigin = Point(*np.random.randint(np.zeros(2, int), originSpace.tupl, 2))
			newRoom = Rectangle(newOrigin.x, newOrigin.y, newSize.x, newSize.y)
			newRoomPadZone = Rectangle(
				max(newOrigin.x - self.padding.x, 0),
				max(newOrigin.y - self.padding.y, 0),
				newSize.x + 2 * self.padding.x,
				newSize.y + 2 * self.padding.y
			) # Use this rectangle to enforce padding
			# Check that there are no overlaps
			nonOverlapping = True
			for r in self.rooms:
				if newRoomPadZone & r:
					nonOverlapping = False
					break
			# Only accept non-overlapping rooms
			if nonOverlapping:
				self.rooms.append(newRoom)
				print(noise, newSize, newOrigin)
				print(newRoom)
				print(newRoomPadZone)
				print()
			# Log if we hit the attempt limit
			if attempts > maxAttempts:
				if len(self.rooms) < self.roomCount:
					print("Warning: maximum room generation attempts reached.")
					print("Your dungeon will only have", len(self.rooms), "rooms")
				break

		print("Attemped room generations", attempts, "times.")

	def genHalls(self, reset : bool):
		"""Randomly generate hallways"""
		if not reset:
			return
		# Erase old hallways	
		self.halls = []
		self.hallCounts = [0 for i in range(len(self.rooms))]
		# Proceed from room to room
		for i in range(len(self.rooms)):
			room = self.rooms[i]
			# Get taxicab distances from current room centroid to every other rooms centroid
			distances = [
				[j, room.getCentroid() | self.rooms[j].getCentroid()]
				for j in range(len(self.rooms))
			]
			distances[i][1] = 2 * max([t[1] for t in distances]) # Eliminate own distance
			distances = sorted(distances, key = lambda t : t[1])[:len(distances) - 1]
			#print(distances)

			k = 0 # Main loop
			while self.hallCounts[i] < self.hallAvgCount:
				j = distances[k][0] # Index of next nearest other room
				mhDist = distances[k][1]
				other = self.rooms[j]
				# Tuple unpacking
				wallOrient, wallCells = room.getNearestWall(other)
				wallOtherOrient, wallOtherCells = other.getNearestWall(room)

				#print(i, j, k, room.getAzimuth(other), wallOrient, len(wallCells))
				# Decide the doorways' locations
				startRoom = list(wallCells)[
					np.random.randint(0, len(wallCells))
				]
				startOther = list(wallOtherCells)[
					np.random.randint(0, len(wallOtherCells))
				]
				# Get the distance delta along both axes
				delta = startRoom - startOther
				dx = abs(delta.x)
				dy = abs(delta.y)

				#print(startRoom, startOther, dx, dy)
				# Orientation booleans
				goingVertical = wallOrient in ('n', 's')
				goingVerticalOther = wallOtherOrient in ('n', 's')
				# Produce an S-hall or an L-hall
				if goingVertical and goingVerticalOther \
					or not goingVertical and not goingVerticalOther:
					# Randomly shift the meeting point of the hallways
					if self.doHallShifting:
						shiftRange = self.padding.x // 2 if not goingVertical \
						else self.padding.y // 2
						shiftRange -= self.hallThickness // 2
						shiftRange = max(0, shiftRange)
						shift = np.random.randint(-shiftRange, shiftRange + 1)
						#print(shiftRange, shift)
					else:
						shift = 0
					# Compute the initial hallway segments
					roomHall = Line(
						startRoom.x, startRoom.y,
						dx // 2 + 1 + dx % 2 + shift if not goingVertical
						else dy // 2 + 1 + dy % 2 + shift,
						wallOrient
					)
					otherHall = Line(
						startOther.x, startOther.y,
						dx // 2 + 1 - shift if not goingVerticalOther
						else dy // 2 + 1 - shift,
						wallOtherOrient
					)
					# Determine the orientation of the connecting hallway segment
					# (It comes out from the segment attached to the starting room)
					connectingOrientation = roomHall.getNearestOrientation(
						otherHall, mode = 'e'
					)[0]
					connectingHall = Line(
						roomHall.getEndpoint().x, roomHall.getEndpoint().y,
						dx + 1 if goingVertical else dy + 1,
						connectingOrientation
					)
					# The other segments will be added at the bottom of the loop
					self.halls.append(connectingHall)
					# Initialize the offset for padding the thickness of this hallway
					offset = 1
					offsetCorrect = -1 if (
						goingVertical and startRoom.x < startOther.x
						or not goingVertical and startRoom.y < startOther.y
					) else 1 # Make sure the staricase formation of the padded halls
					# faces the right way;

					# Make sure the padding lines don't intersect the wall
					# (Keep doorways to 1 cell wide)
					offsetWall = -1 if (
						wallOrient == 'n' or wallOrient == 'w'
					) else 1
					offsetWallOther = -1 if (
						wallOtherOrient == 'n' or wallOtherOrient == 'w'
					) else 1
					# Randomly vary the amount of padding lines
					hallNoise = np.random.randint(-self.varianceHall, self.varianceHall + 1)
					# Generate the padding lines
					for t in range(self.hallThickness - 1 + hallNoise):
						offsetEnd = offset * offsetCorrect
						#print(offset, offsetEnd, offsetCorrect)
						
						thickRoomHall = Line(
							startRoom.x + (
								offset if goingVertical else offsetWall
							),
							startRoom.y + (
								offset if not goingVertical else offsetWall
							),
							dx // 2 + dx % 2 + shift + offsetEnd
							if not goingVertical
							else dy // 2 + dy % 2 + shift + offsetEnd,
							wallOrient
						)

						thickOtherHall = Line(
							startOther.x + (
								offset if goingVerticalOther else offsetWallOther
							),
							startOther.y + (
								offset if not goingVerticalOther else offsetWallOther
							),
							dx // 2 - shift - offsetEnd
							if not goingVerticalOther
							else dy // 2 - shift - offsetEnd,
							wallOtherOrient
						)

						thickConnectingHall = Line(
							thickRoomHall.getEndpoint().x, thickRoomHall.getEndpoint().y,
							dx + 1 if goingVertical else dy + 1,
							connectingOrientation
						)

						self.halls.append(thickConnectingHall)
						self.halls.append(thickRoomHall)
						self.halls.append(thickOtherHall)
						# Sequence: 1, -1, 2, -2, 3, -3, ...
						offset *= -1
						if offset > 0:
							offset += 1

				else: # Parallel above, Perpendicular below
					#print("L-TYPE HALL GENERATED!!!")
					roomHall = Line(
						startRoom.x, startRoom.y,
						dx + 1 if not goingVertical else dy + 1,
						wallOrient
					)
					#print(roomHall.getEndpoint())
					
					otherHall = Line(
						startOther.x, startOther.y,
						dx + 1 if not goingVerticalOther else dy + 1,
						wallOtherOrient
					)

					offset = 1
					# Make sure when we use the offset for position that
					# subtracting from other keeps us on the same side
					offsetCorrectPos = -1 if (
						wallOrient == 'n' and wallOtherOrient == 'w'
						or wallOrient == 'w' and wallOtherOrient == 'n'
						or wallOrient == 's' and wallOtherOrient == 'e'
						or wallOrient == 'e' and wallOtherOrient == 's'
					) else 1
					# Make sure when we use the offset for length that
					# our assumption that more positive lines are
					# inside the turn holds mathematically
					offsetCorrectLen = -1 if (
						wallOrient == 'n' and wallOtherOrient == 'e'
						or wallOrient == 'w' and wallOtherOrient == 's'
						or wallOrient == 's' and wallOtherOrient == 'e'
						or wallOrient == 'e' and wallOtherOrient == 's'
					) else 1
					# Make sure the padding lines don't intersect the wall
					offsetWall = -1 if (
						wallOrient == 'n' or wallOrient == 'w'
					) else 1
					offsetWallOther = -1 if (
						wallOtherOrient == 's' or wallOtherOrient == 'e'
					) else 1
					# Randomly vary the amount of padding lines
					hallNoise = np.random.randint(-self.varianceHall, self.varianceHall + 1)
					# Generate the padding lines
					for t in range(self.hallThickness - 1 + hallNoise):
						offsetPos = offset * offsetCorrectPos
						offsetLen = offset * offsetCorrectLen

						thickRoomWall = Line(
							startRoom.x + (
								offset if goingVertical else offsetWall
							),
							startRoom.y + (
								offset if not goingVertical else offsetWall
							),
							dx - offsetLen if not goingVertical
							else dy - offsetLen,
							wallOrient
						)

						thickOtherWall = Line(
							startOther.x - (
								offsetPos if goingVerticalOther
								else offsetWallOther
							),
							startOther.y - (
								offsetPos if not goingVerticalOther
								else offsetWallOther
							),
							dx - offsetLen if not goingVerticalOther
							else dy - offsetLen,
							wallOtherOrient
						)

						self.halls.append(thickRoomWall)
						self.halls.append(thickOtherWall)
						# See above sequence comment
						offset *= -1
						if offset > 0:
							offset += 1

				self.halls.append(roomHall)
				self.halls.append(otherHall)
				# Update our bookkeeping then advance to the next closest room
				# (or wrap around to the first closest)
				self.hallCounts[i] += 1
				self.hallCounts[j] += 1
				k += 1
				k %= len(distances)
	
	def draw(self, mode : str = '') -> np.array:
		"""
		Produce a 2D boolean numpy array mask of the dungeon.
		Modes are as follows:

		(Note: mode strings can be mix of capitalization:
			ex. "doors" or "Doors" or "DOORS"
		)

		* default (""): draw the walls of rooms and hallways
		* "hallonly"  : draw only the hallways
		* "nowalls"   : draw the floors of rooms and hallways
		* "doors"     : draw the floors of rooms and their doorways
		* "dooronly"  : draw only the doorways
		* "image"     : draw all layers needed for imaging (returns a 3D array)

		The layer order for image mode is as follows:
		0. Floor, Rooms
		1. Floor, Hallways
		2. Walls
		3. Doors
		4. Everything
		"""
		maskRoomEdge = np.zeros(self.size.npar, bool)
		for r in self.rooms:
			maskRoomEdge |= r.getMaskEdge(self.size.x, self.size.y)

		maskRoomFill = np.zeros(self.size.npar, bool)
		for r in self.rooms:
			maskRoomFill |= r.getMaskFill(self.size.x, self.size.y)

		maskHall = np.zeros(self.size.npar, bool)
		for h in self.halls:
			maskHall |= h.getMask(self.size.x, self.size.y)

		if mode.upper() == "HALLONLY":
			return maskHall
		elif mode.upper() == "NOWALLS":
			return maskHall | (
				maskRoomFill & ~ maskRoomEdge
			)
		elif mode.upper() == "DOORS" or mode.upper() == "LIZARDKING":
			return (
				maskHall & maskRoomEdge
			) | (
				maskRoomFill & ~ maskRoomEdge
			)
		elif mode.upper() == "DOORONLY":
			return maskHall & maskRoomEdge
		elif mode.upper() == "IMAGE":
			return np.stack([
				maskRoomFill & ~maskRoomEdge,
				maskHall,
				maskRoomEdge,
				maskRoomEdge & maskHall,
				maskRoomFill | maskHall
			])
			
		return maskRoomEdge | maskHall & ~ (
			maskRoomFill & maskHall & ~ (
				maskRoomEdge & maskHall
			)
		)
	def getImageData(self) -> dict:
		"""Separate image layer masks out into values in a dictionary"""
		layers = self.draw("IMAGE")
		return {
			"floor" : layers[0],
			"hall" : layers[1],
			"wall" : layers[2],
			"door" : layers[3],
			"all" : layers[4],
			"dungeonType": "catacombs"
		}
		
class Caves:
	"""Circle-based caves and tunnels"""
	def __init__(
		self, w : int, h : int,
		rct : int, raap : float,
		carvep : float, carven : int,
		carveq : float, carver : int,
		vari : int, conn : int,
		pad : int = 0, thick : int = 1,
		varihr : int = 0, variha : float = 0.
	):
		"""
		Requires a width and height in cells, a room count, an average area per room
		expressed as a percentage (0.0 -> 1.0), the probability that a carve
		is positive (adds area to its room), the number of times to carve each room,
		the divisor of the room radius used to compute the carve radius,
		the absolute deviation of the carve radius, the absolute deviation of the
		room radius, and how many connections each room should have at minimum.
		
		Optionally, a radial padding radius, a hallway radius, the absolute deviation
		of the hallway radius, and the absolute deviation of the hallway angle
		can be specified.
		"""
		self.size = Point(w, h)
		self.roomCount = rct
		self.roomAvgAreaPercent = raap

		self.carveChance = carvep
		self.carveCount = carven
		self.carveQuotient = carveq
		self.carveNoise = carver
		
		self.variance = vari
		self.padding = pad

		self.roomAvgRad = np.sqrt(w * h * raap / np.pi).round().astype(int)
		self.carveSize = max(1, int(round(self.roomAvgRad / self.carveQuotient)))

		self.hallAvgCount = conn
		self.hallRadius = thick
		self.varianceHallRadius = varihr
		self.varianceHallAngle = variha

		self.rooms = []
		self.carves = []
		self.carvePolarities = []
		self.halls = []
		self.hallCounts = []

	def __str__(self) -> str:
		"""String representation"""
		return (
			"A {} wide by {} tall cave network,\n"
			+ "with {} chambers of about {:02.0f}% average area each,\n"
			+ "or of average radius {}, with an average of {} tunnels\n"
			+ "out of each chamber; Each chamber is carved {} times\n"
			+ "with a {:02.0f}% chance of filling in,\n"
			+ "with circles of average radius {} +/- {};\n"
			+ "Rooms are padded by at least {} radial cells,\n"
			+ "and have a radius variance of +/- {}."
		).format(
			self.size.x, self.size.y,
			self.roomCount, self.roomAvgAreaPercent * 100.,
			self.roomAvgRad, self.hallAvgCount,
			self.carveCount, self.carveChance * 100.,
			self.carveSize, self.carveNoise,
			self.padding, self.variance
		)
	
	def __repr__(self) -> str:
		"""Generic representation"""
		return self.__str__()

	def genCarves(self, reset : bool, attemptsOverride : int = 0):
		"""Randomly carve rooms"""
		if not reset:
			return

		self.carves = []
		self.carvePolarities = []
		
		# Cap how many times circles are generated
		if attemptsOverride > 0:
			maxAttempts = attemptsOverride
		else:
			carveRatio = (
				(2. * self.carveSize) # Diameter of Carve
				/ (2. * np.pi * self.roomAvgRad) # Circumference of Room
			)			
			
			maxAttempts = int(
				round(
					self.carveCount
					* 10. ** (-np.log(0.5 - carveRatio))
					* np.e ** (1. + carveRatio)
				)
			) # Allows for larger carves to have more chances
			print("Carve Ratio:", carveRatio)

		for r in self.rooms:
			carveGroup = []
			polarityGroup = []
			carveMasks = []
			attempts = 0
			for c in range(self.carveCount):
				while True: # Try to find a good origin and radius for the new carve
					if attempts >= maxAttempts:
						break

					carveOrigin = r.getAngledEdgeCell(
						np.random.uniform() * 360.
					)
					carveRadius = self.carveSize + np.random.randint(
						-self.carveNoise, self.carveNoise + 1
					)

					if np.any( # Check that the carve will be in the frame
						(
							carveOrigin.npar - np.array((carveRadius, carveRadius))
						) < np.zeros(2, int)
					) or np.any(
						(
							carveOrigin.npar + np.array((carveRadius, carveRadius))
						) >= self.size.npar
					):
						attempts += 1
						continue

					newCarve = Circle(carveOrigin.x, carveOrigin.y, carveRadius)
					newCarveMask = newCarve.getMaskFill(self.size.x, self.size.y)
					overlapping = False

					for m in carveMasks: # Check that the carve doesn't instersect
						if np.any(newCarveMask & m): # any other carves
							overlapping = True
							break

					attempts += 1

					if overlapping:
						continue # Enforce no carves overlap each other
					else:
						break
				
				if attempts < maxAttempts:
					carvePolarity = np.random.uniform() < self.carveChance

					carveGroup.append(newCarve)
					polarityGroup.append(carvePolarity)
					carveMasks.append(newCarveMask)
				else:
					break

			self.carves.append(carveGroup)
			self.carvePolarities.append(polarityGroup)
			print("Generated", len(carveGroup), "carves with", attempts, "attempts for room", r)

	def genRooms(self, reset : bool, attemptsOverride : int = 0):
		"""Randomly generate rooms"""
		if not reset:
			return
		# Clear old rooms and halls
		self.rooms = []
		self.carves = []
		self.carvePolarities = []
		self.halls = []
		self.hallCounts = [0 for i in range(len(self.rooms))]

		roomMasks = []
		# Cap how many times circles are generated
		attempts = 0
		if attemptsOverride > 0:
			maxAttempts = attemptsOverride
		else: # $$ n_{rooms} \times \max(pad, 1)
			maxAttempts = int( # \times 10^{-\ln(1 - n_{rooms} \times a_{avg})}
				round( # \times e^{1 + n_{rooms} \times a_{avg}} $$
					self.roomCount * max(self.padding, 1)
					* 10. ** (
						-np.log(1. - self.roomCount * self.roomAvgAreaPercent)
					) * np.e ** (
						1. + self.roomCount * self.roomAvgAreaPercent
					)
				)
			) # Allows for more filled dungeons to have more attempts
		# Try to generate valid rooms
		while len(self.rooms) < self.roomCount:
			attempts += 1
			noise = np.random.randint(-self.variance, self.variance + 1)
			newRadius = self.roomAvgRad + noise

			originSpace = Point(self.size.x - newRadius, self.size.y - newRadius)
			newOrigin = Point(
				*np.random.randint((newRadius, newRadius), originSpace.tupl, 2)
			)

			newRoom = Circle(newOrigin.x, newOrigin.y, newRadius)
			newRoomPadZone = Circle(
				newOrigin.x, newOrigin.y,
				newRadius + self.padding
			).getMaskFill(self.size.x + self.padding, self.size.y + self.padding)

			nonOverlapping = True
			for m in roomMasks:
				if np.any(newRoomPadZone & m):
					nonOverlapping = False
					break

			if nonOverlapping:
				self.rooms.append(newRoom)
				roomMasks.append(
					newRoom.getMaskFill(
						self.size.x + self.padding, self.size.y + self.padding
					)
				)

				print(noise, newRadius, newOrigin)
				print(newRoom)
				print()

			if attempts > maxAttempts:
				if len(self.rooms) < self.roomCount:
					print("Warning: maximum room generation attempts reached.")
					print("Your dungeon will only have", len(self.rooms), "rooms")
					break

		print("Attemped room generation", attempts, "times.")
		#print("Now carving out each room...")
		#self.genCarves(True)

	def genHalls(self, reset : bool):
		"""Randomly generate hallways"""
		if not reset:
			return
		# Erase old hallways	
		self.halls = []
		self.hallCounts = [0 for i in range(len(self.rooms))]
		# Proceed from room to room
		for i in range(len(self.rooms)):
			room = self.rooms[i]
			# Get taxicab distances from current room centroid to every other rooms centroid
			distances = [
				[j, room.getCentroid() | self.rooms[j].getCentroid()]
				for j in range(len(self.rooms))
			]
			distances[i][1] = 2 * max([t[1] for t in distances]) # Eliminate own distance
			distances = sorted(distances, key = lambda t : t[1])[:len(distances) - 1]

			# Produce a collision mask of the current room
			maskRoom = room.getMaskFill(*self.size.tupl)
			maskRoomCarvePos = np.zeros(self.size.npar, bool)
			maskRoomFloorNeg = np.zeros(self.size.npar, bool)

			for j in range(len(self.carves[i])):
				if self.carvePolarities[i][j]:
					maskRoomCarvePos |= self.carves[i][j].getMaskFill(*self.size.tupl)
				else:
					maskRoomFloorNeg |= (
						self.carves[i][j].getMaskFill(*self.size.tupl)
						& ~self.carves[i][j].getMaskEdge(*self.size.tupl)
					)

			maskRoom |= maskRoomCarvePos
			maskRoom &= ~maskRoomFloorNeg

			print("Digging tunnels to room", room)

			k = 0 # Main loop
			while self.hallCounts[i] < self.hallAvgCount:
				j = distances[k][0] # Index of next nearest other room
				mhDist = distances[k][1]
				other = self.rooms[j]
				# Decide the doorways' location
				heading = other.getAzimuth(room)
				next = other.getAngledEdgeCell(heading)

				while True: # Add on enough tunnel cells
					firstRadius = True

					while firstRadius or np.any( # Check that the tunnel 
						( # will be in the frame
							next.npar - np.array((nextRadius, nextRadius))
						) < np.zeros(2, int)
					) or np.any(
						(
							next.npar + np.array((nextRadius, nextRadius))
						) >= self.size.npar
					):
						nextRadius = self.hallRadius + np.random.randint(
							-self.varianceHallRadius, self.varianceHallRadius + 1
						) # Recompute the radius
						firstRadius = False

					nextTunnel = Circle(next.x, next.y, nextRadius)
					self.halls.append(nextTunnel)

					if np.any(
						nextTunnel.getMaskFill(*self.size.tupl) & maskRoom
					): # Stop digging if we have hit the target room
						break
					else:
						next = nextTunnel.getAngledEdgeCell(
							nextTunnel.getAzimuth(room) + np.random.uniform(
								-self.varianceHallAngle, self.varianceHallAngle
							)
						)

				print("Generated a hall from", other)

				self.hallCounts[i] += 1
				self.hallCounts[j] += 1
				k += 1
				k %= len(distances)

	def draw(self, mode : str = ""):
		"""
		Produce a 2D boolean numpy array mask of the dungeon.
		Modes are as follows:

		(Note: mode strings can be mix of capitalization:
			ex. "doors" or "Doors" or "DOORS"
		)

		* default (""): draw the walls of rooms and hallways
		* "hallonly"  : draw only the walls of hallways
		* "nowalls"   : draw the floors of rooms and hallways
		* "nonsolid   : draw all wall and floor cells of rooms and hallways
		* "layers"    : draw all layers and return them in a stack
		* "image"     : draw all layers needed for imaging (returns a 3D array)

		The layer order for image mode is as follows:
		0. Floor, Rooms
		1. Floor, Hallways
		2. Walls
		3. Doors
		4. Everything
		"""
		maskRoom = np.zeros(self.size.npar, bool)
		maskRoomCarvePos = np.zeros(self.size.npar, bool)
		maskRoomCarveNeg = np.zeros(self.size.npar, bool)
		maskRoomEdgePos = np.zeros(self.size.npar, bool)
		maskRoomEdgeNeg = np.zeros(self.size.npar, bool)
		maskRoomFloorPos = np.zeros(self.size.npar, bool)
		maskRoomFloorNeg = np.zeros(self.size.npar, bool)

		maskHall = np.zeros(self.size.npar, bool)
		maskHallEdge = np.zeros(self.size.npar, bool)
		maskHallFloor = np.zeros(self.size.npar, bool)
		# Combine all the edge and fill masks of the rooms
		for r in self.rooms:
			edgeMask = r.getMaskEdge(*self.size.tupl)
			fillMask = r.getMaskFill(*self.size.tupl)

			maskRoom |= fillMask
			maskRoomEdgePos |= edgeMask
			maskRoomFloorPos |= fillMask & ~edgeMask # Floor is Fill - Edge
			# And Boolean - is A & ~B
		# Combine all the edge and fill masks of the carves, keeping polarity
		for i in range(len(self.carves)):
			carveGroup = self.carves[i]
			polarityGroup = self.carvePolarities[i]
			for j in range(len(carveGroup)):
				edgeMask = carveGroup[j].getMaskEdge(*self.size.tupl)
				fillMask = carveGroup[j].getMaskFill(*self.size.tupl)

				if polarityGroup[j]:
					maskRoomCarvePos |= fillMask
					maskRoomEdgePos |= edgeMask
					maskRoomFloorPos |= fillMask & ~edgeMask
				else:
					maskRoomCarveNeg |= fillMask
					maskRoomEdgeNeg |= edgeMask
					maskRoomFloorNeg |= fillMask & ~edgeMask
		# Combine all the edge and fill masks of the tunnels
		for h in self.halls:
			edgeMask = h.getMaskEdge(*self.size.tupl)
			fillMask = h.getMaskFill(*self.size.tupl)

			maskHall |= fillMask
			maskHallEdge |= edgeMask
			maskHallFloor |= fillMask & ~edgeMask

		if mode.upper() == "NOWALLS": # Remove all negative carve space from floors,
			# then tack on the hall floors
			return (maskRoomFloorPos & ~maskRoomCarveNeg) | maskHallFloor
		elif mode.upper() == "NONSOLID": # Combine all fill masks with polarity
			return ((maskRoom | maskRoomCarvePos) & ~maskRoomFloorNeg) | maskHall
		elif mode.upper() == "HALLONLY": # This removes overlapping internal edges
			return maskHallEdge & ~maskHallFloor
		elif mode.upper() == "LAYERS":
			return np.array((
				maskRoom,
				maskRoomCarvePos, maskRoomCarveNeg,
				maskRoomEdgePos, maskRoomEdgeNeg,
				maskRoomFloorPos, maskRoomFloorNeg,
				maskHall, maskHallEdge, maskHallFloor
			))
		elif mode.upper() == "IMAGE":
			return (
				maskHallFloor,
				maskRoomFloorPos & ~maskRoomCarveNeg,
				maskRoomFloorPos & maskRoomCarvePos & ~maskRoom,
				( # Part 2 of standard draw
					maskHallEdge & ~maskHallFloor
				) & ~(
					(maskRoom | maskRoomCarvePos) & ~maskRoomFloorNeg
				),
				( # Part 1 of standard draw
					(
						(maskRoomEdgePos & ~maskRoomFloorPos) & ~maskRoomCarveNeg
					) | (
						maskRoomEdgeNeg & maskRoom
					) & ~maskHallFloor
				),
				((maskRoom | maskRoomCarvePos) & ~maskRoomFloorNeg) | maskHall
			)

		return (
			(
				( # Remove and edge cells that are carved floors
					(maskRoomEdgePos & ~maskRoomFloorPos) & ~maskRoomCarveNeg
					# Remove negative carve space
				) | ( # Combine with negative edges that are inside each room
					maskRoomEdgeNeg & maskRoom
				) # Cut out edges where tunnels will connect
			) & ~maskHallFloor
		) | ( # Remove overlapping internal hall edges
			(
				maskHallEdge & ~maskHallFloor # And remove edges inside rooms
			) & ~(
				(maskRoom | maskRoomCarvePos) & ~maskRoomFloorNeg
			)
		)

	def getImageData(self) -> dict:
		"""Separate image layer masks out into values in a dictionary"""
		layers = self.draw("IMAGE")
		return {
			"floorHall": layers[0],
			"floorRoom": layers[1],
			"floorCarve": layers[2],
			"wallHall": layers[3],
			"wallRoom": layers[4],
			"all": layers[5],
			"dungeonType": "caves"
		}

class City:
	"""Grid-planned cities and towns"""
	def __init__(
		self, w : int, h : int, streetv : int, streeth : int,
		streetw : int, varis : int,
		buildingc : int, buildingp : float, baap : float,
		plazap : float, plazabp : float, 
		plazax : int, plazay : int,
		varibx : int = 0, variby : int = 0,
		padbx : int = 0, padby : int = 0
	):
		"""
		Requires a width & height in cells, a count of vertical and horizontal streets,
		a street width, the absolute deviation of the street width,
		a count of buildings per lot, the probability for a lot to have buildings,
		the average area of each building expressed as a percentage (0.0 -> 1.0),
		the probability for a plaza to generate instead of a lot,
		the probability for buildings to generate in a plaza,
		and how many lots a plaza will take up in width and height.

		Optionally, the absolute deviation of the width and height of, as well as
		the padding space around, each building in a lot or plaza, can be specified.
		"""
		self.size = Point(w, h)
		self.streetCount = Point(streetv, streeth)
		self.streetWidth = streetw
		self.varianceStreet = varis
		self.streetMaxWidth = self.streetWidth + self.varianceStreet

		self.buildingCount = buildingc
		self.buildingChance = buildingp
		self.buildingPadding = Point(padbx, padby)

		self.lotSize = (
			self.size - (
				self.streetCount * (self.streetWidth + self.varianceStreet)
			)
		) // (self.streetCount.npar - 1)
		self.buildingAverageAreaPercent = baap
		self.buildingSize = Point(
			*(
				(
					(
						self.lotSize.npar - self.buildingPadding.npar
					) * np.sqrt(self.buildingAverageAreaPercent)
				).astype(int)[::-1]
			)
		)
		self.varianceBuilding = Point(varibx, variby)

		self.plazaChance = plazap
		self.plazaBuildingChance = plazabp
		self.plazaSize = Point(plazax, plazay)

		self.streets = []
		self.lots = []
		self.plazas = []
		self.buildings = []

	def __str__(self) -> str:
		"""String representation"""
		return (
			"A {} wide by {} tall city,\n"
			+ "with {} North-South streets and {} East-West streets\n"
			+ "which are each {} +/- {} cells wide;\n"
			+ "The streets contain lots that are {} wide by {} tall,\n"
			+ "which {:02.0f}% of the time contain on average {} buildings,\n"
			+ "which each are on average {} +/- {} wide by {} +/- {} tall,\n"
			+ "and are padded by at least {} East-West and {} North South;\n"
			+ "In the place of lots, there is a {:02.0f}% chance of there being\n"
			+ "a plaza, which take up {} lots wide by {} lots tall worth of the city;\n"
			+ "In each plaza, there is a {:02.0f}% chance for there to be\n"
			+ "{} buildings instead of bare terrain."
		).format(
			self.size.x, self.size.y,
			self.streetCount.x, self.streetCount.y,
			self.streetWidth, self.varianceStreet,
			self.lotSize.x, self.lotSize.y,
			self.buildingChance * 100., self.buildingCount,
			self.buildingSize.x, self.varianceBuilding.x,
			self.buildingSize.y, self.varianceBuilding.y,
			self.buildingPadding.x, self.buildingPadding.y,
			self.plazaChance * 100.,
			self.plazaSize.x, self.plazaSize.y,
			self.plazaBuildingChance * 100.,
			self.buildingCount * np.prod(self.plazaSize.npar)
		)
	
	def __repr__(self) -> str:
		"""Generic representation"""
		return self.__str__()

	def genLayout(self, reset : bool):
		"""Evenly lay out the streets, lots, and plazas"""
		if not reset:
			return

		self.streets = []
		self.lots = []
		self.plazas = []
		self.buildings = []

		middleOfStreet = self.streetMaxWidth // 2 - (1 - (self.streetMaxWidth % 2))

		for xi in range(self.streetCount.x):
			x = xi * (self.streetMaxWidth + self.lotSize.x)
			width = self.streetWidth + np.random.randint(
				-self.varianceStreet, self.varianceStreet + 1
			)

			middle = x + middleOfStreet
			xl = middle
			d = 1
			for i in range(width):
				self.streets.append(Line(xl, 0, self.size.y, 's'))
				xl = middle + d
				d *= -1
				if d > 0:
					d += 1

		for yi in range(self.streetCount.y):
			y = yi * (self.streetMaxWidth + self.lotSize.y)
			width = self.streetWidth + np.random.randint(
				-self.varianceStreet, self.varianceStreet + 1
			)

			middle = y + middleOfStreet
			yl = middle
			d = 1
			for i in range(width):
				self.streets.append(Line(0, yl, self.size.x, 'e'))
				yl = middle + d
				d *= -1
				if d > 0:
					d += 1

		self.plazaLots = np.zeros(self.streetCount.npar - 1, bool)
		deferPlaza = False
		for yi in range(self.streetCount.y - 1):
			for xi in range(self.streetCount.x - 1):
				if self.plazaLots[yi, xi]:
					continue

				origin = (
					Point(xi, yi) * (
						self.lotSize + self.streetMaxWidth
					).npar
				) + self.streetMaxWidth

				isPlaza = np.random.uniform() < self.plazaChance
				cellsOpen = (self.streetCount - 1) - Point(xi, yi)
				
				if cellsOpen.x < self.plazaSize.x or cellsOpen.y < self.plazaSize.y:
					if isPlaza:
						print("Deferring plaza!", xi, yi)
						deferPlaza = True
						isPlaza = False
				elif deferPlaza or isPlaza:
					deferPlaza = False
					isPlaza = True
				
				if isPlaza:
					print("Making a plaza!", xi, yi)

					plazaSize = (
						self.lotSize * self.plazaSize.npar
					) + (
						(self.plazaSize - 1) * self.streetMaxWidth
					)

					self.plazas.append(
						Rectangle(origin.x, origin.y, plazaSize.x, plazaSize.y)
					)

					for yp in range(self.plazaSize.y):
						for xp in range(self.plazaSize.x):
							self.plazaLots[yi + yp, xi + xp] = True

				else:
					self.lots.append(
						Rectangle(origin.x, origin.y, self.lotSize.x, self.lotSize.y)
					)
	def genBuildings(self, reset : bool, attemptsOverride : int = 0):
		"""Docstring"""
		if not reset:
			return

		self.buildings = []
		# Cap how many times rectangles are generated
		if attemptsOverride > 0:
			maxAttempts = attemptsOverride
		else:
			maxAttempts = int(
				round(
					self.buildingCount * max(
						self.buildingPadding.x, self.buildingPadding.y, 1
					) * 10. ** (
						-np.log(
							1. - self.buildingCount * self.buildingAverageAreaPercent
						)
					) * np.e ** (
						1. + self.buildingCount * self.buildingAverageAreaPercent
					)
				)
			)
		# Try to generate valid rooms
		for block in self.lots + self.plazas:
			if block in self.lots:
				build = np.random.uniform() < self.buildingChance
				buildCount = self.buildingCount
				maxAttemptsActual = maxAttempts
			else:
				build = np.random.uniform() < self.plazaBuildingChance
				buildCount = self.buildingCount * np.prod(self.plazaSize.npar)
				maxAttemptsActual = maxAttempts * np.prod(self.plazaSize.npar)

			if not build:
				print("Skipping lot", block.origin)
				continue

			extent = (
				block.origin + Point(block.width, block.height)
			) - (self.buildingSize + self.varianceBuilding)
			print(block.origin, extent, maxAttemptsActual)

			buildingsPlaced = 0
			attempts = 0

			while buildingsPlaced < buildCount:
				attempts += 1
				noise = np.random.randint(
					-self.varianceBuilding.npar[::-1],
					self.varianceBuilding.npar[::-1] + 1,
					2
				)
				newOrigin = Point(
					*(
						np.random.randint(block.origin.npar, extent.npar, 2)[::-1]
					)
				)
				newSize = Point(
					*np.maximum(
						self.buildingSize.npar[::-1] + noise,
						np.zeros(2, int) + 3
					)
				)

				newBuilding = Rectangle(newOrigin.x, newOrigin.y, newSize.x, newSize.y)
				newBuildingPadZone = Rectangle(
					max(newOrigin.x - self.buildingPadding.x, 0),
					max(newOrigin.y - self.buildingPadding.y, 0),
					newSize.x + 2 * self.buildingPadding.x,
					newSize.y + 2 * self.buildingPadding.y,
				)

				nonOverlapping = True
				for b in self.buildings:
					if newBuildingPadZone & b:
						nonOverlapping = False
						break

				if nonOverlapping:
					self.buildings.append(newBuilding)
					buildingsPlaced += 1

				if attempts > maxAttemptsActual:
					if buildingsPlaced < self.buildingCount:
						print("Warning: maximum building generation attempts reached.")
						print("The block at", block.origin, "will only have")
						print(buildingsPlaced, "buildings.")
					break

			print("Attempted building generation", attempts, "times")
			print("on the block at", block.origin)

	def draw(self, mode : str = "") -> np.array:
		"""Docstring"""
		maskStreetV = np.zeros(self.size.npar, bool)
		maskStreetH = np.zeros(self.size.npar, bool)
		maskLotAndPlazaEdge = np.zeros(self.size.npar, bool)
		maskLotAndPlazaFill = np.zeros(self.size.npar, bool)
		maskBuildingEdge = np.zeros(self.size.npar, bool)
		maskBuildingFill = np.zeros(self.size.npar, bool)

		for line in self.streets:
			if line.orient.x != 0:
				maskStreetH |= line.getMask(*self.size.tupl)
			elif line.orient.y != 0:
				maskStreetV |= line.getMask(*self.size.tupl)

		for lot in self.lots:
			maskLotAndPlazaEdge |= lot.getMaskEdge(*self.size.tupl)
			maskLotAndPlazaFill |= lot.getMaskFill(*self.size.tupl)

		for plaza in self.plazas:
			maskLotAndPlazaEdge |= plaza.getMaskEdge(*self.size.tupl)
			maskLotAndPlazaFill |= plaza.getMaskFill(*self.size.tupl)

		for building in self.buildings:
			maskBuildingEdge |= building.getMaskEdge(*self.size.tupl)
			maskBuildingFill |= building.getMaskFill(*self.size.tupl)

		return np.array((
			(
				(maskStreetV | maskStreetH)
				& ~maskLotAndPlazaFill
			) | maskBuildingEdge,
			maskLotAndPlazaFill
		))

