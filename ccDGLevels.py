from ccDGGeom import np, Point, Rectangle, Line, Circle

# Nethack style dungeon
class Catacombs:
	def __init__(
		self, w : int, h : int,
		rct : int, raap : float,
		varix : int, variy : int,
		conn : int, doShift : bool,
		padx : int = 0, pady : int = 0,
		thick : int = 1, varih : int = 0
	):
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
	# String representation	
	def __str__(self) -> str:
		return (
			"A {} wide by {} tall dungeon,\n" \
			+ "with {} rooms of about {:02.0f}% average area each,\n" \
			+ "or of average dimension {} wide by {} tall,\n" \
			+ "with an average of {} hallways out of each room;\n" \
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
	# Generic representation
	def __repr__(self) -> str:
		return self.__str__()
	# Randomly generate rooms	
	def genRooms(self, reset = False, attemptsOverride : int = 0):
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
	# Randomly generate hallways
	def genHalls(self, reset : bool = False):
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
	"""
	def draw(self, mode : str = '') -> np.array:
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
			
		return maskRoomEdge | maskHall & ~ (
			maskRoomFill & maskHall & ~ (
				maskRoomEdge & maskHall
			)
		)
