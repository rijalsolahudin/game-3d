"""Render laporan audit Markdown dari hasil osm.audit.run.

Deterministik, tanpa nama/data pribadi. Setiap klaim diturunkan dari data `res` atau dicetak bersyarat.
"""
from __future__ import annotations

from osm.geom import CHUNK_M
from osm.network import EDGE_MARGIN_M, GAP_MAX_M
from osm.parse import CATEGORIES
from osm.stats import MIN_BUILDING_AREA_M2

LOW_COVERAGE_PCT = 30.0    # chunk dengan cakupan di bawah ini (dan cukup padat) ditandai
MIN_REF_FOR_FLAG = 20      # jumlah bangunan pembanding minimum agar chunk ditandai
LONG_DEADEND_M = 200.0     # dead-end lebih panjang dari ini dianggap mencurigakan
ADEQUATE_COVERAGE_PCT = 80.0   # di bawah ini footprint bangunan dinilai belum cukup
DOMINANT_SHARE = 0.9       # tipe building dominan bila porsinya >= ini
PATH_LIKE = ("path", "track", "footway", "service", "steps", "cycleway")
# kategori lahan/alam yang dampaknya dijelaskan bila kosong: kategori -> (judul, dampak)
VISUAL_IMPACT = {
    "landuse": ("Tata guna lahan (`landuse`: sawah, kebun, hutan, pekarangan)",
                "tidak ada tekstur/zonasi lahan; luasan harus diturunkan dari citra referensi atau digitasi"),
    "natural": ("Alam (`natural`: air, hutan/bambu, semak, pohon)",
                "tidak ada vegetasi/badan air terpetakan; pohon perlu penebaran procedural"),
    "leisure": ("Rekreasi (`leisure`: lapangan, taman)", "lapangan/taman harus dicari lewat survei"),
    "amenity": ("Fasilitas (`amenity`: masjid, sekolah, balai desa, pasar, makam)",
                "landmark dan POI Tier A harus dikumpulkan lewat survei lapangan"),
}


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def _local(res: dict, x: float, y: float) -> str:
    ox, oy = res["origin_utm"]
    return f"({x - ox:.0f}, {y - oy:.0f})"


def _count(res: dict, cat: str) -> int:
    return sum(res["counts"].get(cat, {}).values())


def _road_km(res: dict) -> float:
    return sum(v["km"] for v in res["road_km"].values())


def _cov_range(ref: dict) -> tuple[float, float]:
    vals = [r["coverage_pct"] for r in ref["sensitivity"] if r["coverage_pct"] is not None]
    return min(vals), max(vals)


def _boundary_label(b: dict) -> str:
    if not b["provisional"]:
        return "resmi + buffer"
    detail = f"{b['method']}, radius {b['radius_m']:g} m" if b.get("radius_m") else b.get("method", "")
    return f"SEMENTARA ({detail})"


def _types(d: dict) -> str:
    return ", ".join(f"{k} {v}" for k, v in d.items())


def _is_coverage_low(res: dict) -> bool | None:
    ref = res.get("reference")
    return None if not ref else ref["summary"]["coverage_pct"] < ADEQUATE_COVERAGE_PCT


def _header(res: dict) -> str:
    m, b = res["meta"], res["boundary"]
    return f"""# Audit Data OSM - Desa Tumanggal (GAME-6)

Dihasilkan otomatis oleh `scripts/audit_osm.py` dari raw `data/raw/osm/{m['raw_file']}`; jangan edit manual.

| Item | Nilai |
|---|---|
| Tanggal unduh | {m['downloaded_at']} |
| Timestamp basis OSM (Overpass) | {m['osm_base_timestamp']} |
| Sumber | {m['source']} ({m['endpoint']}) |
| Elemen mentah | {m['element_counts']['total']} (node {m['element_counts']['node']}, way {m['element_counts']['way']}, relation {m['element_counts']['relation']}) |
| Batas audit | {_boundary_label(b)}, luas {b['area_km2']} km2 |
| bbox query (S,W,N,E) | {m['bbox_swne']} |
| Lisensi | {m['license']}, {m['attribution']} |
| SHA-256 raw (terverifikasi) | `{m['raw_sha256'][:16]}...` |

Statistik jalan dihitung setelah clip ke batas; bangunan dihitung bila titik wakilnya di dalam batas.
Semua angka di UTM 49S (EPSG:32749) lewat `geo/projection.py`; koordinat lokal (x timur, z utara, meter) relatif
origin usulan `data/origin.json`; chunk {CHUNK_M:.0f} m berID `"{{x}}_{{z}}"`.

"""


