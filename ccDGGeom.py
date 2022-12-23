import numpy as np
np.set_printoptions(
	linewidth = 128, precision = 3,
	formatter = {"bool" : lambda b : '#' if b else '_'}
) # Above makes pre-imaging debugging easier to view

# Numpy supporting point class
class Point:
	# Needs a coordinate
	def __init__(self, x : int, y : int):
		self.x = x
		self.y = y
		self.dict = {'y': y, 'x': x}
		self.npar = np.array([y, x], int)
		self.tupl = (x, y)
	# String representation
	def __str__(self) -> str:
		return str(self.tupl)
	# Generic representation (just uses __str__)
	def __repr__(self) -> str:
		return self.__str__()
	# Arithmetic operators
	def __add__(self, other):
		p = self.npar + other.npar
		return Point(p[1], p[0])
	def __sub__(self, other):
		p = self.npar - other.npar
		return Point(p[1], p[0])
	def __mul__(self, scalar : int):
		p = self.npar * scalar
		return Point(p[1], p[0])

# Base shape class
class Shape:
	# Placeholder, subclass must implement!
	def getCentroid(self) -> Point:
		return Point(0, 0)
	# Placeholder, subclass must implement!
	def getMinFrame(self) -> Point:
		return Point(0, 0)
	# Placeholder, subclass must implement!
	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
		return np.zeros(1, bool)
	# Determine if the shape fits with an arbitrary frame
	def isInBounds(self, frame : Point) -> bool:
		return np.all(self.getMinFrame().npar <= frame.npar)
	# Use the mask method to determine if this rectangle overlaps with another
	def overlaps(self, other) -> bool:
		smf = self.getMinFrame()
		omf = other.getMinFrame()
		w = max(smf.x, omf.x)
		h = max(smf.y, omf.y)
		return np.count_nonzero(self.getMaskFill(w, h) & other.getMaskFill(w, h)) > 0
	# Turn the overlap method into an operator (not commutative!) (IT IS, YOU IDIOT!!)
	def __and__(self, other) -> bool:
		return self.overlaps(other)
	# Determine the bearing towards another shape (its centroid in particular)
	def getAzimuth(self, other) -> float:
		vector = self.getCentroid() - other.getCentroid()
		"""
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
		Mathematcially, this is $\theta + 90$. Since we don't want negative azimuths,
		we mod by 360 to wind negatives around.
		"""
		return ((np.arctan2(vector.y, vector.x) * 180. / np.pi) + 90.) % 360.

