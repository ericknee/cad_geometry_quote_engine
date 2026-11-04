"""Helpers for walking an OpenCascade shape."""

from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS_Shape


def unique_subshapes(shape: TopoDS_Shape, kind: TopAbs_ShapeEnum) -> list[TopoDS_Shape]:
    """Return each face/edge/solid once.

    The explorer returns a shape once per parent, so an edge shared by two faces appears
    twice. We drop repeats with IsSame, using the hash to avoid comparing every pair.
    """
    buckets: dict[int, list[TopoDS_Shape]] = {}
    unique: list[TopoDS_Shape] = []
    explorer = TopExp_Explorer(shape, kind)
    while explorer.More():
        current = explorer.Current()
        bucket = buckets.setdefault(hash(current), [])
        if not any(current.IsSame(seen) for seen in bucket):
            bucket.append(current)
            unique.append(current)
        explorer.Next()
    return unique