def _summary(res: dict) -> str:
    bl, net = res["buildings"], res["network"]
    ref = res.get("reference")
    top_type, top_n = max(bl["by_type"].items(), key=lambda kv: kv[1]) if bl["by_type"] else ("-", 0)
    generic = (f"; {top_n / bl["count"]:.1%} bertipe `building={top_type}`" if bl["count"] and top_n / bl["count"] >= DOMINANT_SHARE
               else f"; tipe: {_types(bl['by_type'])}")
    lines = [
        "## 1. Ringkasan\n",
        f"- Bangunan OSM: **{bl['count']}** footprint, total {bl['total_area_m2']:.0f} m2 "
        f"(median {bl['median_area_m2']:.0f} m2){generic}.",
        f"- Jalan: **{_road_km(res):.1f} km** pada {net['roads']} way (tipe: {', '.join(res['road_km'])}; "
        f"bernama {sum(net['named'].values())} way; atribut surface {net['attrs']['surface']}, width {net['attrs']['width']}).",
    ]
    if ref:
        s = ref["summary"]
        lo, hi = _cov_range(ref)
        lines.append(
            f"- **Perkiraan bangunan yang sudah punya footprint di OSM: sekitar {s['coverage_pct']:.0f}% "
            f"(kisaran {lo:.0f}% sampai {hi:.0f}% menurut ambang confidence)**, dibandingkan Google Open Buildings v3 + "
            f"Microsoft ML ({s['n_ref']} footprint, confidence >= {ref['min_confidence']}). "
            f"Artinya kira-kira {100 - s['coverage_pct']:.0f}% bangunan belum ada di OSM.")
    rp = res["road_proximity"]
    lines.append(f"- {rp['pct']:.0f}% bangunan OSM berjarak > {rp['threshold_m']:.0f} m dari jalan OSM mana pun "
                 f"({rp['count']} bangunan).")
    lines.append("- Tata guna lahan dan POI di OSM: " + ", ".join(
        f"{k} {_count(res, k)}" for k in ("landuse", "natural", "waterway", "leisure", "amenity", "place")) + ".")
    low = _is_coverage_low(res)
    if low is None:
        lines.append("- Kesimpulan kelengkapan bangunan: butuh data pembanding.\n")
    elif low:
        lines.append(f"- Kesimpulan: cakupan bangunan di bawah {ADEQUATE_COVERAGE_PCT:.0f}%; OSM saja **belum cukup** untuk "
                     "peta yang mirip aslinya. Perlu pelengkapan sebelum masuk pipeline (bagian 7).\n")
    else:
        lines.append("- Kesimpulan: cakupan bangunan memadai; periksa jalan dan lahan (bagian 4 dan 6).\n")
    return "\n".join(lines) + "\n"


