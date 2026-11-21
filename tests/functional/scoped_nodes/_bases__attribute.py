class A(object): pass
class B(object): pass
class C(A, B): pass
# +4: getattr(__bases__)[0]: Tuple(ClassDef(_bases__attribute.C))
# +3: getattr(__bases__)[0].elts: [ClassDef(_bases__attribute.C)]
# +2: getattr(__bases__)[0].elts[0]: ClassDef(_bases__attribute.C)
# +1: getattr(__bases__)[0].elts[0].name: 'C'
class D(C): pass
