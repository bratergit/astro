"""
Pure-Python, low-precision planetary ephemeris.

Replaces pyswisseph, which only ships precompiled wheels through CPython
3.11 (last released 2023) and breaks on newer interpreters (e.g. Streamlit
Cloud's Python 3.14) with a binary ABI mismatch. This module has zero
compiled dependencies — just math — so it can't hit that class of problem
on any Python version or hosting platform.

Method: standard low-precision Keplerian orbital elements for the major
planets (Standish/JPL, valid ~1800-2050 AD, accurate to a few arcminutes)
for Mercury through Saturn and the Sun, plus Meeus's abbreviated
low-precision lunar position formula (~10 arcmin accuracy) for the Moon.
This is entertainment-grade accuracy — plenty for astrocartography lines,
which are already a non-scientific technique — not observatory-grade.
"""

import math
from typing import Tuple

# --- Keplerian elements at J2000.0 and their rates per Julian century ---
# Format: a (AU), e, I (deg), L (deg), long.peri = ϖ (deg), long.node = Ω (deg)
# Source: standard JPL/Standish low-precision elements (1800-2050 AD).
_ELEMENTS = {
    "mercury": dict(
        a=(0.38709927, 0.00000037), e=(0.20563593, 0.00001906),
        I=(7.00497902, -0.00594749), L=(252.25032350, 149472.67411175),
        peri=(77.45779628, 0.16047689), node=(48.33076593, -0.12534081),
    ),
    "venus": dict(
        a=(0.72333566, 0.00000390), e=(0.00677672, -0.00004107),
        I=(3.39467605, -0.00078890), L=(181.97909950, 58517.81538729),
        peri=(131.60246718, 0.00268329), node=(76.67984255, -0.27769418),
    ),
    "earth": dict(
        a=(1.00000261, 0.00000562), e=(0.01671123, -0.00004392),
        I=(-0.00001531, -0.01294668), L=(100.46457166, 35999.37244981),
        peri=(102.93768193, 0.32327364), node=(0.0, 0.0),
    ),
    "mars": dict(
        a=(1.52371034, 0.00001847), e=(0.09339410, 0.00007882),
        I=(1.84969142, -0.00813131), L=(-4.55343205, 19140.30268499),
        peri=(-23.94362959, 0.44441088), node=(49.55953891, -0.29257343),
    ),
    "jupiter": dict(
        a=(5.20288700, -0.00011607), e=(0.04838624, -0.00013253),
        I=(1.30439695, -0.00183714), L=(34.39644051, 3034.74612775),
        peri=(14.72847983, 0.21252668), node=(100.47390909, 0.20469106),
    ),
    "saturn": dict(
        a=(9.53667594, -0.00125060), e=(0.05386179, -0.00050991),
        I=(2.48599187, 0.00193609), L=(49.95424423, 1222.49362201),
        peri=(92.59887831, -0.41897216), node=(113.66242448, -0.28867794),
    ),
}

OBLIQUITY_J2000_DEG = 23.43929111


def julian_day(year: int, month: int, day: int, hour_utc: float = 12.0) -> float:
    """Standard Julian Day Number for a Gregorian calendar date + UT hour."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    jd = (math.floor(365.25 * (year + 4716)) +
          math.floor(30.6001 * (month + 1)) +
          day + hour_utc / 24.0 + b - 1524.5)
    return jd


def _norm360(deg: float) -> float:
    return deg % 360.0


def _solve_kepler(m_deg: float, e: float, tol: float = 1e-7) -> float:
    """Solves Kepler's equation M = E - e*sin(E) for E, in degrees."""
    m_rad = math.radians(_norm360(m_deg + 180) - 180)  # wrap to [-180,180]
    e_rad = m_rad + e * math.sin(m_rad)
    for _ in range(50):
        delta = (e_rad - e * math.sin(e_rad) - m_rad) / (1 - e * math.cos(e_rad))
        e_rad -= delta
        if abs(delta) < math.radians(tol):
            break
    return math.degrees(e_rad)


