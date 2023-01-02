import numpy as np
import cv2 as cv
from itertools import combinations

def HSVtoRGB(color : np.array) -> np.array:
	"""Convert a single HSV color to an RGB color"""
	H, S, V = color
	
	CHROMA = S * V
	Hprime = H / 60.
	X = CHROMA * (1. - abs((Hprime % 2.) - 1.))
	m = V - CHROMA

	RGB1 = np.array([
		CHROMA if (
			(Hprime >= 0. and Hprime < 1.) or (Hprime >= 5. and Hprime < 6.)
		) else X if (
			(Hprime >= 1. and Hprime < 2.) or (Hprime >= 4. and Hprime < 5.)
		) else 0.,
		CHROMA if (
			(Hprime >= 1. and Hprime < 2.) or (Hprime >= 2. and Hprime < 3.)
		) else X if (
			(Hprime >= 0. and Hprime < 1.) or (Hprime >= 3. and Hprime < 4.)
		) else 0.,
		CHROMA if (
			(Hprime >= 3. and Hprime < 4.) or (Hprime >= 4. and Hprime < 5.)
		) else X if (
			(Hprime >= 2. and Hprime < 3.) or (Hprime >= 5. and Hprime < 6.)
		) else 0.
	])

	return ((RGB1 + np.array([m, m, m])) * 255.).astype(np.uint8)
# Since BGR is the reverse of RGB, we can use the old ::-1 trick
HSVtoBGR = lambda color : HSVtoRGB(color)[:, ::-1]

def HSVtoRGBVectorized(colors : np.array) -> np.array:
	"""
	Convert many HSV colors to their corresponding RGB colors;
	For this and the above single-color function, thank you Wikipedia
	for the page on HSV and the Color conversion formulae section!
	"""
	def f(H : np.array, S : np.array, V : np.array, n : int) -> np.array:
		K = (H / 60. + n) % 6.
		return V - (
			V * S * np.maximum(
				0, np.minimum(
					1, np.minimum(
						K, 4 - K
					)
				)
			)
		)

	H = colors[:, 0]
	S = colors[:, 1]
	V = colors[:, 2]
	return (
		np.stack(( f(H, S, V, 5), f(H, S, V, 3), f(H, S, V, 1) )).transpose() * 255.
	).astype(np.uint8)
# Since BGR is the reverse of RGB, we can use the old ::-1 trick
HSVtoBGRVectorized = lambda colors : HSVtoRGBVectorized(colors)[:, ::-1]

# Actual tiling
tileSize = (16, 16, 3)
baseTile = np.ones(tileSize, float)

tileTileKeys = (
	"boxN", "boxE", "boxS", "boxW",
	"diagNE", "diagNW", "diagSW", "diagSE"
)
tileBrickKeys = (
	"horiz2", "horiz3", "horiz4", "horiz5",
	"vert2", "vert3", "vert4", "vert5"
)

shadeCount = 24
shadeNames = (
	"RED",
	"RORANGE",
	"ORANGE",
	"BRONZE",
	"YELLOW",
	"LIME",
	"GRASS",
	"GREEN1",
	"GREEN2",
	"GREEN3",
	"GREEN4",
	"POND",
	"CYAN",
	"SKY",
	"CORN",
	"SEA",
	"BLUE",
	"INDIGO",
	"VIOLET",
	"FUSCHIA",
	"MAGENTA",
	"HOTPINK",
	"BLOODORANGE",
	"NOTRED"
)

colorsHSV = np.ones((shadeCount, 3), float)
colorsHSV[:, 0] = np.arange(shadeCount) * 360. / shadeCount

colorsBright = HSVtoBGRVectorized(colorsHSV)

colorsHSV[:, 1] = 0.85
colorsHSV[:, 2] = 0.65

colorsDark = HSVtoBGRVectorized(colorsHSV)

colorsHSV[:, 1] = 0.
colorsHSV[:, 2] = np.linspace(0, 1, shadeCount)

colorsGray = HSVtoBGRVectorized(colorsHSV)
"""
print(colorsBright, colorsDark, colorsGray)

colorTest = np.zeros((8 * 3, 8 * shadeCount, 3), np.uint8)
print(colorTest.shape)
print(colorsBright.repeat(8, 0).shape)
colorTest[0:8, :] = colorsBright.repeat(8, 0)
colorTest[8:16, :] = colorsDark.repeat(8, 0)
colorTest[16:24, :] = colorsGray.repeat(8, 0)

cv.imshow("Color Test", colorTest)
cv.waitKey(0)
"""

tileTileMasks = {}

for k in tileTileKeys:
	if len(k) == 4:
		maskType = k[:-1]
		maskDirection = k[-1]
	else:
		maskType = k[:-2]
		maskDirection = k[-2:]

	if maskType == "box":
		maskVal = -0.25
		if maskDirection == 'N':
			y = 1
			x = np.arange(13) + 1
		elif maskDirection == 'E':
			y = np.arange(13) + 1
			x = 14
		elif maskDirection == 'S':
			y = 14
			x = np.arange(13) + 2
		elif maskDirection == 'W':
			y = np.arange(13) + 2
			x = 1
 
	elif maskType == "diag":
		maskVal = -0.5
		if maskDirection == "NE":
			y = np.arange(8)
			x = np.arange(15, 7, -1)
		elif maskDirection == "NW":
			y = np.arange(8)
			x = np.arange(8)
		elif maskDirection == "SW":
			y = np.arange(8, 16)
			x = np.arange(7, -1, -1)
		elif maskDirection == "SE":
			y = np.arange(8, 16)
			x = np.arange(8, 16)

	tileMask = np.zeros(tileSize, float)
	tileMask[y, x] = maskVal
	tileTileMasks[k] = tileMask

tileDirectory = "./tiles/"
paletteNames = ("BRIGHT", "DARK", "GRAY")
p = 0
for palette in (colorsBright, colorsDark, colorsGray):
	paletteString = paletteNames[p]
	for c in range(shadeCount):
		shadeName = shadeNames[c]
		shade = palette[c]
		print(shadeName)

		for comboCount in range(6, 9):
			maskCombiner = combinations(tileTileKeys, comboCount)
			for maskGroup in maskCombiner:
				boxStrings = list({s[-1] if len(s) == 4 else '' for s in maskGroup})
				try:
					boxStrings.remove('')
				except ValueError:
					pass
				boxStrings = sorted(boxStrings)

				diagStrings = list({s[-2:] if len(s) == 6 else '' for s in maskGroup})
				try:
					diagStrings.remove('')
				except ValueError:
					pass
				diagStrings = sorted(diagStrings)

				fileSuffix = (
					shadeName + paletteString if p < 2 else paletteString + str(c)
				) + "-B-" + '_'.join(boxStrings) + "-D-" + '_'.join(diagStrings)

				mask = baseTile.copy()

				for k in maskGroup:
					mask += tileTileMasks[k]

				mask *= shade

				cv.imwrite(
					tileDirectory + "TILE-" + fileSuffix + ".png", mask.astype(np.uint8)
				)
	p += 1
