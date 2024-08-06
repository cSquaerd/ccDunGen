from math import ceil, log

digitLength = lambda n : ceil(log(max(n, 1) + 1, 10))
typeScrubber = lambda hints, arg : (
	hints[arg].__name__ if arg in hints.keys() and isinstance(hints[arg], type)
	else hints[arg] if arg in hints.keys()
	else ''
)
typeLengther = lambda hints, arg : (
	len(hints[arg].__name__) if arg in hints.keys() and isinstance(hints[arg], type)
	else len(hints[arg]) if arg in hints.keys()
	else 0
)

def getDocStringWithArgs(
	f : "function", descriptions : list, indentation : int = 2,
	isMethod : bool = False, classMemberNames : list = []
) -> str:
	if not hasattr(f, "__code__"):
		raise ValueError(
			"Provided function has no .__code__ element, probably a builtin."
		)

	hints = f.__annotations__
	defaults = f.__defaults__
	argCount = f.__code__.co_argcount
	
	if isMethod:
		i_argStart = 1
		argCount -= 1
	else:
		i_argStart = 0
	
	argNames = f.__code__.co_varnames[i_argStart:argCount + i_argStart]

	if len(argNames) != len(descriptions):
		raise ValueError(
			(
				"Length mismatch between number of arguments "
				"and number of argument descriptions ({:d} vs. {:d})".format(
					len(argNames), len(descriptions)
				)
			)
		)
	if isMethod and len(argNames) != len(classMemberNames):
		raise ValueError(
			(
				"Length mismatch between number of arguments "
				"and number of argument class member names ({:d} vs. {:d})".format(
					len(argNames), len(classMemberNames)
				)
			)
		)
	
	try:
		defaultCount = len(defaults)
	except TypeError:
		defaultCount = 0
	
	nonDefaultCount = argCount - defaultCount

	numberingWidth = digitLength(argCount - 1)
	nameWidth = max(map(lambda a : len(a), argNames))
	typeWidth = max(
		map(lambda a : typeLengther(hints, a), argNames[:argCount - defaultCount])
	)

	if defaultCount > 0:
		typeWidthDefaults = max(
			map(lambda a : typeLengther(hints, a),
			argNames[argCount - defaultCount:])
		)
		defaultsWidth = max(map(lambda d : len(str(d)), defaults))
	else:
		typeWidthDefaults = 0
		defaultsWidth = 0

	if typeWidthDefaults > 0 or defaultsWidth > 0:
		defaultsWidthCombined = typeWidthDefaults + 3 + defaultsWidth
		descriptionsWidth = max(
			map(lambda s : len(s), descriptions[:nonDefaultCount])
		)
		descriptionsWidthDefaults = max(
			map(lambda s : len(s), descriptions[nonDefaultCount:])
		)

		nonDefaultWidthTotal = typeWidth + descriptionsWidth
		defaultWidthTotal = defaultsWidthCombined + descriptionsWidthDefaults
		widthDelta = abs(nonDefaultWidthTotal - defaultWidthTotal)

		if nonDefaultWidthTotal > defaultWidthTotal:
			descriptionsWidthDefaults += widthDelta
		elif defaultWidthTotal > nonDefaultWidthTotal:
			descriptionsWidth += widthDelta
		
	s = '\n' # Start with this for padding with the help() builtin
	for i in range(argCount - defaultCount):
		arg = argNames[i]
		hint = typeScrubber(hints, arg)
		s += (
			' ' * indentation
			+ (
				"{: >{:d}d}. {: <{:d}s} : {: <{:d}s} : "
				"{: <{:d}s} :"
			).format(
				i, numberingWidth, arg, nameWidth, hint, typeWidth,
				descriptions[i], descriptionsWidth
			) + (
				" {:s}\n".format(classMemberNames[i]) if isMethod
				else '\n'
			)
		)

	for i in range(argCount - defaultCount, argCount):
		arg = argNames[i]
		hint = typeScrubber(hints, arg)
		defaultValue = defaults[i - nonDefaultCount]

		s += (
			' ' * indentation
			+ (
				"{: >{:d}d}. {: <{:d}s} : {: >{:d}s} = {: <{:d}s} : "
				"{: <{:d}s} :"
			).format(
				i, numberingWidth, arg, nameWidth, hint, typeWidthDefaults,
				str(defaultValue), defaultsWidth, descriptions[i],
				descriptionsWidthDefaults
			) + (
				" {:s}\n".format(classMemberNames[i]) if isMethod
				else '\n'
			)
		)

	return s