def _stats(res: dict) -> str:
    out = ["## 2. Statistik per kategori\n"]
    rows = [[c, sum(v.values()), ", ".join(f"{k}: {n}" for k, n in v.items())] for c, v in res["counts"].items()]
    out.append(_table(["Kategori", "Jumlah elemen (beririsan batas)", "Rincian nilai tag"], rows))
    empty = [c for c in CATEGORIES if c not in res["counts"]]
    out.append("Kategori yang diekspor tetapi kosong dalam batas: " + (", ".join(empty) or "tidak ada") + ".\n")
    out.append("### Panjang jalan per tipe (di dalam batas)\n")
    out.append(_table(["highway", "Way", "Panjang (km)"],
                      [[k, v["ways"], v["km"]] for k, v in res["road_km"].items()]
                      + [["**total**", sum(v["ways"] for v in res["road_km"].values()),
                          f"**{_road_km(res):.3f}**"]]))
    out.append("Waterway: " + (", ".join(f"{k} {v} km" for k, v in res["waterway_km"].items()) or "tidak ada") + ".\n")
    bl = res["buildings"]
    out.append("### Bangunan\n")
    out.append(f"- Jumlah {bl['count']}, luas footprint total {bl['total_area_m2']:.0f} m2 "
               f"({bl['total_area_m2'] / 1e4:.2f} ha), median {bl['median_area_m2']:.0f} m2.")
    out.append("- Tipe `building=`: " + _types(bl["by_type"]) + ".")
    out.append(f"- Bertag `name`: {bl['with_name']}; bertag `addr:*`: {bl['with_addr']} "
               f"(NFR-07: nama/alamat tidak dicantumkan di laporan; bangunan pribadi berlabel generik).")
    out.append(f"- Bertag `building:levels`: {bl['with_levels']}; `roof:shape`: {bl['with_roof']}.")
    out.append(f"- Footprint < {MIN_BUILDING_AREA_M2:g} m2 (janggal): {bl['tiny_lt_min']}"
               + (f" ({', '.join('way/' + i.split('/')[1] for i in bl['tiny_ids'])})" if bl["tiny_ids"] else "") + ".")
    if res["skipped_no_geometry"]:
        out.append(f"- Elemen bertag tanpa geometri yang bisa dirakit (dilaporkan, tidak dibuang diam-diam): "
                   f"{len(res['skipped_no_geometry'])}.")
    out.append("")
    out.append(f"### Sebaran bangunan OSM per chunk {CHUNK_M:.0f} m\n")
    out.append("Tabel lengkap gabungan dengan pembanding ada di bagian 3. Ringkas: "
               f"{len(bl['per_chunk'])} chunk berisi bangunan OSM; terpadat: " + ", ".join(
                   f"`{k}` ({n})" for k, n in sorted(bl["per_chunk"].items(), key=lambda kv: (-kv[1], kv[0]))[:5]) + ".\n")
    return "\n".join(out) + "\n"


