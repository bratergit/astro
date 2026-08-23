import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np
from PIL import Image, ImageFilter

# --- 1. BIORHYTHM ENGINE ---
def calculate_biorhythms(birthdate: datetime, target_date: datetime) -> Dict[str, float]:
    """Calculates Physical (23d), Emotional (28d), and Intellectual (33d) sine cycles."""
    days = (target_date - birthdate).days
    return {
        "physical": math.sin(2 * math.pi * days / 23),
        "emotional": math.sin(2 * math.pi * days / 28),
        "intellectual": math.sin(2 * math.pi * days / 33)
    }

# --- 2. NAME NUMEROLOGY ENGINE ---
NUMEROLOGY_MAP = {
    'a': 1, 'j': 1, 's': 1, 'b': 2, 'k': 2, 't': 2, 'c': 3, 'l': 3, 'u': 3,
    'd': 4, 'm': 4, 'v': 4, 'e': 5, 'n': 5, 'w': 5, 'f': 6, 'o': 6, 'x': 6,
    'g': 7, 'p': 7, 'y': 7, 'h': 8, 'q': 8, 'z': 8, 'i': 9, 'r': 9
}

PLANETARY_RULERS = {
    1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Uranus",
    5: "Mercury", 6: "Venus", 7: "Neptune", 8: "Saturn", 9: "Mars"
}

def calculate_name_number(name: str) -> Tuple[int, str]:
    """Reduces name letters to a single digit and returns the governing planet."""
    total = sum(NUMEROLOGY_MAP.get(char.lower(), 0) for char in name if char.isalpha())
    while total > 9:
        total = sum(int(digit) for digit in str(total))
    return total, PLANETARY_RULERS.get(total, "Unknown")

