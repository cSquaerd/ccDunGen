import numpy as np
np.set_printoptions(
	linewidth = 128, precision = 3,
	formatter = {"bool" : lambda b : '#' if b else '_'}
) # Above makes pre-imaging debugging easier to view

class Point:
	"""Numpy supporting point class"""
	def __init__(self, x : int, y : int):
		"""Needs a coordinate"""
		self.x = x
		self.y = y
		self.dict = {'y': y, 'x': x}
		self.npar = np.array([y, x], int)
		self.tupl = (x, y)
	
	def __str__(self) -> str:
		"""String representation"""
		return str(self.tupl)

	def __repr__(self) -> str:
		"""Generic representation (just uses __str__)"""
		return self.__str__()

	# Arithmetic operators
	def __add__(self, other):
		if type(other) in (int, float):
			p = self.npar + other
		else:
			p = self.npar + other.npar
		return Point(p[1], p[0])
	def __sub__(self, other):
		if type(other) in (int, float):
			p = self.npar - other
		else:
			p = self.npar - other.npar
		return Point(p[1], p[0])
	def __mul__(self, scalar : int):
		# Note: happens to work with numpy arrays of the same shape
		# because type "hints" aren't strictly enforced
		p = self.npar * scalar
		return Point(p[1], p[0])
	def __floordiv__(self, divisor : np.array):
		# Ditto
		p = self.npar // divisor
		return Point(p[1], p[0])

	def __or__(self, other) -> int:
		"""Manhattan a.k.a. taxicab distance"""
		return abs(self.x - other.x) + abs(self.y - other.y)

class Shape:
	"""Base shape class"""
	def getCentroid(self) -> Point:
		"""Placeholder, subclass must implement!"""
		return Point(0, 0)

	def getMinFrame(self) -> Point:
		"""Placeholder, subclass must implement!"""
		return Point(0, 0)

	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
		"""Placeholder, subclass must implement!"""
		return np.zeros(1, bool)

	def isInBounds(self, frame : Point) -> bool:
		"""Determine if the shape fits with an arbitrary frame"""
		return np.all(self.getMinFrame().npar <= frame.npar)

	def overlaps(self, other) -> bool:
		"""Use the mask method to determine if this rectangle overlaps with another"""
		smf = self.getMinFrame()
		omf = other.getMinFrame()
		w = max(smf.x, omf.x)
		h = max(smf.y, omf.y)
		return np.count_nonzero(self.getMaskFill(w, h) & other.getMaskFill(w, h)) > 0

	def __and__(self, other) -> bool:
		"""
		Turn the overlap method into an operator (not commutative!)
		(IT IS, YOU IDIOT!!)
		"""
		return self.overlaps(other)

	def getAzimuth(self, other) -> float:
		"""
		Determine the bearing towards another shape (its centroid in particular)

		To go from trig angles (
			start at 3 o'clock, counterclockwise
		) to azimuths (
			start at 6 o'clock (
				not noon since y increseas downward in graphics
			), clockwise (
				but this is cancelled out by Graphics Space being right-handed,
				compared to Cartesian Space, which is left-handed;
				In right-handed trig, angles increase clockwise (think about it!)
			)
		), we need to rotate 90 degrees to the right to bring the trig 0-axis
		to meet the place for the azimuth 0-axis.

		Mathematcially, this is $\theta - 90$.
		Since we don't want negative azimuths, we mod by 360 to wind negatives around.
		"""
		vector = other.getCentroid() - self.getCentroid()
		return ((np.arctan2(vector.y, vector.x) * 180. / np.pi) - 90.) % 360.