def _completeness(res: dict) -> str:
    out = ["## 3. Perkiraan kelengkapan footprint bangunan\n"]
    ref = res.get("reference")
    if not ref:
        out.append("Data pembanding belum diunduh (`scripts/fetch_open_buildings.py`); estimasi tidak tersedia.\n")
        return "\n".join(out)
    s, rm = ref["summary"], ref["meta"]
    lo, hi = _cov_range(ref)
    lp_pct = 100 * s["n_osm"] / s["lincoln_petersen_total"] if s["lincoln_petersen_total"] else None
    area_cov = 100 - 100 * s["ref_missing_area_m2"] / s["ref_total_area_m2"] if s["ref_total_area_m2"] else None
    out.append(f"""**Metode.** Tidak ada survei lapangan, sehingga dipakai proxy otomatis: footprint OSM dibandingkan dengan
footprint hasil deteksi citra satelit (Google Open Buildings v3 + Microsoft Global ML Building Footprints, gabungan VIDA di
source.coop; diunduh {rm['download_date']}, {rm['count']} footprint di bbox sebelum filter). Pada audit ini pembanding hanya
dibandingkan dan tidak digabung ke data OSM. Lisensi: {rm['license']}. Google v3 dipakai pada confidence >= {ref['min_confidence']}
(rekomendasi Google; Microsoft tidak punya skor). Dua footprint dianggap bangunan yang sama bila irisan >= {ref['match_overlap']:.0%} dari
luas yang terkecil. Baris pembanding divalidasi satu per satu: {ref['rows_invalid']} dari {ref['rows_total']} baris ditolak karena tidak valid.

| Metrik | Nilai |
|---|---|
| Footprint OSM (dalam batas) | {s['n_osm']} |
| Footprint pembanding (dalam batas, filter confidence) | {s['n_ref']} ({_types(s['ref_by_source'])}) |
| Pembanding yang tertutup footprint OSM | {s['ref_covered_by_osm']} |
| **Cakupan OSM terhadap pembanding (jumlah)** | **{s['coverage_pct']}%** |
| Cakupan berdasar luas | {'-' if area_cov is None else f'{area_cov:.1f}%'} ({s['ref_total_area_m2']:.0f} m2 pembanding, {s['ref_missing_area_m2']:.0f} m2 belum ada di OSM) |
| Footprint OSM yang terkonfirmasi pembanding | {s['osm_confirmed_by_ref']} ({s['ref_recall_pct']}% dari footprint OSM) |
| Footprint OSM tanpa pasangan pembanding | {s['osm_only']} |
| Estimasi alternatif total bangunan (Lincoln-Petersen) | {s['lincoln_petersen_total']} (OSM = {'-' if lp_pct is None else f'{lp_pct:.0f}%'}) |

Estimasi alternatif Lincoln-Petersen (n_osm x n_ref / cocok) mengasumsikan dua sumber saling bebas; asumsi itu
cenderung optimistis karena bangunan yang sulit dideteksi citra juga cenderung belum dipetakan di OSM. Ia dicantumkan
sebagai pembanding, bukan batas bawah.

Sensitivitas terhadap ambang confidence Google:

""")
    out.append(_table(["Ambang confidence", "Footprint pembanding", "Cakupan OSM (%)", "Estimasi alternatif (LP)"],
                      [[r["min_conf"], r["n_ref"], r["coverage_pct"], r["lincoln_petersen_total"]] for r in ref["sensitivity"]]))
    out.append(f"""**Cara membaca dan batasan.** Cakupan jumlah tidak sama dengan cakupan sebenarnya: (a) pembanding punya
false positive (atap seng, gudang, kandang, bayangan) dan memecah satu bangunan menjadi beberapa footprint, yang menaikkan
penyebut; (b) pencocokan memakai irisan terhadap luas yang terkecil, sehingga satu bangunan OSM bisa menutup beberapa
footprint pembanding yang terpecah dan menaikkan hitungan "tertutup" (jumlah tertutup bisa melebihi jumlah footprint OSM);
(c) bangunan kecil/tertutup pohon luput dari pembanding. Cakupan menurut ambang confidence berkisar {lo:.0f}% sampai {hi:.0f}%,
artinya sekitar {100 - hi:.0f}% sampai {100 - lo:.0f}% bangunan belum ada di OSM. Angka pasti baru bisa didapat dari
survei/pencocokan manual pada sampel chunk.

""")
    out.append(f"### Per chunk {CHUNK_M:.0f} m (OSM vs pembanding)\n")
    out.append(f"Chunk bertanda `!` = cakupan < {LOW_COVERAGE_PCT:.0f}% dengan >= {MIN_REF_FOR_FLAG} footprint pembanding "
               "(prioritas pelengkapan). Kolom \"Tertutup OSM\" menghitung footprint pembanding (lihat catatan (b)).\n")
    rows = []
    for r in sorted(ref["per_chunk"], key=lambda r: tuple(int(p) for p in r["chunk"].split("_"))):
        flag = "!" if _flagged(r) else ""
        rows.append([f"`{r['chunk']}`", r["osm"], r["ref"], r["ref_covered"],
                     "-" if r["coverage_pct"] is None else r["coverage_pct"], flag])
    out.append(_table(["Chunk", "OSM", "Pembanding", "Tertutup OSM", "Cakupan %", "Prioritas"], rows))
    return "\n".join(out) + "\n"


def _flagged(r: dict) -> bool:
    return r["coverage_pct"] is not None and r["coverage_pct"] < LOW_COVERAGE_PCT and r["ref"] >= MIN_REF_FOR_FLAG


