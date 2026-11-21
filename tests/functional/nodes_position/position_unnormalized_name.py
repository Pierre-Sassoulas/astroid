# No position info when the name token never matches ``node.name``.
#
# ``node.name`` is the NFKC-normalized identifier while ``tokenize``
# yields the raw source spelling (here the ``fi`` ligature), so the
# name token is never matched and no position can be computed.
class ﬁ:  # name: 'fi'  # position: 6:0-7:7
    ...