# --- 3. GEOSPATIAL & LEY LINE ENGINE ---
LEY_LINE_NODES = {
    "Giza Grid": (29.9792, 31.1342),
    "Stonehenge Line": (51.1789, -1.8262),
    "Sedona Vortex": (34.8710, -111.7601),
    "Machu Picchu Node": (-13.1631, -72.5450)
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in kilometers between two geographic coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_nearest_ley_line(user_lat: float, user_lon: float) -> Tuple[str, float]:
    """Finds proximity to closest Earth energetic grid point."""
    distances = {node: haversine_distance(user_lat, user_lon, coords[0], coords[1])
                 for node, coords in LEY_LINE_NODES.items()}
    nearest = min(distances, key=distances.get)
    return nearest, distances[nearest]

# --- 4. PALM IMAGE ENGINE (heuristic, right hand) ---
# NOTE: This is a simplified image-heuristic, not a validated biometric or
# scientific palm-reading system. Palmistry itself has no established
# predictive validity — treat this purely as a stylistic/entertainment input
# generator, the same way the rest of this app treats numerology and ley lines.

def _load_color(image_path: str, size: Tuple[int, int] = (256, 256)) -> np.ndarray:
    """Captures the photo in full color (RGB) first, at a fixed size."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize(size)
    return np.asarray(img, dtype=np.uint8)

def _to_grayscale(color_arr: np.ndarray) -> np.ndarray:
    """Derives a blurred grayscale array from an already-captured color image."""
    img = Image.fromarray(color_arr, mode="RGB").convert("L")
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    return np.asarray(img, dtype=np.float32)

def _edge_gradients(gray: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Simple Sobel-style gradient magnitudes in x and y directions."""
    gx = np.gradient(gray, axis=1)
    gy = np.gradient(gray, axis=0)
    return gx, gy

def _dominant_aura_color(color_arr: np.ndarray) -> str:
    """Buckets the photo's average hue into a simple named 'aura' color."""
    import colorsys
    r, g, b = [float(np.mean(color_arr[:, :, i])) / 255.0 for i in range(3)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    degrees = h * 360
    buckets = [
        (15, "Red"), (45, "Orange"), (70, "Yellow"), (170, "Green"),
        (200, "Cyan"), (260, "Blue"), (290, "Violet"), (345, "Magenta"),
    ]
    for cutoff, label in buckets:
        if degrees < cutoff:
            return label
    return "Red"

def analyze_palm_image(image_path: str, hand: str = "right") -> Dict[str, str]:
    """
    Heuristically derives a 'heart line' style descriptor from a photo of a hand.

    The photo is captured in color first, then a grayscale version is derived
    from that color capture for the edge/curvature analysis. The color capture
    is also used for a lightweight 'aura color' extra.

    This does NOT perform real hand/landmark detection. It is a crude image
    heuristic (edge curvature + contrast) over the whole frame, intended to
    feed the same categorical inputs the rest of the app already uses.
    For a real palm-line reader you'd want a hand-landmark model (e.g.
    MediaPipe Hands) to first crop/align the palm before any line analysis.
    """
    if hand.lower() != "right":
        raise ValueError("This build only processes the right hand, per app convention.")

    color_arr = _load_color(image_path)
    gray = _to_grayscale(color_arr)
    aura_color = _dominant_aura_color(color_arr)
    gx, gy = _edge_gradients(gray)

    # "Curvature" proxy: how much horizontal gradient dominates vertical
    # gradient across strong-edge pixels (curved lines bend across both axes;
    # straight lines tend to have a single dominant orientation).
    magnitude = np.sqrt(gx**2 + gy**2)
    strong_edges = magnitude > np.percentile(magnitude, 85)

    if strong_edges.sum() == 0:
        curvature_ratio = 0.5
        depth_score = 0.0
    else:
        gx_strong = np.abs(gx[strong_edges])
        gy_strong = np.abs(gy[strong_edges])
        curvature_ratio = float(np.mean(np.minimum(gx_strong, gy_strong) /
                                         (np.maximum(gx_strong, gy_strong) + 1e-6)))
        depth_score = float(np.mean(magnitude[strong_edges]) / 255.0)

    is_curved = curvature_ratio > 0.35
    is_deep = depth_score > 0.15

    if is_curved and is_deep:
        heart_line_type = "Curved/Deep"
    elif is_curved and not is_deep:
        heart_line_type = "Curved/Shallow"
    elif not is_curved and is_deep:
        heart_line_type = "Straight/Deep"
    else:
        heart_line_type = "Straight/Shallow"

    return {
        "heart_line_type": heart_line_type,
        "curvature_ratio": round(curvature_ratio, 3),
        "depth_score": round(depth_score, 3),
        "dominant_aura_color": aura_color,
        "note": "Heuristic estimate from whole-image edge/color statistics; not a validated palm reading."
    }

# --- 5. CORRELATION & SOULMATE ENGINE ---
def synthesize_profile(
    name: str,
    birthdate_str: str,
    lat: float,
    lon: float,
    is_single: bool,
    heart_line_type: Optional[str] = None,
    palm_image_path: Optional[str] = None,
) -> Dict:
    """
    heart_line_type can be supplied directly, OR derived from a right-hand
    photo via palm_image_path (analyze_palm_image is called automatically
    if heart_line_type isn't given but an image path is).
    """
    birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d")
    now = datetime.now()

    bio = calculate_biorhythms(birthdate, now)
    num_val, ruler = calculate_name_number(name)
    node, distance = find_nearest_ley_line(lat, lon)

    palm_analysis = None
    if heart_line_type is None:
        if palm_image_path is None:
            raise ValueError("Provide either heart_line_type or palm_image_path (right hand photo).")
        palm_analysis = analyze_palm_image(palm_image_path, hand="right")
        heart_line_type = palm_analysis["heart_line_type"]

    estimated_astro_line = "Venus Midheaven (MC)" if ruler in ["Venus", "Moon"] else "Mars Ascendant (AC)"

    profile = {
        "user_name": name,
        "numerology_number": num_val,
        "planetary_ruler": ruler,
        "biorhythms_current": bio,
        "nearest_ley_node": f"{node} ({round(distance, 1)} km)",
        "astrocartography_influence": estimated_astro_line,
        "palmistry_heart_line": heart_line_type,
    }
    if palm_analysis:
        profile["palm_image_analysis"] = palm_analysis

    if is_single:
        soulmate_element = "Water/Earth" if ruler in ["Moon", "Venus", "Neptune"] else "Fire/Air"
        optimal_timing = "High Emotional Cycle" if bio["emotional"] > 0 else "Cycle Transitioning Positive"

        profile["soulmate_profile"] = {
            "archetype": f"{ruler}-aligned {soulmate_element} archetype",
            "key_traits": "Deeply empathetic and grounded" if "Curved" in heart_line_type else "Independent and logical",
            "ideal_meeting_location": f"Regions along your {estimated_astro_line} line or near {node}",
            "biorhythmic_readiness": optimal_timing,
        }

    return profile

# --- EXAMPLE EXECUTION ---
if __name__ == "__main__":
    import json

    # Option A: manual heart_line_type (original behavior)
    result_manual = synthesize_profile(
        name="Adalberto Brant",
        birthdate_str="1995-06-15",
        lat=-18.9186,
        lon=-48.2772,
        heart_line_type="Curved/Deep",
        is_single=True,
    )
    print(json.dumps(result_manual, indent=2))

    # Option B: derive heart_line_type from a right-hand photo instead
    # result_from_photo = synthesize_profile(
    #     name="Adalberto Brant",
    #     birthdate_str="1995-06-15",
    #     lat=-18.9186,
    #     lon=-48.2772,
    #     is_single=True,
    #     palm_image_path="/path/to/right_hand.jpg",
    # )
    # print(json.dumps(result_from_photo, indent=2))