def _roads(res: dict) -> str:
    net = res["network"]
    out = ["## 4. Jalan dan gang: hilang atau janggal\n"]
    out.append(f"- Way jalan: {net['roads']}; komponen terhubung: **{len(net['components'])}** "
               f"({', '.join(str(c['ways']) + ' way / ' + str(c['km']) + ' km' for c in net['components'])}; "
               "panjang di dalam batas).")
    for c in net["components"][1:]:
        out.append(f"  - Komponen terpisah ({c['sample']}; {c['ways']} way, tipe {_types(c['types'])}) berjarak "
                   f"{c['min_dist_to_main_m']} m dari jaringan utama tanpa simpul bersama: ruas penghubung kemungkinan "
                   "belum dipetakan, atau terhubung lewat bagian di luar batas buatan.")
    out.append(f"- Nama: {sum(net['named'].values())} dari {net['roads']} way bernama; tanpa nama: {_types(net['unnamed']) or 'tidak ada'}.")
    out.append("- Atribut (jumlah way yang punya): " + ", ".join(f"`{k}` {v}" for k, v in net["attrs"].items()) + ".")
    absent = [t for t in PATH_LIKE if t not in res["road_km"]]
    if absent:
        out.append("- Tipe `highway` yang tidak ada di OSM dalam batas: " + ", ".join(f"`{t}`" for t in absent)
                   + " (gang kecil/jalan setapak/akses kebun berkurang pemetaannya).")
    rp = res["road_proximity"]
    out.append(f"- **{rp['count']} bangunan OSM ({rp['pct']}%) > {rp['threshold_m']:.0f} m dari jalan OSM terdekat**: "
               "akses ke rumah-rumah ini tidak terpetakan.")
    out.append(f"- Persilangan jalan tanpa simpul (bukan jembatan/terowongan): {len(net['crossings'])}.")
    out.append(f"\n### Dead-end ({len(net['dead_ends'])}) dan kandidat celah ({len(net['gaps'])})\n")
    out.append(f"Dead-end = ujung way yang tidak dipakai way lain, di dalam batas (di luar {EDGE_MARGIN_M:g} m dari tepi), "
               f"tanpa jalan lain dalam {GAP_MAX_M:g} m. Kandidat celah = ujung yang berada <= {GAP_MAX_M:g} m dari jalan lain "
               "tetapi tidak berbagi simpul (seharusnya tersambung). Koordinat lokal (x timur, z utara) relatif origin.\n")
    rows = [[d["way"], d["highway"], d["len_m"], _local(res, d["x"], d["y"]), "-"] for d in net["dead_ends"]]
    rows += [[d["way"], d["highway"], d["len_m"], _local(res, d["x"], d["y"]),
              f"celah {d['gap_m']} m ke {d['near_way']}"] for d in net["gaps"]]
    out.append(_table(["Way", "highway", "Panjang way (m)", "Ujung (x, z) m", "Catatan"], rows))
    longs = [d for d in net["dead_ends"] if d["len_m"] > LONG_DEADEND_M]
    out.append(f"Dead-end pada jalan permukiman pedesaan sebagian wajar (gang buntu). Yang mencurigakan adalah way lebih "
               f"panjang dari {LONG_DEADEND_M:g} m yang berhenti di tengah area: {len(longs)} dead-end, "
               + (", ".join(sorted({d['way'] for d in longs})) or "tidak ada") + ", serta kandidat celah di atas.\n")
    return "\n".join(out) + "\n"


def _suspicious_areas(res: dict) -> str:
    out = ["## 5. Area mencurigakan (tanpa bangunan OSM padahal ada bangunan)\n"]
    ref = res.get("reference")
    if not ref:
        return "\n".join(out) + "Butuh data pembanding.\n"
    o = ref["occupancy"]
    out.append(f"Sel {ref['cell_m']:.0f} m x {ref['cell_m']:.0f} m di dalam batas: total {o['cells']}; berisi bangunan OSM {o['osm']}; "
               f"berisi bangunan pembanding {o['ref']}; **hanya pembanding (OSM kosong) {o['ref_only']}**; "
               f"kosong di keduanya {o['empty_both']} (kemungkinan sawah/kebun/hutan/sungai, wajar tanpa bangunan).\n")
    out.append(f"Klaster sel dengan bangunan pembanding tidak tercakup OSM terbanyak "
               f"(sepuluh teratas dari {len(ref['missing_cells'])} sel):\n")
    out.append(_table(["Pusat sel (x, z) m dari origin", "Footprint pembanding belum di OSM"],
                      [[f"({c['local_x_m']}, {c['local_z_m']})", c["missing"]] for c in ref["missing_cells"][:10]]))
    flagged = [r for r in ref["per_chunk"] if _flagged(r)]
    out.append(f"Chunk dengan cakupan < {LOW_COVERAGE_PCT:.0f}% dan >= {MIN_REF_FOR_FLAG} footprint pembanding: "
               f"{len(flagged)} chunk ({', '.join('`' + r['chunk'] + '`' for r in flagged) or '-'}). "
               f"Footprint pembanding yang belum tertutup OSM: {_missing(ref)}.\n")
    return "\n".join(out) + "\n"


