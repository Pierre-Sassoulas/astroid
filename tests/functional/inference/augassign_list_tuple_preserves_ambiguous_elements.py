def choice(flag):
    if flag:
        return 1
    return 2
values = [0]
values += (choice(True), 3)
# +4: inferred: List([0, Unknown.Unknown(), 3])
# +3: inferred.elts[0].value: 0
# +2: inferred.elts[1].inferred: Uninferable
# +1: inferred.elts[2].value: 3
values
