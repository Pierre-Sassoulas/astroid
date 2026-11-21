# Assert, Break, Continue, Global, Nonlocal, Pass, Raise, Return, Expr.
# +5: fail: Const('Some message')
# +4: fail.position: 7:13-7:27
# +3: position: 7:0-7:27
# +2: test: Const(True)
# +1: test.position: 7:7-7:11
assert True, "Some message"
break  # position: 8:0-8:5
continue  # position: 9:0-9:8
global var  # position: 10:0-10:10
nonlocal var  # position: 11:0-11:12
pass  # position: 12:0-12:4
# +5: cause: Name(ex)
# +4: cause.position: 18:21-18:23
# +3: exc: Name(Exception)
# +2: exc.position: 18:6-18:15
# +1: position: 18:0-18:23
raise Exception from ex
return 42  # position: 19:0-19:9  # value: Const(42)  # value.position: 19:7-19:9
# +4: parent: Expr(var)
# +3: parent.position: 24:0-24:3
# +2: parent.value: Name(var)
# +1: parent.value.position: 24:0-24:3
var
