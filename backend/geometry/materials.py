"""Materials the engine knows. Prices and rates are PRD baseline data (section 7.2)."""

from pydantic import BaseModel, ConfigDict, Field


class Material(BaseModel):
    # Frozen: a material cannot change while a part is being analyzed or priced.
    model_config = ConfigDict(frozen=True)

    name: str
    density_g_per_cm3: float = Field(gt=0)
    price_per_kg: float = Field(gt=0)  # dollars
    machine_type: str
    # Cents, so money stays an integer until the final dollar output.
    machining_hourly_rate_cents: int = Field(gt=0)

    def mass_kg(self, volume_cm3: float) -> float:
        return volume_cm3 * self.density_g_per_cm3 / 1000


ALUMINUM_6061 = Material(
    name="6061 Aluminum",
    density_g_per_cm3=2.7,
    price_per_kg=5.0,
    machine_type="Haas CNC",
    machining_hourly_rate_cents=10_000,
)

DEFAULT_MATERIAL = ALUMINUM_6061
MATERIALS: dict[str, Material] = {ALUMINUM_6061.name: ALUMINUM_6061}


def get_material(name: str) -> Material:
    """Look a material up by the name stored in a GeometryResult."""
    try:
        return MATERIALS[name]
    except KeyError:
        raise ValueError(f"Unknown material '{name}'. Known: {', '.join(MATERIALS)}") from None