def _heliocentric_ecliptic(planet: str, t_centuries: float) -> Tuple[float, float, float]:
    """Heliocentric ecliptic J2000 Cartesian coordinates (AU) for a planet
    (or Earth) at time T (Julian centuries from J2000.0 TT)."""
    el = _ELEMENTS[planet]
    a = el["a"][0] + el["a"][1] * t_centuries
    e = el["e"][0] + el["e"][1] * t_centuries
    inc = el["I"][0] + el["I"][1] * t_centuries
    L = el["L"][0] + el["L"][1] * t_centuries
    peri = el["peri"][0] + el["peri"][1] * t_centuries
    node = el["node"][0] + el["node"][1] * t_centuries

    w = peri - node  # argument of perihelion
    m = _norm360(L - peri)  # mean anomaly
    big_e = _solve_kepler(m, e)  # eccentric anomaly, degrees

    e_rad = math.radians(big_e)
    x_orb = a * (math.cos(e_rad) - e)
    y_orb = a * math.sqrt(1 - e * e) * math.sin(e_rad)

    w_r, node_r, i_r = math.radians(w), math.radians(node), math.radians(inc)
    cw, sw = math.cos(w_r), math.sin(w_r)
    cn, sn = math.cos(node_r), math.sin(node_r)
    ci, si = math.cos(i_r), math.sin(i_r)

    x = (cw * cn - sw * sn * ci) * x_orb + (-sw * cn - cw * sn * ci) * y_orb
    y = (cw * sn + sw * cn * ci) * x_orb + (-sw * sn + cw * cn * ci) * y_orb
    z = (sw * si) * x_orb + (cw * si) * y_orb
    return x, y, z


def _ecliptic_to_equatorial(x: float, y: float, z: float) -> Tuple[float, float]:
    """Converts ecliptic Cartesian (AU) to equatorial RA/Dec (degrees)."""
    eps = math.radians(OBLIQUITY_J2000_DEG)
    x_eq = x
    y_eq = y * math.cos(eps) - z * math.sin(eps)
    z_eq = y * math.sin(eps) + z * math.cos(eps)
    r = math.sqrt(x_eq ** 2 + y_eq ** 2 + z_eq ** 2)
    ra = _norm360(math.degrees(math.atan2(y_eq, x_eq)))
    dec = math.degrees(math.asin(z_eq / r))
    return ra, dec


def _moon_geocentric_ecliptic(t_centuries: float) -> Tuple[float, float]:
    """Meeus's abbreviated low-precision lunar position (~10 arcmin
    accuracy): returns geocentric ecliptic (longitude, latitude) in degrees."""
    T = t_centuries
    Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T**2
    D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T**2
    M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T**2
    Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T**2
    F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T**2

    Lp, D, M, Mp, F = (math.radians(_norm360(v)) for v in (Lp, D, M, Mp, F))

    lon = math.degrees(Lp) + (
        6.289 * math.sin(Mp) - 1.274 * math.sin(Mp - 2 * D) + 0.658 * math.sin(2 * D)
        - 0.186 * math.sin(M) - 0.059 * math.sin(2 * Mp - 2 * D)
        - 0.057 * math.sin(Mp - 2 * D + M) + 0.053 * math.sin(Mp + 2 * D)
        + 0.046 * math.sin(2 * D - M) + 0.041 * math.sin(Mp - M)
        - 0.035 * math.sin(D) - 0.031 * math.sin(Mp + M)
        - 0.015 * math.sin(2 * F - 2 * D) + 0.011 * math.sin(Mp - 4 * D)
    )
    lat = (
        5.128 * math.sin(F) + 0.281 * math.sin(Mp + F) + 0.278 * math.sin(Mp - F)
        + 0.173 * math.sin(2 * D - F) + 0.055 * math.sin(2 * D - Mp + F)
        + 0.046 * math.sin(2 * D - Mp - F) + 0.033 * math.sin(2 * D + F)
        + 0.017 * math.sin(2 * Mp + F)
    )
    return _norm360(lon), lat


def get_planet_radec(jd_ut: float, planet: str) -> Tuple[float, float]:
    """Returns (RA, Dec) in degrees for the given planet at the given
    Julian Day (UT). `planet` is one of: sun, moon, mercury, venus, mars,
    jupiter, saturn."""
    t = (jd_ut - 2451545.0) / 36525.0
    planet = planet.lower()

    if planet == "moon":
        lon_deg, lat_deg = _moon_geocentric_ecliptic(t)
        lon, lat = math.radians(lon_deg), math.radians(lat_deg)
        x = math.cos(lat) * math.cos(lon)
        y = math.cos(lat) * math.sin(lon)
        z = math.sin(lat)
        return _ecliptic_to_equatorial(x, y, z)

    ex, ey, ez = _heliocentric_ecliptic("earth", t)
    if planet == "sun":
        return _ecliptic_to_equatorial(-ex, -ey, -ez)

    px, py, pz = _heliocentric_ecliptic(planet, t)
    gx, gy, gz = px - ex, py - ey, pz - ez
    return _ecliptic_to_equatorial(gx, gy, gz)


def gmst_hours(jd_ut: float) -> float:
    """Greenwich Mean Sidereal Time, in hours, for the given Julian Day (UT)."""
    d = jd_ut - 2451545.0
    t = d / 36525.0
    gmst_deg = (280.46061837 + 360.98564736629 * d
                + 0.000387933 * t**2 - (t**3) / 38710000.0)
    return _norm360(gmst_deg) / 15.0
