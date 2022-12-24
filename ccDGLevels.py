from ccDGGeom import np, Point, Rectangle, Line, Circle

# Nethack style dungeon
class Catacombs:
	def __init__(
		self, w : int, h : int,
		rct : int, conn : int,
		raap : float,
		varix : int, variy : int,
		padx : int = 0, pady : int = 0
	):
		self.size = Point(w, h)
		self.roomCount = rct
		self.hallAvgCount = conn
		self.roomAvgAreaPercent = raap
		self.variance = Point(varix, variy)
		self.padding = Point(padx, pady)
		# Average dimension of each room
		adim = (self.size.npar * np.sqrt(self.roomAvgAreaPercent)).astype(int)
		self.roomAvgDim = Point(adim[1], adim[0])
		# Store the rooms and halls in these lists, must generate them separately
		self.rooms = []
		self.halls = []
		self.hallCounts = []
		
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
	
	def __repr__(self) -> str:
		return self.__str__()
	# Randomly generate rooms	
	def genRooms(self, reset = False, attemptsOverride : int = 0):
		if not reset:
			return
		
		self.rooms = []
		self.halls = []
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
			)
		
		while len(self.rooms) < self.roomCount:
			attempts += 1
			noise = np.random.randint(
				-self.variance.npar[::-1], self.variance.npar[::-1] + 1, 2
			)
			newSize = Point(*np.maximum(
				self.roomAvgDim.npar[::-1] + noise,
				np.zeros(2, int) + 4
			))
			originSpace = self.size - newSize
			newOrigin = Point(*np.random.randint(np.zeros(2, int), originSpace.tupl, 2))
			newRoom = Rectangle(newOrigin.x, newOrigin.y, newSize.x, newSize.y)
			newRoomPadZone = Rectangle(
				max(newOrigin.x - self.padding.x, 0),
				max(newOrigin.y - self.padding.y, 0),
				newSize.x + 2 * self.padding.x,
				newSize.y + 2 * self.padding.y
			)
			
			nonOverlapping = True
			for r in self.rooms:
				if newRoomPadZone & r:
					nonOverlapping = False
					break
			
			if nonOverlapping:
				self.rooms.append(newRoom)
				print(noise, newSize, newOrigin)
				print(newRoom)
				print(newRoomPadZone)
				print()
				
			if attempts > maxAttempts:
				if len(self.rooms) < self.roomCount:
					print("Warning: maximum room generation attempts reached.")
					print("Your dungeon will only have", len(self.rooms), "rooms")
				break

		self.hallCounts = [0 for i in range(len(self.rooms))]
		
		print("Attemped room generations", attempts, "times.")

	def genHalls(self, reset : bool = False):
		if not reset:
			return
	
		self.halls = []

		for i in range(len(self.rooms)):
			room = self.rooms[i]

			distances = [
				[j, room.getCentroid() | self.rooms[j].getCentroid()]
				for j in range(len(self.rooms))
			]
			distances[i][1] = 2 * max([t[1] for t in distances])
			distances = sorted(distances, key = lambda t : t[1])[:len(distances) - 1]
			print(distances)

			j = 0
			#for otherInfo in distances[:self.hallAvgCount - self.hallCounts[i]]:
			while self.hallCounts[i] < self.hallAvgCount:
				k = distances[j][0]
				mhDist = distances[j][1]
				other = self.rooms[k]

				wallInfo = room.getNearestWall(other)
				wallOrient = wallInfo[0]
				wallCells = wallInfo[1]

				wallOtherInfo = other.getNearestWall(room)
				wallOtherOrient = wallOtherInfo[0]
				wallOtherCells = wallOtherInfo[1]

				print(i, j, k, room.getAzimuth(other), wallOrient, len(wallCells))

				startRoom = list(wallCells)[
					np.random.randint(0, len(wallCells))
				]
				startOther = list(wallOtherCells)[
					np.random.randint(0, len(wallOtherCells))
				]
				
				delta = startRoom - startOther
				dx = abs(delta.x)
				dy = abs(delta.y)

				print(startRoom, startOther, dx, dy)

				if wallOrient in ('n', 's') and wallOtherOrient in ('n', 's') \
					or wallOrient in ('e', 'w') and wallOtherOrient in ('e', 'w'):				
					roomHall = Line(
						startRoom.x, startRoom.y,
						dx // 2 + 1 + dx % 2 if wallOrient in ('e', 'w')
						else dy // 2 + 1 + dy % 2,
						wallOrient
					)
					otherHall = Line(
						startOther.x, startOther.y,
						dx // 2 + 1 if wallOtherOrient in ('e', 'w')
						else dy // 2 + 1,
						wallOtherOrient
					)

					connectingOrientation = roomHall.getNearestOrientation(
						otherHall, mode = 'e'
					)[0]
					connectingHall = Line(
						roomHall.getEndpoint().x, roomHall.getEndpoint().y,
						dy + 1 if wallOrient in ('e', 'w') else dx + 1,
						connectingOrientation
					)

					self.halls.append(connectingHall)
				else: # Parallel above, Perpendicular below
					print("NON-CONNECTION HALL GENERATED!!!")
					roomHall = Line(
						startRoom.x, startRoom.y,
						dx + 1 if wallOrient in ('e', 'w') else dy + 1,
						wallOrient
					)
					
					otherHall = Line(
						startOther.x, startOther.y,
						dx + 1 if wallOtherOrient in ('e', 'w') else dy + 1,
						wallOtherOrient
					)

				self.halls.append(roomHall)
				self.halls.append(otherHall)

				self.hallCounts[i] += 1
				self.hallCounts[k] += 1
				j += 1
				j %= len(distances)
				
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
			
		return maskRoomEdge | maskHall & ~ (
			maskRoomFill & maskHall & ~ (
				maskRoomEdge & maskHall
			)
		)
