# Match, MatchValue, MatchSingleton, MatchSequence, MatchMapping,
# MatchClass, MatchStar, MatchOr, MatchAs.
match x:  # position: 3:0-57:12  # subject.position: 3:6-3:7
    # +6: body[0]: Pass(pass)
    # +5: body[0].position: 11:8-11:12
    # +4: guard: Const(True)
    # +3: guard.position: 10:16-10:20
    # +2: pattern: MatchValue(200)
    # +1: pattern.position: 10:9-10:12
    case 200 if True:
        pass
    case True:  # pattern: MatchSingleton(True)  # pattern.position: 12:9-12:13
        pass
    # +8: pattern: MatchSequence([1, 2, *args])
    # +7: pattern.patterns[0]: MatchValue(1)
    # +6: pattern.patterns[0].position: 22:10-22:11
    # +5: pattern.patterns[2]: MatchStar(*args)
    # +4: pattern.patterns[2].name: AssignName(args)
    # +3: pattern.patterns[2].name.position: 22:16-22:21
    # +2: pattern.patterns[2].position: 22:16-22:21
    # +1: pattern.position: 22:9-22:22
    case (1, 2, *args):
        pass
    # +8: pattern: MatchMapping({1: 'Hello', **rest})
    # +7: pattern.keys[0]: Const(1)
    # +6: pattern.keys[0].position: 32:10-32:11
    # +5: pattern.patterns[0]: MatchValue('Hello')
    # +4: pattern.patterns[0].position: 32:13-32:20
    # +3: pattern.position: 32:9-32:29
    # +2: pattern.rest: AssignName(rest)
    # +1: pattern.rest.position: 32:9-32:29
    case {1: "Hello", **rest}:
        pass
    # +8: pattern: MatchClass(Point2d(0, y=0))
    # +7: pattern.cls: Name(Point2d)
    # +6: pattern.cls.position: 42:9-42:16
    # +5: pattern.kwd_patterns[0]: MatchValue(0)
    # +4: pattern.kwd_patterns[0].position: 42:22-42:23
    # +3: pattern.patterns[0]: MatchValue(0)
    # +2: pattern.patterns[0].position: 42:17-42:18
    # +1: pattern.position: 42:9-42:24
    case Point2d(0, y=0):
        pass
    # +4: pattern: MatchOr(200 | 300)
    # +3: pattern.patterns[0]: MatchValue(200)
    # +2: pattern.patterns[0].position: 48:9-48:12
    # +1: pattern.position: 48:9-48:18
    case 200 | 300:
        pass
    # +6: pattern: MatchAs(200 as c)
    # +5: pattern.name: AssignName(c)
    # +4: pattern.name.position: 56:9-56:17
    # +3: pattern.pattern: MatchValue(200)
    # +2: pattern.pattern.position: 56:9-56:12
    # +1: pattern.position: 56:9-56:17
    case 200 as c:
        pass