def _missing(ref: dict) -> int:
    return ref["summary"]["n_ref"] - ref["summary"]["ref_covered_by_osm"]


def _visual(res: dict) -> str:
    out = ["## 6. Yang hilang untuk kemiripan visual\n"]
    vm = {k: v for k, v in res["visual_missing"].items() if v}
    out.append("Per kategori, nilai tag lazim di desa Jawa yang tidak ada satu pun di OSM (dalam batas):\n")
    out.append(_table(["Kategori", "Jumlah elemen", "Nilai tag yang tidak ada"],
                      [[k, _count(res, k), ", ".join(v)] for k, v in vm.items()]))
    out.append("Dampak (hanya kategori yang kosong atau kurang):\n")
    for cat, (title, impact) in VISUAL_IMPACT.items():
        if cat in vm and _count(res, cat) == 0:
            out.append(f"- **{title}**: nol di OSM; {impact}.")
    ww = res["visual_missing"].get("waterway", [])
    if ww:
        out.append(f"- **Waterway**: {_count(res, 'waterway')} elemen ({_types(res['counts'].get('waterway', {})) or 'tidak ada'}); "
                   f"tidak ada: {', '.join(ww)}; saluran kecil/irigasi perlu dilengkapi.")
    pl = res["visual_missing"].get("place", [])
    if pl:
        out.append(f"- **Nama tempat**: `place` hanya {_types(res['counts'].get('place', {})) or 'tidak ada'}; tidak ada: {', '.join(pl)}.")
    bl = res["buildings"]
    if not bl["with_levels"] and not bl["with_roof"]:
        out.append("- **Atribut bangunan**: tidak ada `building:levels` maupun `roof:shape`; tinggi dan atap harus ditebak.")
    out.append("")
    return "\n".join(out) + "\n"


