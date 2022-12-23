from ccDGGeom import np, Point, Rectangle, Line, Circle

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
		
		adim = (self.size.npar * np.sqrt(self.roomAvgAreaPercent)).astype(int)
		self.roomAvgDim = Point(adim[1], adim[0])
		
		self.rooms = []
		self.halls = []
		
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
	
	def genRooms(self, reset = False, attemptsOverride : int = 0):
		if not reset:
			return
		
		self.rooms = []
		attempts = 0
		if attemptsOverride > 0:
			maxAttempts = attemptsOverride
		else:
			maxAttempts = int(
				round(
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
		
		print("Attemped room generations", attempts, "times.")
				
	def draw(self) -> np.array:
		mask = np.zeros(self.size.npar, bool)
		for r in self.rooms:
			mask |= r.getMaskEdge(self.size.x, self.size.y)
		for h in self.halls:
			mask |= h.getMask(self.size.x, self.size.y)
			
		return mask
