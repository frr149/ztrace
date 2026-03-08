"""Parser del XML exportado por xctrace."""

from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass
class Frame:
    name: str
    binary_name: str
    binary_path: str

    @property
    def is_user(self) -> bool:
        """True si el frame pertenece a código del usuario (no sistema)."""
        if self.binary_path.startswith(("/usr/lib/", "/System/")):
            return False
        # Runtime internals linkeados en el binario del usuario
        if self.name.startswith(("__swift_", "swift_", "_swift_", "__objc_", "DYLD-STUB$$")):
            return False
        return True


@dataclass
class Sample:
    weight_ns: int
    frames: list[Frame]


def parse_time_profile(xml_data: str) -> list[Sample]:
    """Parsea el XML de time-profile resolviendo el sistema id/ref."""
    root = ET.fromstring(xml_data)
    registry: dict[str, ET.Element] = {}
    samples: list[Sample] = []

    # Primer paso: registrar todos los elementos con id
    _register_ids(root, registry)

    # Segundo paso: extraer samples
    for row in root.iter("row"):
        weight_ns = _resolve_weight(row, registry)
        backtrace = _resolve_backtrace(row, registry)
        if backtrace is None:
            continue

        frames = _extract_frames(backtrace, registry)
        samples.append(Sample(weight_ns=weight_ns, frames=frames))

    return samples


def _register_ids(element: ET.Element, registry: dict[str, ET.Element]) -> None:
    """Registra recursivamente todos los elementos con atributo id."""
    eid = element.get("id")
    if eid is not None:
        registry[eid] = element
    for child in element:
        _register_ids(child, registry)


def _resolve_ref(element: ET.Element, registry: dict[str, ET.Element]) -> ET.Element:
    """Resuelve un elemento que puede ser un ref a otro."""
    ref = element.get("ref")
    if ref is not None:
        return registry.get(ref, element)
    return element


def _resolve_weight(row: ET.Element, registry: dict[str, ET.Element]) -> int:
    """Extrae el weight en nanosegundos de un row."""
    weight_el = row.find("weight")
    if weight_el is None:
        return 1_000_000  # default 1ms
    weight_el = _resolve_ref(weight_el, registry)
    text = weight_el.text
    if text:
        return int(text)
    return 1_000_000


def _resolve_backtrace(
    row: ET.Element, registry: dict[str, ET.Element]
) -> ET.Element | None:
    """Extrae el backtrace de un row, resolviendo refs."""
    bt = row.find("backtrace")
    if bt is None:
        return None
    return _resolve_ref(bt, registry)


def _extract_frames(
    backtrace: ET.Element, registry: dict[str, ET.Element]
) -> list[Frame]:
    """Extrae los frames de un backtrace, resolviendo refs."""
    frames: list[Frame] = []
    for frame_el in backtrace.findall("frame"):
        frame_el = _resolve_ref(frame_el, registry)
        name = frame_el.get("name", "<unknown>")

        # Resolver binary (puede ser hijo directo o ref)
        binary_el = frame_el.find("binary")
        if binary_el is not None:
            binary_el = _resolve_ref(binary_el, registry)
            binary_name = binary_el.get("name", "<unknown>")
            binary_path = binary_el.get("path", "")
        else:
            binary_name = "<unknown>"
            binary_path = ""

        frames.append(Frame(name=name, binary_name=binary_name, binary_path=binary_path))
    return frames
