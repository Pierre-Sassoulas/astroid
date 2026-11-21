# FormattedValue, JoinedStr.
# +18: <3.12: position: 20:0-20:29
# +17: >=3.12: position: 20:0-20:29
# +16: <3.12: values[0]: Const('Hello World: ')
# +15: >=3.12: values[0]: Const('Hello World: ')
# +14: <3.12: values[0].position: 20:0-20:29
# +13: >=3.12: values[0].position: 20:2-20:15
# +12: <3.12: values[1]: FormattedValue({42.1234:02d})
# +11: >=3.12: values[1]: FormattedValue({42.1234:02d})
# +10: <3.12: values[1].format_spec: JoinedStr(f'02d')
# +9: >=3.12: values[1].format_spec: JoinedStr(f'02d')
# +8: <3.12: values[1].format_spec.position: 20:0-20:29
# +7: >=3.12: values[1].format_spec.position: 20:23-20:27
# +6: <3.12: values[1].position: 20:0-20:29
# +5: >=3.12: values[1].position: 20:15-20:28
# +4: <3.12: values[1].value: Const(42.1234)
# +3: >=3.12: values[1].value: Const(42.1234)
# +2: <3.12: values[1].value.position: 20:16-20:23
# +1: >=3.12: values[1].value.position: 20:16-20:23
f"Hello World: {42.1234:02d}"
# +14: <3.12: position: 35:0-35:17
# +13: >=3.12: position: 35:0-35:17
# +12: <3.12: values[0]: Const('Hello: name=')
# +11: >=3.12: values[0]: Const('Hello: name=')
# +10: <3.12: values[0].position: 35:0-35:17
# +9: >=3.12: values[0].position: 35:2-35:15
# +8: <3.12: values[1]: FormattedValue({name!r})
# +7: >=3.12: values[1]: FormattedValue({name!r})
# +6: <3.12: values[1].position: 35:0-35:17
# +5: >=3.12: values[1].position: 35:9-35:16
# +4: <3.12: values[1].value: Name(name)
# +3: >=3.12: values[1].value: Name(name)
# +2: <3.12: values[1].value.position: 35:10-35:14
# +1: >=3.12: values[1].value.position: 35:10-35:14
f"Hello: {name=}"