# Numpy supporting rectangle class
class Rectangle(Shape):
	# Needs a coordinate for the northwest corner (nearest to origin), a width, and height
	def __init__(self, x : int, y : int, w : int, h : int):
		self.origin = Point(x, y)
		self.height = abs(h)
		self.width = abs(w)
		self.area = self.height * self.width
		self.refreshEdgeCells()
	# String representation
	def __str__(self) -> str:
		return "A {: 4d} by {: 4d} Rectangle cornered at ({: 4d}, {: 4d}).".format(
			self.width, self.height, self.origin.x, self.origin.y
		)
	# Generic representation (just uses __str__)
	def __repr__(self) -> str:
		return self.__str__()
	# Make six sets detailing the coordinates of cells in the rectangle on the edge of it
	def refreshEdgeCells(self):
		yi = self.origin.y
		xi = self.origin.x
		self.corners = {
			Point(xi + xo, yi + yo)
			for xo in (0, self.width - 1)
			for yo in (0, self.height - 1)
		}
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
	# Determine the center cell of the rectangle
	def getCentroid(self) -> Point:
		return self.origin + Point(self.width // 2, self.height // 2)
	# Determine the minimum graphic frame for the rectangle
	def getMinFrame(self) -> Point:
		return self.origin + Point(self.width, self.height)
	# Get a binary numpy mask array with the rectangle filled in, to arbitrary frame size
	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
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
	# Get a binary numpy mask array with the rectangle's edge only, to arbitrary frame size
	def getMaskEdge(self, fw : int = 0, fh : int = 0) -> np.array:
		M = self.getMaskFill(fw, fh)
		
		M[
			self.origin.y + 1 : self.origin.y + self.height - 1,
			self.origin.x + 1 : self.origin.x + self.width - 1
		] = 0
		
		return M
	# Compute the percentage of how much of this rectangle overlaps with another
	def percentOverlap(self, other) -> float:
		smf = self.getMinFrame()
		omf = other.getMinFrame()
		w = max(smf.x, omf.x)
		h = max(smf.y, omf.y)
		return np.count_nonzero(self.getMaskFill(w, h) & other.getMaskFill(w, h)) / self.area
	# Determine the closest wall that faces another rectangle
	def getNearestWall(self, other) -> set:
		a = self.getAzimuth(other)
		if a > 315. or a <= 45.:
			return self.edgeCellsSouth
		elif a > 45. and a <= 135.:
			return self.edgeCellsWest
		elif a > 135. and a <= 225.:
			return self.edgeCellsNorth
		elif a > 225. and a <= 315.:
			return self.edgeCellsEast
		return {}

# Numpy supporting line class
class Line(Shape):
	# Needs a coordinate, a length, and an orientation
	def __init__(self, x : int, y : int, l : int, o : str):
		o = o.lower()[0]
		self.origin = Point(x, y)
		self.length = abs(l)
		self.orient = Point(
			-1 if o == 'w' else 1 if o == 'e' else 0,
			-1 if o == 'n' else 1 if o == 's' else 0
		)
	# Determine the center cell of the line
	def getCentroid(self) -> Point:
		return self.origin + self.orient * (self.length // 2)
	# Determine the cell at the end of the line
	def getEndpoint(self) -> Point:
		return self.origin + self.orient * (self.length - 1)
	# Determine the minimum graphic frame for the line
	def getMinFrame(self) -> Point:
		e = self.getEndpoint()
		return Point(max(self.origin.x, e.x) + 1, max(self.origin.y, e.y) + 1)
	# Determine if the line fits within an arbitrary frame
	def isInBounds(self, frame : Point) -> bool:
		return np.all(self.getMinFrame().npar <= frame.npar)
	# Get a binary numpy mask array with the line drawn, arbitrary frame size
	def getMask(self, fw : int = 0, fh : int = 0) -> np.array:
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
	# Allow for interoperability with overlaps for rectangles and circles
	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
		return self.getMask(fw, fh)
	# Determine the bearing to another line (or rectangle, centroid mode only!)
	def getAzimuth(self, other, mode = 'c') -> float:
		if mode.lower()[0] == 'e':
			vector = self.getEndpoint() - other.getEndpoint()
		else:
			vector = self.getCentroid() - other.getCentroid()
		# See description in shape class for why this works
		return ((np.arctan2(vector.y, vector.x) * 180. / np.pi) + 90.) % 360.
	# Determine which cardinal direction leads closest to another line
	# (or rectangle, centroid mode only like above!)
	def getNearestOrientation(self, other, mode = 'c') -> tuple:
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

# Numpy supporting circle class
class Circle(Shape):
	# Needs a coordinate and radius
	def __init__(self, x : int, y : int, r : int):
		self.origin = Point(x, y)
		self.radius = abs(r)
		self.edgePoints = {}
		self.refreshEdgePoints()
	# Use a version of the midpoint circle algorithm to compute the edge cells of the circle
	def refreshEdgePoints(self, charliesMethod : bool = True):
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
		self.edgePoints = {p + self.origin for p in firstQuarter} \
			| {Point(*p) + self.origin for p in secondQuarter} \
			| {Point(*p) + self.origin for p in thirdQuarter} \
			| {Point(*p) + self.origin for p in fourthQuarter} 
	# Determine the minimum graphic frame for the circle
	def getMinFrame(self) -> Point:
		return self.origin + Point(self.radius + 1, self.radius + 1)
	# Return the center cell of the cirlce
	def getCentroid(self) -> Point:
		return self.origin
	# Get a binary numpy mask array with the circle's edge only, to arbitrary frame size
	def getMaskEdge(self, fw : int = 0, fh : int = 0) -> np.array:
		if fw == 0 or fh == 0:
			f = self.getMinFrame()
			fw = f.x
			fh = f.y
			
		M = np.zeros((fh, fw), bool)
		
		for p in self.edgePoints:
			M[p.y, p.x] = 1
			
		return M
	# Use flood fill to get a binary numpy mask array with the circle filled in,
	# to arbitrary frame size
	def getMaskFill(self, fw : int = 0, fh : int = 0) -> np.array:
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

