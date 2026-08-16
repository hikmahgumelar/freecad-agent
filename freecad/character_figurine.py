import os

import FreeCAD as App
import FreeCADGui as Gui
import Part


def _fit(doc):
    try:
        Gui.getDocument(doc.Name).activeView().viewAxonometric()
        Gui.getDocument(doc.Name).activeView().fitAll()
    except Exception:
        pass


def _add(doc, name, label, shape):
    old = doc.getObject(name)
    if old is not None:
        doc.removeObject(name)
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    return obj


def create_character_figurine(command):
    """Create a printable stylized figurine inspired by the supplied reference.

    Default overall height is 120 mm. The model is intentionally constructed
    from robust solids rather than photo-dependent mesh reconstruction, so it
    remains editable and exportable from FreeCAD.
    """
    doc = App.ActiveDocument or App.newDocument("CharacterFigurine")
    H = float(command.get("height", 120.0))
    base_d = float(command.get("base_diameter", 46.0))
    base_t = float(command.get("base_thickness", 3.0))
    if H <= 0 or base_d <= 0 or base_t <= 0:
        raise RuntimeError("Character dimensions must be positive")

    # Coordinate system: Z is vertical, centered on the figurine.
    z0 = base_t
    scale = H / 120.0

    def S(v):
        return v * scale

    parts = []

    # Display/print base.
    parts.append(_add(doc, "CharacterBase", "Display base", Part.makeCylinder(base_d / 2, base_t)))

    # Feet and legs.
    for side, x in (("L", -S(8)), ("R", S(8))):
        foot = Part.makeBox(S(15), S(8), S(4), App.Vector(x - S(7.5), -S(4), z0))
        leg = Part.makeCylinder(S(5), S(25), App.Vector(x, 0, z0 + S(4)))
        parts.extend([
            _add(doc, f"Foot{side}", f"Foot {side}", foot),
            _add(doc, f"Leg{side}", f"Leg {side}", leg),
        ])

    # Sandals with raised strap.
    for side, x in (("L", -S(8)), ("R", S(8))):
        sole = Part.makeBox(S(17), S(9), S(2), App.Vector(x - S(8.5), -S(4.5), z0 + S(1)))
        strap = Part.makeBox(S(3), S(9), S(3), App.Vector(x - S(1.5), -S(4.5), z0 + S(3)))
        parts.extend([
            _add(doc, f"Sandal{side}", f"Sandal {side}", sole.fuse(strap)),
        ])

    # Grass-skirt silhouette: a shallow conical frustum.
    skirt = Part.makeCone(S(14), S(18), S(30), App.Vector(0, 0, z0 + S(29)))
    parts.append(_add(doc, "GrassSkirt", "Grass skirt silhouette", skirt))

    # Top/torso.
    torso = Part.makeCone(S(12), S(10), S(28), App.Vector(0, 0, z0 + S(55)))
    parts.append(_add(doc, "Torso", "Black top / torso", torso))

    # Arms, hands.
    for side, x in (("L", -S(12)), ("R", S(12))):
        arm = Part.makeCylinder(S(3.2), S(25), App.Vector(x, 0, z0 + S(55)))
        hand = Part.makeSphere(S(3.4), App.Vector(x, 0, z0 + S(52)))
        parts.extend([
            _add(doc, f"Arm{side}", f"Arm {side}", arm),
            _add(doc, f"Hand{side}", f"Hand {side}", hand),
        ])

    # Neck and head.
    neck = Part.makeCylinder(S(4), S(5), App.Vector(0, 0, z0 + S(82)))
    head = Part.makeSphere(S(9.5), App.Vector(0, 0, z0 + S(96)))
    parts.extend([
        _add(doc, "Neck", "Neck", neck),
        _add(doc, "Head", "Head", head),
    ])

    # Hair mass and ponytail.
    hair = Part.makeSphere(S(10.5), App.Vector(0, S(-1), z0 + S(97)))
    pony = Part.makeCylinder(S(4), S(12), App.Vector(0, S(-8), z0 + S(88)), App.Vector(0, 0, 1))
    parts.extend([
        _add(doc, "Hair", "Hair mass", hair),
        _add(doc, "Ponytail", "Ponytail", pony),
    ])

    # Feathered headpiece: crown band plus six tapered feather forms.
    crown = Part.makeTorus(S(10), S(1.4), App.Vector(0, 0, z0 + S(104)), App.Vector(0, 0, 1), 0, 360, 360)
    parts.append(_add(doc, "HeaddressBand", "Decorative feather headdress band", crown))
    feather_angles = (-55, -33, -15, 15, 33, 55)
    for i, angle in enumerate(feather_angles):
        import math
        a = math.radians(angle)
        dx, dy = math.sin(a), math.cos(a)
        start = App.Vector(dx * S(7), dy * S(7), z0 + S(105))
        direction = App.Vector(dx * S(6), dy * S(6), S(10))
        feather = Part.makeCone(S(2.2), S(0.45), direction.Length, start, direction)
        parts.append(_add(doc, f"Feather{i+1}", f"Headdress feather {i+1}", feather))

    # Simple chest/arm decorative bands and center ornament, all printable solids.
    chest = Part.makeBox(S(12), S(2), S(5), App.Vector(-S(6), -S(10.5), z0 + S(68)))
    parts.append(_add(doc, "ChestOrnament", "Chest ornament", chest))
    for side, x in (("L", -S(13.5)), ("R", S(13.5))):
        band = Part.makeTorus(S(3.8), S(1.2), App.Vector(x, 0, z0 + S(69)), App.Vector(1, 0, 0), 0, 360, 360)
        parts.append(_add(doc, f"ArmBand{side}", f"Decorative arm band {side}", band))

    doc.recompute()
    _fit(doc)

    output_path = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/character-figurine-120mm.FCStd"))
    stl_path = os.path.abspath(command.get("stl_path", "/home/hikmah/projectx/freecad-agent/cad/output/character-figurine-120mm.stl"))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(os.path.dirname(stl_path), exist_ok=True)
    doc.saveAs(output_path)

    try:
        import Mesh
        Mesh.export(parts, stl_path)
    except Exception as exc:
        raise RuntimeError(f"FCStd saved but STL export failed: {exc}")

    return {
        "ok": True,
        "action": "create_character_figurine",
        "document": doc.Name,
        "height": H,
        "base_diameter": base_d,
        "base_thickness": base_t,
        "style": "stylized printable reference-based figurine",
        "output_path": output_path,
        "stl_path": stl_path,
        "parts": [o.Name for o in parts],
    }