class Rectangle(Shape):
	"""Numpy supporting rectangle class"""
	def __init__(self, x : int, y : int, w : int, h : int):
		"""
		Needs a coordinate for the northwest corner (nearest to origin),
		a width, and height
		"""
		self.origin = Point(x, y)
		self.height = abs(h)
		self.width = abs(w)
		self.area = self.height * self.width
		self.refreshEdgeCells()
	
	def __str__(self) -> str:
		"""String representation"""
		return "A {: 4d} by {: 4d} Rectangle cornered at ({: 4d}, {: 4d}).".format(
			self.width, self.height, self.origin.x, self.origin.y
		)

	def __repr__(self) -> str:
		"""Generic representation (just uses __str__)"""
		return self.__str__()

	def refreshEdgeCells(self):
		"""
		Make six sets detailing the coordinates of cells on the edge of the rectangle
		"""
		yi = self.origin.y
		xi = self.origin.x

		self.corners = {
			Point(xi + xo, yi + yo)
			for xo in (0, self.width - 1)
			for yo in (0, self.height - 1)
		}
		# Compute the azimuth boundary angles based on the corners
		C = self.getCentroid().npar - np.array([c.npar for c in self.corners], int)
		azimuths = ((np.arctan2(C[:, 0], C[:, 1]) * 180. / np.pi) + 90.) % 360.
		# Use these down in getNearestWall
		self.azi45 = azimuths[
			np.where((azimuths > 0.) & (azimuths <= 90.))[0][0]
		]
		self.azi135 = azimuths[
			np.where((azimuths > 90.) & (azimuths <= 180.))[0][0]
		]
		self.azi225 = azimuths[
			np.where((azimuths > 180.) & (azimuths <= 270.))[0][0]
		]
		self.azi315 = azimuths[
			np.where((azimuths > 270.) & (azimuths <= 360.))[0][0]
		]

		self.edgeCellsNorth = {
			Point(xe, yi)
			for xe in range(xi + 1, xi + self.width - 1)
		}
		self.edgeCellsWest = {
			Point(xi, ye)
			for ye in range(yi + 1, yi + self.height - 1)
		}
		self.edgeCellsSouth = {
			Point(xe, yi + self.height - 1)
			for xe in range(xi + 1, xi + self.width - 1)
		}
		self.edgeCellsEast = {
			Point(xi + self.width - 1, ye)
			for ye in range(yi + 1, yi + self.height - 1)
		}
		
		self.edgeCells = self.corners | self.edgeCellsNorth | self.edgeCellsWest \
			| self.edgeCellsSouth | self.edgeCellsEast
	
	def getCentroid(self) -> Point:
		"""Determine the center cell of the rectangle"""
		return self.origin + Point(self.width // 2, self.height // 2)

	def getMinFrame(self) -> Point:
		"""Determine the minimum graphic frame for the rectangle"""
		return self.origin + Point(self.width, self.height)

	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
		"""
		Get a binary numpy mask array with the rectangle filled in,
		to arbitrary frame size
		"""
		if fw == 0 or fh == 0:
			f = self.getMinFrame()
			fw = f.x
			fh = f.y
		
		M = np.zeros((fh, fw), bool)
		
		M[
			self.origin.y : self.origin.y + self.height,
			self.origin.x : self.origin.x + self.width
		] = 1
		
		return M

	def getMaskEdge(self, fw : int = 0, fh : int = 0) -> np.array:
		"""
		Get a binary numpy mask array with the rectangle's edge only,
		to arbitrary frame size
		"""
		M = self.getMaskFill(fw, fh)
		
		M[
			self.origin.y + 1 : self.origin.y + self.height - 1,
			self.origin.x + 1 : self.origin.x + self.width - 1
		] = 0
		
		return M

	def percentOverlap(self, other) -> float:
		"""Compute the percentage of how much of this rectangle overlaps with another"""
		smf = self.getMinFrame()
		omf = other.getMinFrame()
		w = max(smf.x, omf.x)
		h = max(smf.y, omf.y)
		return np.count_nonzero(self.getMaskFill(w, h) & other.getMaskFill(w, h)) / self.area

	def getNearestWall(self, other) -> tuple:
		"""Determine the closest wall that faces another rectangle"""
		a = self.getAzimuth(other)
		if a > self.azi315 or a <= self.azi45:
			return ('s', self.edgeCellsSouth)
		elif a > self.azi45 and a <= self.azi135:
			return ('w', self.edgeCellsWest)
		elif a > self.azi135 and a <= self.azi225:
			return ('n', self.edgeCellsNorth)
		elif a > self.azi225 and a <= self.azi315:
			return ('e', self.edgeCellsEast)
		return ()

class Line(Shape):
	"""Numpy supporting line class"""
	def __init__(self, x : int, y : int, l : int, o : str):
		"""Needs a coordinate, a length, and an orientation"""
		o = o.lower()[0]
		self.origin = Point(x, y)
		self.length = abs(l)
		self.orient = Point(
			-1 if o == 'w' else 1 if o == 'e' else 0,
			-1 if o == 'n' else 1 if o == 's' else 0
		)

	def __str__(self):
		"""String representation"""
		return "A {: 4d} cell long line starting from {} headed {}.".format(
			self.length, self.origin, [ # Fuck you we do this cursed!
				[' ', 'east', 'west'],
				['south', ' ', ' '],
				['north', ' ', ' '],
			][self.orient.y][self.orient.x]
		)

	def __repr__(self):
		"""Generic representation (just uses __str__)"""
		return self.__str__()

	def getCentroid(self) -> Point:
		"""Determine the center cell of the line"""
		return self.origin + self.orient * (self.length // 2)

	def getEndpoint(self) -> Point:
		"""Determine the cell at the end of the line"""
		return self.origin + self.orient * (self.length - 1)

	def getMinFrame(self) -> Point:
		"""Determine the minimum graphic frame for the line"""
		e = self.getEndpoint()
		return Point(max(self.origin.x, e.x) + 1, max(self.origin.y, e.y) + 1)

	def isInBounds(self, frame : Point) -> bool:
		"""Determine if the line fits within an arbitrary frame"""
		return np.all(self.getMinFrame().npar <= frame.npar)

	def getMask(self, fw : int = 0, fh : int = 0) -> np.array:
		"""Get a binary numpy mask array with the line drawn, arbitrary frame size"""
		pi = self.origin
		pf = pi + self.orient * self.length
		# the abs-abs thing is for the slice to work properly
		sliceCompensate = np.abs(np.abs(self.orient.npar) - 1)
		pSC = Point(sliceCompensate[1], sliceCompensate[0])
		# Flip if need be for the slice to work properly
		if pi.x > pf.x:
			xt = pf.x
			pf = Point(pi.x + 1, pf.y)
			pi = Point(xt + 1, pi.y)
		if pi.y > pf.y:
			yt = pf.y
			pf = Point(pf.x, pi.y + 1)
			pi = Point(pi.x, yt + 1)
		# Apply slice compensation
		pf = pf + pSC
		# Apply northwest culling
		northwestCull = np.maximum(pi.npar, np.zeros(2, int))
		pi = Point(northwestCull[1], northwestCull[0])

		if fw == 0 or fh == 0:
			fw = pf.x
			fh = pf.y
			
		M = np.zeros((fh, fw), bool)
		
		M[pi.y:pf.y, pi.x:pf.x] = 1
		
		return M

	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
		"""Allow for interoperability with overlaps for rectangles and circles"""
		return self.getMask(fw, fh)

	def getAzimuth(self, other, mode = 'c') -> float:
		"""
		Determine the bearing to another line
		(or rectangle, centroid mode only!)
		"""
		if mode.lower()[0] == 'e':
			vector = self.getEndpoint() - other.getEndpoint()
		else:
			vector = self.getCentroid() - other.getCentroid()
		# See description in shape class for why this works
		return ((np.arctan2(vector.y, vector.x) * 180. / np.pi) + 90.) % 360.

	def getNearestOrientation(self, other, mode = 'c') -> tuple:
		"""
		Determine which cardinal direction leads closest to another line
		(or rectangle, centroid mode only like above!)
		"""
		a = self.getAzimuth(other, mode)
		if a > 315. or a <= 45.:
			return ('s', Point(0, 1))
		elif a > 45. and a <= 135.:
			return ('w', Point(-1, 0))
		elif a > 135. and a <= 225.:
			return ('n', Point(0, -1))
		elif a > 225. and a <= 315.:
			return ('e', Point(1, 0))
		return ()

class Circle(Shape):
	"""Numpy supporting circle class"""
	def __init__(self, x : int, y : int, r : int):
		"""Needs a coordinate and radius"""
		self.origin = Point(x, y)
		self.radius = abs(r)
		self.edgeCells = {}
		self.refreshEdgeCells()

	def __str__(self):
		"""String representation"""
		return "A radius {: 4d} circle centered at {}.".format(self.radius, self.origin)

	def __repr__(self):
		"""Generic representation (just uses __str__)"""
		return self.__str__()
	
	def refreshEdgeCells(self, charliesMethod : bool = True):
		"""
		Use a version of the midpoint circle algorithm to compute
		the edge cells of the circle
		"""
		firstQuarter = []
		p = Point(self.radius, 0) # Start at (r, 0)
		# Build up from 0 to pi/2 radians in quadrant 1
		while p.x > 0:
			firstQuarter.append(p)
			nextPoints = (
				Point(p.x - 1, p.y),
				Point(p.x, p.y + 1),
				Point(p.x - 1, p.y + 1)
			)
			XY = np.stack(tuple(p.tupl for p in nextPoints)) # Vectorize next points
			
			if charliesMethod: # Filter out points that are too far out first
				nextPointsWithinRange = []
				for i in np.where(
					XY[:, 0] ** 2 + XY[:, 1] ** 2 - (
						self.radius ** 2 + int(self.radius ** 0.5)
					) <= 0
				)[0]:
					nextPointsWithinRange.append(nextPoints[i])
					
				XYWithinRange = np.stack(tuple(p.tupl for p in nextPointsWithinRange))
				# Take the farthest out point that passed the above filter
				p = nextPointsWithinRange[
					np.argmax(
						XYWithinRange[:, 0] ** 2 + XYWithinRange[:, 1] ** 2
					)
				]
			else: # Standard vectorized midpoint circle algorithm (I think?)
				p = nextPoints[
					np.argmin(
						np.abs(
							XY[:, 0] ** 2 + XY[:, 1] ** 2 - (
								self.radius ** 2 + int(self.radius ** 0.5)
							)
						)
					)
				]
		# Vectorize the quadrant 1 points then apply rotation matrices to them
		fqA = np.array(tuple(p.tupl for p in firstQuarter), int).transpose()
		sqR, tqR, rqR = (
			np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
			for t in (np.pi / 2, np.pi, 3 * np.pi / 2)
		)
		# After rotating, bring them back to ints and back to a list of lists
		secondQuarter = (sqR @ fqA).round().astype(int).transpose().tolist()
		thirdQuarter = (tqR @ fqA).round().astype(int).transpose().tolist()
		fourthQuarter = (rqR @ fqA).round().astype(int).transpose().tolist()
		# Apply a translation to all points
		self.edgeCells = {p + self.origin for p in firstQuarter} \
			| {Point(*p) + self.origin for p in secondQuarter} \
			| {Point(*p) + self.origin for p in thirdQuarter} \
			| {Point(*p) + self.origin for p in fourthQuarter}
	
	def getMinFrame(self) -> Point:
		"""Determine the minimum graphic frame for the circle"""
		return self.origin + Point(self.radius + 1, self.radius + 1)

	def getCentroid(self) -> Point:
		"""Return the center cell of the cirlce"""
		return self.origin

	def getMaskEdge(self, fw : int = 0, fh : int = 0) -> np.array:
		"""
		Get a binary numpy mask array with the circle's edge only,
		to arbitrary frame size
		"""
		if fw == 0 or fh == 0:
			f = self.getMinFrame()
			fw = f.x
			fh = f.y
			
		M = np.zeros((fh, fw), bool)
		
		for p in self.edgeCells:
			M[p.y, p.x] = 1
			
		return M

	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
		"""
		Use flood fill to get a binary numpy mask array with the circle filled in,
		to arbitrary frame size
		"""
		M = self.getMaskEdge(fw, fh)
		
		queue = [self.origin]
		while len(queue) > 0:
			p = queue.pop()
			if M[p.y, p.x] == 0:
				M[p.y, p.x] = 1
				queue.insert(0, Point(p.x, p.y - 1))
				queue.insert(0, Point(p.x - 1, p.y))
				queue.insert(0, Point(p.x, p.y + 1))
				queue.insert(0, Point(p.x + 1, p.y))
				
		return M

	def getAngledEdgeCell(self, azimuth : float) -> Point:
		"""Determine the best edge cell of this circle given a bearing"""
		# Since we -90 deg to go from trig to azimuth, we undo that to go back
		theta = (azimuth + 90.) % 360.

		trigStuff = np.array([
			np.sin(theta * np.pi / 180.),
			np.cos(theta * np.pi / 180.)
		])

		estimate = self.origin + Point(
			*( # Fuck you, we unpack iterables in my code!
				(self.origin.npar * trigStuff).round().astype(int).tolist()[::-1]
			)
		)
		edgeArray = np.vstack([p.npar for p in self.edgeCells])

		correct = np.count_nonzero(np.all(estimate.npar == edgeArray, axis = 1))

		if not correct:
			return Point(
				*( # Unpack into individual parameters
					edgeArray[
						np.argmin( # Index of smallest total deviated cell
							np.sum( # Total taxicab deviation per cell
								np.abs( #Absolute deviation per axis
									edgeArray - estimate.npar
								), axis = 1
							)
						)
					][::-1] # Reverse from (y, x) to (x, y)
				)
			)

		return estimate

