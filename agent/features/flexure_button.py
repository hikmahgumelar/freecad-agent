"""Reusable rectangular imperfect-U flexure button feature.

This module intentionally contains geometry math only. The actual FreeCAD
boolean operations are supplied by the caller so the feature can be reused
across enclosure generators without embedding enclosure-specific coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


Point2D = Tuple[float, float]
Size2D = Tuple[float, float]


@dataclass(frozen=True)
class FlexureButton:
    """Parametric rectangular imperfect-U flexure button.

    ``origin`` is the local coordinate of the inner base of the U. All
    dependent geometry is derived from that local origin, so the actuator pad
    cannot drift with respect to the flexure when the feature is instantiated
    at another enclosure location.
    """

    origin: Point2D
    width: float = 2.0
    length: float = 7.0
    slot: float = 0.5
    rear_bridge: float = 1.0
    pad_size: Size2D = (2.0, 2.0)
    pad_height: float = 0.75

    def __post_init__(self) -> None:
        ox, oy = self.origin
        if self.width <= 0 or self.length <= 0:
            raise ValueError("button width and length must be positive")
        if self.slot <= 0:
            raise ValueError("slot must be positive")
        if self.rear_bridge <= 0:
            raise ValueError("rear_bridge must be positive")
        if self.pad_size[0] <= 0 or self.pad_size[1] <= 0:
            raise ValueError("pad dimensions must be positive")
        if self.pad_height <= 0:
            raise ValueError("pad_height must be positive")
        if self.slot >= self.length:
            raise ValueError("slot must be smaller than button length")
        if self.rear_bridge >= self.length:
            raise ValueError("rear_bridge must be smaller than button length")
        _ = (ox, oy)

    @property
    def button_origin(self) -> Point2D:
        return self.origin

    @property
    def pad_origin(self) -> Point2D:
        """Return pad lower-left corner in local coordinates.

        The pad is centered on the button width and placed at the inner base
        of the U, so its lateral and longitudinal relationship to the
        flexure remains invariant across instances.
        """

        ox, oy = self.origin
        pad_w, pad_l = self.pad_size
        return (
            ox + (self.width - pad_w) / 2.0,
            oy - pad_l,
        )

    @property
    def u_slot_bounds(self) -> tuple[float, float, float, float]:
        """Return the canonical U-slot bounding box.

        Bounds are expressed as ``(x_min, y_min, x_max, y_max)`` using the
        feature's local origin. The slot thickness is immutable per instance.
        """

        ox, oy = self.origin
        return (
            ox - self.slot,
            oy,
            ox + self.width + self.slot,
            oy + self.length,
        )

    def mirrored(self, center_x: float) -> "FlexureButton":
        """Return a horizontally mirrored instance about ``center_x``."""

        ox, oy = self.origin
        mirrored_x = 2.0 * center_x - ox - self.width
        return FlexureButton(
            origin=(mirrored_x, oy),
            width=self.width,
            length=self.length,
            slot=self.slot,
            rear_bridge=self.rear_bridge,
            pad_size=self.pad_size,
            pad_height=self.pad_height,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic parameters for a CAD builder."""

        return {
            "origin": self.origin,
            "width": self.width,
            "length": self.length,
            "slot": self.slot,
            "rear_bridge": self.rear_bridge,
            "pad_size": self.pad_size,
            "pad_height": self.pad_height,
            "pad_origin": self.pad_origin,
            "u_slot_bounds": self.u_slot_bounds,
        }
