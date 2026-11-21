# +6: handlers[0].statement().name.inferred: ExceptionInstance(builtins.ExceptionGroup)
# +5: handlers[0].statement().name.inferred.getattr(exceptions)[0]: Tuple(ExceptionInstance(builtins.ValueError))
# +4: handlers[0].statement().name.inferred.getattr(exceptions)[0].elts[0].pytype(): 'builtins.ValueError'
# +3: handlers[1].statement().name.inferred: ExceptionInstance(builtins.ExceptionGroup)
# +2: handlers[1].statement().name.inferred.getattr(exceptions)[0]: Tuple(ExceptionInstance(builtins.TypeError))
# +1: handlers[1].statement().name.inferred.getattr(exceptions)[0].elts[0].pytype(): 'builtins.TypeError'
try:
    raise ExceptionGroup("group", [ValueError(654), TypeError(10)])
except* ValueError as ve:
    print(e.exceptions)
except* TypeError as te:
    print(e.exceptions)
else:
    sys.exit(127)
finally:
    sys.exit(0)
