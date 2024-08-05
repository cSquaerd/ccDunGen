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
	f : "function", isMethod : bool = False, indentation : int = 2
) -> str:
	if not hasattr(f, "__code__"):
		print("Error: provided function has no .__code__ element, probably a builtin; Returning...")
		return ""

	if isMethod:
		i_argStart = 1
	else:
		i_argStart = 0
	
	hints = f.__annotations__
	defaults = f.__defaults__
	
	argCount = f.__code__.co_argcount
	argNames = f.__code__.co_varnames[i_argStart:argCount]
	
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
	else:
		typeWidthDefaults = 1

	s = ""
	for i in range(argCount - defaultCount):
		arg = argNames[i]
		hint = typeScrubber(hints, arg)
		s += (
			' ' * indentation
			+ "{: <{:d}d}. {: <{:d}s} : {: <{:d}s} : ".format(
				i, numberingWidth, arg, nameWidth, hint, typeWidth
			) + '\n'
		)

	for i in range(argCount - defaultCount, argCount):
		arg = argNames[i]
		hint = typeScrubber(hints, arg)
		defaultValue = defaults[i - nonDefaultCount]

		s += (
			' ' * indentation
			+ "{: <{:d}d}. {: <{:d}s} : {: <{:d}s} = {: >{:d}s} : ".format(
				i, numberingWidth, arg, nameWidth, hint, typeWidthDefaults,
				str(defaultValue), 10
			) + '\n'
		)

	return s