def _recommend(res: dict) -> str:
    ref = res.get("reference")
    b = res["boundary"]
    rp = res["road_proximity"]
    net = res["network"]
    low = _is_coverage_low(res)
    out = ["## 7. Rekomendasi\n"]
    items: list[str] = []
    if low:
        cov = ref["summary"]["coverage_pct"]
        items.append(
            f"**Bangunan (P0).** Cakupan ~{cov:.0f}%: lengkapi footprint untuk tier C (procedural dari footprint). "
            f"{_missing(ref)} footprint pembanding belum ada di OSM. Keputusan pemilik produk: footprint Google/Microsoft dipakai "
            "sebagai layer pelengkap di game (ADR-0003, PR docs #14); simpan sebagai layer sumber terpisah dengan jejak sumber dan "
            "lisensi, dedup terhadap OSM, dan bersihkan false positive (atap/gudang), footprint terpecah, dan bentuk tidak kotak. "
            "Impor ke OSM (RapiD/MapWithAI) bersifat opsional dan harus mengikuti panduan impor OSM.")
    absent = [t for t in PATH_LIKE if t not in res["road_km"]]
    if rp["count"] or absent or len(net["components"]) > 1 or net["gaps"]:
        items.append(
            f"**Jalan dan gang (P0).** Fokus: akses ke {rp['count']} bangunan yang jauh dari jalan, "
            f"{len(net['components']) - 1} komponen jaringan terpisah, {len(net['gaps'])} kandidat celah, dan dead-end panjang "
            "(bagian 4). Digitasi dari survei, Mapillary (CC BY-SA, perlu atribusi dan berbagi-serupa), dan tracing "
            "**hanya dari layer imagery yang disetujui editor OSM** (lisensinya mengizinkan tracing untuk OSM); citra lain "
            "dilarang untuk tracing dan, sesuai NFR-06, citra berlisensi terbatas hanya referensi modeling, bukan tekstur. "
            "Beri `name` bila diketahui dari pemerintah desa (nama jalan umum, bukan nama pribadi), serta `surface` dan `width`.")
    if _count(res, "landuse") == 0 or _count(res, "natural") == 0:
        items.append("**Landuse dan alam (P1).** Digitasi poligon sawah, kebun, hutan/bambu, dan pekarangan "
                     "(`landuse=farmland/orchard/forest/residential`, `natural=wood/scrub`) dengan aturan citra yang sama seperti jalan; "
                     "tanpa ini lahan tidak punya zonasi.")
    if res["visual_missing"].get("waterway"):
        items.append("**Sungai kecil dan irigasi (P1).** Tambah `waterway=stream/ditch/canal`; lebar kira-kira dari DEM dan survei.")
    if _count(res, "amenity") == 0:
        items.append("**Landmark dan POI Tier A (P1).** Survei lapangan (masjid, balai desa, sekolah, makam, lapangan, warung): "
                     "titik GPS dan foto di `pipeline/data/reference/<slug>/` tanpa data pribadi (NFR-07). Balai desa juga "
                     "menentukan origin final.")
    if not res["buildings"]["with_levels"]:
        items.append("**Atribut bangunan (P2).** `building:levels`, tipe atap, material hanya untuk Tier A/B; Tier C cukup default per kluster.")
    if b["provisional"]:
        items.append("**Batas resmi (P0, di luar task ini).** Audit memakai batas sementara; ulangi `fetch_osm.py` dan "
                     "`audit_osm.py` setelah batas resmi tersedia.")
    need = bool(items)
    out.append(("**Perlu pelengkapan/digitasi sebelum data masuk pipeline? YA.**" if need
                else "**Perlu pelengkapan/digitasi sebelum data masuk pipeline? Tidak ada temuan yang mewajibkan.**") + "\n")
    out.append("Prioritas (tinggi ke rendah):\n")
    out += [f"{i}. {t}" for i, t in enumerate(items, 1)]
    out.append("\nSemua citra satelit/foto hanya referensi modeling (NFR-06); survei lapangan adalah sumber utama landmark dan POI.\n")
    return "\n".join(out)


def _footer(res: dict) -> str:
    return f"""## 8. Atribusi, lisensi, privasi

- Data OSM (c) OpenStreetMap contributors, lisensi ODbL 1.0. Teks kredit untuk game dan rilis:
  **"Map data (c) OpenStreetMap contributors, available under the Open Database License (https://www.openstreetmap.org/copyright)."**
  Turunan database OSM (footprint, jalan hasil olahan) harus tetap diberi atribusi dan berbagi-serupa sesuai ODbL
  (NFR-06). Dicatat juga di `pipeline/README.md`.
- Pembanding (VIDA gabungan): Google Open Buildings v3 (CC BY 4.0 / ODbL) dan Microsoft Global ML Building Footprints (ODbL).
  Dipakai di audit ini; pemakaian sebagai layer pelengkap game mengikuti ADR-0003 dan wajib diberi atribusi sesuai lisensi masing-masing.
- Privasi (NFR-07): laporan tidak memuat nama pemilik atau alamat; tag `name`/`addr:*` pada bangunan diabaikan
  ({res['buildings']['with_name']} bernama, {res['buildings']['with_addr']} beralamat pada data saat ini).

## 9. Reproduksi

```
uv run python scripts/fetch_osm.py                                   # raw OSM + metadata (jaringan)
uv run --group buildings-ref python scripts/fetch_open_buildings.py  # pembanding (opsional, jaringan)
uv run python scripts/audit_osm.py                                   # tulis laporan ini (tanpa jaringan)
```
"""


def render(res: dict) -> str:
    return "".join([_header(res), _summary(res), _stats(res), _completeness(res), _roads(res),
                    _suspicious_areas(res), _visual(res), _recommend(res), "\n", _footer(res)])
