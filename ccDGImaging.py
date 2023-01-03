from ccDGLevels import Catacombs, Caves
from ccDGLevels import np, Point, Rectangle, Line, Circle
import cv2 as cv

catacombsTileKeys = ("hall", "floor", "wall", "door")
cavesTileKeys = ("floorHall", "floorRoom", "floorCarve", "wallHall", "wallRoom")

class Renderer:
	""""""
	def __init__(
		self, dungeon, tileInfo : dict,
		tileResX : int, tileResY : int = 0,
		alphaChannel : bool = False
	):
		"""
		Requires a constructed dungeon, a tile information dictionary,
		and a resolution size of each tile. Optionally,
		non-square tiles can be specified with a Y-resolution,
		and it can be specified if an alpha channel should be used.
		"""
		if tileResY == 0: # Square tiles
			self.scale = Point(tileResX, tileResX)
		else: # Rectangular tiles
			self.scale = Point(tileResX, tileResY)
		# Image size
		self.size = dungeon.size * self.scale.npar

		if alphaChannel: # Transparent
			self.channels = 4
		else: # Opaque
			self.channels = 3
		# Note: OpenCV's default colorspace is BGR, not RGB.
		# To preview this properly, you need to reverse the third axis (see below)
		self.image = np.zeros((self.size.y, dungeon.size.x, self.channels), np.uint8)

		self.masks = dungeon.getImageData()
		self.dungeonType = masks["dungeonType"]

		self.tileInfo = tileInfo
		self.loadTiles()

	def loadTiles(self, tileInfo : dict = {}):
		"""
		Use the existing tileInfo, or new tileInfo,
		to read in the individual tile files
		and prepare the tiles dictionary
		"""
		if len(tileInfo.keys()) > 0: # Allow for fixes/overrides
			self.tileInfo = tileInfo

		self.tiles = {}

		if self.dungeonType == "catacombs":
			self.tileKeys = catacombsTileKeys
		elif self.dungeonType == "caves":
			self.tileKeys = cavesTileKeys
		else:
			self.tileKeys = ()

		failedToLoad = False
		for k in self.tileKeys: # Across all types of tiles
			try:
				tileGroup = [ # Load all tiles of a type in one go (and hope it works)
					cv.imread(filename) for filename in self.tileInfo[k]["files"]
				]

				self.tiles[k] = {
					"tiles" : tileGroup,
					"variants" : len(tileGroup),
					"probabilities": np.concatenate(
						( # Uniform chance is default
							np.zeros(1), np.cumsum(
								np.ones(len(tileGroup)) / len(tileGroup)
							)
						) # This reduces to [0., 1.] in the case of only 1 variant
					) if "probs" not in self.tileInfo[k].keys() else np.concatenate(
						( # Don't try to index by the probs key unless we're sure it's there
							np.zeros(1), np.cumsum(self.tileInfo[k]["probs"])
						)
					)
				}
			except FileNotFoundError as e: # If it didn't work
				print("Error! Could not load tile(s) for", k)
				print("Error Message:", e)
				failedToLoad = True
				break

			if self.tiles[k]["probabilities"][-1] > 1.:
				# Won't break things but undesireable
				print("Warning! Tile probabilities on", k, "do not add up to 1.")
				print("You may see weird distributions of this tile type.")

		if failedToLoad:
			print("Warning! Tile loading failed. Please re-invoke loadTiles()")
			print("with a properly formatted tileInfo dictionary.")
			print("Current dictionary:")
			print(self.tileInfo)
			self.tiles = {}

	def render(reset : bool = False):
		"""Use the masks to paint the tiles on one layer at a time"""
		if reset: # Clear out old rendering work
			self.image = np.zeros((self.size.y, self.size.x, self.channels), np.uint8)

		if self.dungeonType == "catacombs":
			paintOrder = catacombsTileKeys
		elif self.dungeonType == "caves":
			paintOrder = cavesTileKeys
		else:
			paintOrder = ()

		for layer in paintOrder:
			indices = np.where(
				self.masks[layer].repeat(self.scale.y, 0).repeat(self.scale.x, 1)
			) # Scale up the current mask to the image size
			# Decide randomly which tile variants will appear where
			variantizer = np.random.uniform(size = self.dungeon.size.npar)
			# Do you want this typed out in full two more times? Me neither
			probs = self.tiles[layer]["probabilites"]

			for i in range(self.tiles[layer]["variants"]): # Across all variants
				tileSheet = np.tile( # For the numpy magic below
					self.tiles[layer]["tiles"][i],
					(self.dungeon.size.y, self.dungeon.size.x, 1)
				)
				# Because we need two prob values, we need the concat of zeros
				# as shown above in loadTiles()
				variedIndicies = indices & (variantizer >= probs[i]) \
					& (variantizer < probs[i + 1])
				# Numpy magic!
				self.image[variedIndicies] = tileSheet[variedIndicies]
