from ccDGLevels import Catacombs, Caves
from ccDGLevels import np, Point, Rectangle, Line, Circle
import cv2 as cv

class Renderer:
	"""Docstring"""
	def __init__(
		self, dungeon, tileFilenames : dict,
		tileResX : int, tileResY : int = 0,
		alphaChannel : bool = False
	):
		"""Docstring"""
		if tileResY == 0:
			self.scale = Point(tileResX, tileResX)
		else:
			self.scale = Point(tileResX, tileResY)

		self.size = dungeon.size * self.scale.npar

		if alphaChannel:
			self.channels = 4
		else:
			self.channels = 3

		self.image = np.zeros((self.size.y, dungeon.size.x, self.channels), np.uint8)

		self.masks = dungeon.getImageData()
		self.dungeonType = masks["dungeonType"]

		self.tilenames = tileFilenames
		self.loadTiles()

	def loadTiles(self, tileFilenames : dict = {}):
		pass

	def render(reset : bool = False):
		if reset:
			self.image = np.zeros((self.size.y, self.size.x, self.channels), np.uint8)

		if self.dungeonType == "catacombs":
			paintOrder = ("floorHalls", "floorRooms", "walls", "doors")
		elif self.dungeonType == "caves":
			paintOrder = ("floorHalls", "floorRooms", "floorCarves", "wallHalls", "wallRooms")
		else:
			paintOrder = ()

		for layer in paintOrder:
			indices = np.where(
				self.masks[layer].repeat(self.scale.y, 0).repeat(self.scale.x, 1)
			)

			tileSheet = np.tile(
				self.tiles[layer], (self.dungeon.size.y, self.dungeon.size.x, 1)
			)

			self.image[indices] = tileSheet[indices]
