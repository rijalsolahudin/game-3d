import pytest

from geo.projection import lonlat_to_local, lonlat_to_utm, utm_to_lonlat


def test_utm_zone_49s_known_point():
    # node place=village "Tumanggal" (OSM 1308706192)
    x, y = lonlat_to_utm(109.4864955, -7.3487136)
    assert 300_000 < x < 400_000  # zona 49, dekat meridian tengah 111E
    assert 9_000_000 < y < 9_200_000  # belahan selatan (false northing 10.000 km)


def test_roundtrip():
    lon, lat = 109.4864955, -7.3487136
    x, y = lonlat_to_utm(lon, lat)
    lon2, lat2 = utm_to_lonlat(x, y)
    assert lon2 == pytest.approx(lon, abs=1e-9)
    assert lat2 == pytest.approx(lat, abs=1e-9)


def test_local_axes_east_north():
    o = (109.4864955, -7.3487136)
    x, z = lonlat_to_local(o[0] + 0.001, o[1] + 0.001, *o)
    assert 100 < x < 120 and 100 < z < 120  # ~111 m ke timur & utara
    assert lonlat_to_local(*o, *o) == (0.0, 0.0)
