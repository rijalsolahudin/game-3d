"""Konfigurasi ekspor chunk: semua konstanta tuning ada di sini (general.md: tanpa angka ajaib)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

SCHEMA_VERSION = 1
COORDINATE_SYSTEM = {"crs": "EPSG:32749 (UTM 49S) minus origin", "axes": "x=east, z=north, y=up", "unit": "m"}
ID_HASH_LEN = 12  # panjang hex sha1 WKT sumber pada id bangunan pelengkap
AREA_STAT_PREFIX = "areas_"

# Sumber data + atribusi untuk kredit game (NFR-06). SATU sumber teks: dipakai index.json dan README (dijaga test).
# Keputusan pemilik produk: Google Open Buildings v3 (dual CC BY 4.0 / ODbL) diatribusikan sebagai ODbL 1.0,
# konsisten dengan data OSM gabungan. Untuk mengganti cukup ubah entri di sini dan blok atribusi di README.
ODBL_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
SOURCE_INFO: dict[str, dict[str, str]] = {
    "osm": {"name": "OpenStreetMap", "license": "ODbL 1.0", "license_url": ODBL_URL,
            "attribution": "Map data (c) OpenStreetMap contributors, available under the Open Database License "
                           "(https://www.openstreetmap.org/copyright)."},
    "google": {"name": "Google Open Buildings v3 (via VIDA, source.coop)", "license": "ODbL 1.0", "license_url": ODBL_URL,
               "attribution": "Building footprints: Google Open Buildings v3, via VIDA (source.coop), "
                              f"licensed under ODbL 1.0 ({ODBL_URL})."},
    "microsoft": {"name": "Microsoft Global ML Building Footprints (via VIDA, source.coop)", "license": "ODbL 1.0",
                  "license_url": ODBL_URL,
                  "attribution": "Building footprints: Microsoft Global ML Building Footprints, via VIDA (source.coop), "
                                 f"licensed under ODbL 1.0 ({ODBL_URL})."},
}

# Lebar default (m) bila tag `width` tidak ada/tidak valid. Tipe `*_link` memakai tipe induknya.
ROAD_WIDTH_M: dict[str, float] = {
    "motorway": 12.0, "trunk": 10.0, "primary": 9.0, "secondary": 7.0, "tertiary": 6.0,
    "unclassified": 4.0, "residential": 4.0, "living_street": 4.0, "service": 3.0, "road": 4.0,
    "track": 2.5, "pedestrian": 3.0, "cycleway": 2.0, "bridleway": 2.0, "path": 1.5, "footway": 1.5,
    "steps": 1.5, "corridor": 1.5,
}
ROAD_WIDTH_FALLBACK_M = 3.0
# highway yang belum ada di dunia nyata: dikecualikan dan DILAPORKAN (bukan dibuang diam-diam)
ROAD_EXCLUDED_KINDS = frozenset({"proposed", "construction", "abandoned", "razed", "platform"})

WATERWAY_WIDTH_M: dict[str, float] = {
    "river": 8.0, "stream": 2.0, "canal": 4.0, "ditch": 1.5, "drain": 1.5, "brook": 2.0,
}
WATERWAY_WIDTH_FALLBACK_M = 2.0

# key OSM yang menjadi polygon area (kategori = nama key); air ditangani terpisah
AREA_KEYS = ("landuse", "natural", "leisure")
WATER_NATURAL = "water"
WATER_WATERWAY = "riverbank"

# tinggi default bangunan (m) menurut tag building; sisanya menurut luas footprint
HEIGHT_BY_KIND_M: dict[str, float] = {
    "house": 4.5, "residential": 4.5, "detached": 4.5, "static_caravan": 2.8, "hut": 2.5, "shed": 2.8,
    "garage": 3.0, "garages": 3.0, "carport": 2.8, "roof": 3.0, "farm_auxiliary": 3.0, "barn": 5.0,
    "commercial": 5.0, "retail": 5.0, "school": 5.5, "industrial": 6.0, "warehouse": 6.0,
    "mosque": 10.0, "church": 9.0, "temple": 8.0, "religious": 8.0,
}
# (batas atas luas m2, tinggi m), dipakai bila tipe tidak dikenal; luas di atas tabel -> HEIGHT_LARGE_M
HEIGHT_BY_AREA_M: tuple[tuple[float, float], ...] = ((30.0, 3.0), (150.0, 4.5))
HEIGHT_LARGE_M = 6.0


@dataclass(frozen=True)
class ExportConfig:
    chunk_size_m: int = 256
    coord_decimals: int = 2          # presisi koordinat lokal (0.01 m)
    boundary_margin_m: float = 25.0  # jalan/air/landuse dipotong ke batas + margin ini
    floor_height_m: float = 3.0      # building:levels x ini bila tag height tidak ada
    height_min_m: float = 1.0
    height_max_m: float = 200.0
    width_min_m: float = 0.3
    width_max_m: float = 40.0
    default_tier: str = "C"
    # dedup + filter footprint pelengkap (Google/Microsoft)
    google_min_confidence: float = 0.70   # Microsoft tanpa skor: lolos filter confidence, tetap kena filter lain
    supp_min_area_m2: float = 15.0
    supp_max_area_m2: float = 3000.0
    supp_min_rectangularity: float = 0.55  # luas / luas persegi panjang terkecil
    supp_max_aspect: float = 6.0           # sisi panjang / sisi pendek persegi panjang terkecil
    overlap_ratio_max: float = 0.10        # irisan / luas terkecil >= ini = bangunan yang sama
    overlap_area_max_m2: float = 4.0       # luas irisan absolut >= ini juga ditolak (mesh tidak boleh saling tembus)
    min_piece_area_m2: float = 0.01        # sisa polygon hasil potong chunk yang lebih kecil dibuang (dilaporkan)

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_CONFIG = ExportConfig()
