"""Natural Earth 공개 경계로 수업용 지도를 그린다."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from edupub.paths import ROOT

DATA = ROOT / "지도자료"
OUT = ROOT / "산출물" / "지리연계" / "지도"
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"

OCEAN = (214, 230, 238)
LAND = (226, 232, 236)
LINE = (255, 255, 255)
INK = (35, 48, 58)
HIGH = (31, 111, 139)
MID = (61, 126, 166)
SOUTH = (196, 122, 61)
NORTH = (92, 138, 104)

CENTRAL = {"KR-11", "KR-28", "KR-41", "KR-42", "KR-43", "KR-44", "KR-30", "KR-50"}
SOUTHERN = {"KR-26", "KR-27", "KR-29", "KR-31", "KR-45", "KR-46", "KR-47", "KR-48", "KR-49"}


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _rings(geometry: dict):
    kind = geometry["type"]
    coords = geometry["coordinates"]
    if kind == "Polygon":
        for ring in coords:
            yield ring
    elif kind == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield ring


def _project(lon: float, lat: float, bounds, size, pad: int):
    min_lon, min_lat, max_lon, max_lat = bounds
    width, height = size
    x = pad + (lon - min_lon) / (max_lon - min_lon) * (width - 2 * pad)
    y = pad + (max_lat - lat) / (max_lat - min_lat) * (height - 2 * pad)
    return x, y


def _draw_ring(draw: ImageDraw.ImageDraw, ring, bounds, size, pad, fill, outline):
    points = []
    previous = None
    for lon, lat in ring:
        if previous is not None and abs(lon - previous[0]) > 180:
            if len(points) >= 3:
                draw.polygon(points, fill=fill, outline=outline)
            points = []
        points.append(_project(lon, lat, bounds, size, pad))
        previous = (lon, lat)
    if len(points) >= 3:
        draw.polygon(points, fill=fill, outline=outline)


def _base(title: str, size=(1400, 860)):
    image = Image.new("RGB", size, OCEAN)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, size[0], 64), fill=(24, 62, 84))
    draw.text((28, 16), title, font=_font(28), fill=(255, 255, 255))
    return image, draw


def _title_bar(image: Image.Image, title: str) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 64), fill=(24, 62, 84))
    draw.text((28, 16), title, font=_font(28), fill=(255, 255, 255))


def _footer(image: Image.Image, note: str) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, image.height - 48, image.width, image.height), fill=(245, 248, 250))
    draw.text((20, image.height - 34), note, font=_font(16), fill=INK)


def _graticule(draw, bounds, size, pad):
    min_lon, min_lat, max_lon, max_lat = bounds
    for lon in range(-180, 181, 30):
        if min_lon <= lon <= max_lon:
            x, _ = _project(lon, min_lat, bounds, size, pad)
            draw.line((x, pad, x, size[1] - pad), fill=(190, 210, 220), width=1)
    for lat in range(-60, 81, 30):
        if min_lat <= lat <= max_lat:
            _, y = _project(min_lon, lat, bounds, size, pad)
            draw.line((pad, y, size[0] - pad, y), fill=(190, 210, 220), width=1)


def render_world(
    path: Path,
    highlight: set[str] | None,
    title: str,
    cities: list[str],
    bounds: tuple[float, float, float, float] = (-180, -58, 180, 84),
) -> None:
    countries = _load("ne_110m_countries_slim.geojson")
    places = _load("ne_110m_places_subset.geojson")
    size = (1400, 760)
    pad = 70
    image, draw = _base(title, (1400, 860))
    _graticule(draw, bounds, (1400, 800), pad)
    for feature in countries["features"]:
        continent = feature["properties"].get("CONTINENT") or ""
        if continent == "Seven seas (open ocean)":
            continue
        fill = HIGH if highlight and continent in highlight else LAND
        if highlight is None:
            fill = {
                "Africa": (230, 195, 92),
                "Asia": (126, 182, 217),
                "Europe": (143, 191, 159),
                "North America": (224, 155, 122),
                "South America": (212, 122, 122),
                "Oceania": (183, 160, 212),
                "Antarctica": (244, 244, 244),
            }.get(continent, LAND)
        for ring in _rings(feature["geometry"]):
            _draw_ring(draw, ring, bounds, (1400, 800), pad, fill, LINE)
    placed: list[tuple[float, float, float, float]] = []
    label_font = _font(15)
    for feature in places["features"]:
        if feature["properties"]["NAME"] not in cities:
            continue
        lon, lat = feature["geometry"]["coordinates"]
        x, y = _project(lon, lat, bounds, (1400, 800), pad)
        raw_label = feature["properties"].get("NAME_KO") or feature["properties"]["NAME"]
        label = {"서울특별시": "서울", "베이징시": "베이징", "상하이시": "상하이", "도쿄도": "도쿄"}.get(raw_label, raw_label)
        box = label_font.getbbox(label)
        width, height = box[2] - box[0], box[3] - box[1]
        spot = (x + 6, y - 8, x + 8 + width, y - 6 + height)
        if any(not (spot[2] < old[0] or old[2] < spot[0] or spot[3] < old[1] or old[3] < spot[1]) for old in placed):
            spot = (x + 6, y + 10, x + 8 + width, y + 12 + height)
        if any(not (spot[2] < old[0] or old[2] < spot[0] or spot[3] < old[1] or old[3] < spot[1]) for old in placed):
            continue
        placed.append(spot)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(180, 50, 40))
        draw.text((spot[0], spot[1]), label, font=label_font, fill=INK)
    _title_bar(image, title)
    _footer(image, "Natural Earth 1:110m · 위도경도를 그대로 펼친 학습용 그림 · 면적과 거리는 왜곡됨 · 러시아는 이 자료에서 유럽으로 분류됨")
    image.save(path)


def render_korea(path: Path) -> None:
    korea = _load("ne_10m_admin1_korea.geojson")
    bounds = (124.0, 33.0, 131.2, 43.2)
    size = (900, 1100)
    pad = 70
    image, draw = _base("우리나라 지역의 큰 묶음: 중부 · 남부 · 북부", (980, 1220))
    for feature in korea["features"]:
        iso = feature["properties"].get("iso") or ""
        if iso in CENTRAL:
            fill = MID
        elif iso in SOUTHERN:
            fill = SOUTH
        else:
            fill = NORTH
        for ring in _rings(feature["geometry"]):
            _draw_ring(draw, ring, bounds, size, pad, fill, (255, 255, 255))
    for feature in korea["features"]:
        lon = feature["properties"].get("lon")
        lat = feature["properties"].get("lat")
        label = feature["properties"].get("name_ko") or ""
        if lon is None or lat is None or not label:
            continue
        x, y = _project(float(lon), float(lat), bounds, size, pad)
        short = label.replace("특별자치도", "").replace("특별자치시", "").replace("광역시", "").replace("특별시", "").replace("직할시", "")
        if feature["properties"].get("admin") == "North Korea" and short == "강원도":
            short = "강원도(북)"
        draw.text((x - 18, y - 8), short, font=_font(14), fill=INK)
    draw.rectangle((40, 90, 70, 112), fill=MID)
    draw.text((78, 88), "중부: 수도권 · 강원 · 충청", font=_font(18), fill=INK)
    draw.rectangle((40, 118, 70, 140), fill=SOUTH)
    draw.text((78, 116), "남부: 영남 · 호남 · 제주", font=_font(18), fill=INK)
    draw.rectangle((40, 146, 70, 168), fill=NORTH)
    draw.text((78, 144), "북부: 북한의 시도", font=_font(18), fill=INK)
    _title_bar(image, "우리나라 지역의 큰 묶음: 중부 · 남부 · 북부")
    _footer(image, "Natural Earth 1:10m 시도 경계 · 작은 섬은 이 축척에서 면으로 안 보일 수 있음 · 강원도(북)은 북한 강원도")
    image.save(path)


def render_latitude(path: Path) -> None:
    countries = _load("ne_110m_countries_slim.geojson")
    bounds = (-180, -58, 180, 84)
    size = (1400, 760)
    pad = 70
    image, draw = _base("위도대 모식도: 저위도 · 중위도 · 고위도", (1400, 860))
    for feature in countries["features"]:
        if feature["properties"].get("CONTINENT") == "Seven seas (open ocean)":
            continue
        for ring in _rings(feature["geometry"]):
            _draw_ring(draw, ring, bounds, size, pad, (236, 239, 242), (255, 255, 255))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    bands = [
        (-58, -66.5, (150, 180, 200, 90)),
        (-66.5, -23.5, (120, 170, 140, 80)),
        (-23.5, 23.5, (230, 180, 70, 90)),
        (23.5, 66.5, (120, 170, 140, 80)),
        (66.5, 84, (150, 180, 200, 90)),
    ]
    for lat_a, lat_b, color in bands:
        y_a = _project(0, lat_a, bounds, size, pad)[1]
        y_b = _project(0, lat_b, bounds, size, pad)[1]
        overlay_draw.rectangle((pad, min(y_a, y_b), 1400 - pad, max(y_a, y_b)), fill=color)
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)
    for lat, label in ((0, "적도"), (23.5, "북회귀선"), (-23.5, "남회귀선"), (66.5, "북극권"), (-66.5, "남극권")):
        _, y = _project(0, lat, bounds, size, pad)
        draw.line((pad, y, 1400 - pad, y), fill=(180, 60, 40), width=2)
        draw.text((pad + 8, y + 4), label, font=_font(16), fill=(120, 30, 20))
    _title_bar(image, "위도대 모식도: 저위도 · 중위도 · 고위도")
    _footer(image, "색띠는 관측 기후가 아니라 위도로 나눈 모식도 · Natural Earth 국가 경계")
    image.save(path)


def render_scale(path: Path) -> None:
    image = Image.new("RGB", (1400, 420), (245, 248, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1400, 64), fill=(24, 62, 84))
    draw.text((28, 16), "스케일: 작은 곳과 큰 곳이 서로 연결된다", font=_font(28), fill=(255, 255, 255))
    labels = ["우리 생활 장소", "시·도", "우리나라", "아시아", "세계"]
    for index, label in enumerate(labels):
        left = 40 + index * 270
        draw.rounded_rectangle((left, 120, left + 230, 280), radius=16, fill=HIGH if index == 4 else (220, 232, 238), outline=HIGH, width=3)
        draw.text((left + 24, 175), label, font=_font(26), fill=(255, 255, 255) if index == 4 else INK)
        if index < 4:
            draw.text((left + 236, 180), "→", font=_font(28), fill=HIGH)
    draw.text((40, 330), "중학교 [9사(지리)01-02]의 스케일 개념이 고등학교 세계시민과 지리, 한국지리 탐구로 이어진다.", font=_font(20), fill=INK)
    _footer(image, "학습용 단계 그림 · 실제 지도가 아님")
    image.save(path)


def build_maps() -> dict[str, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {
        "world": OUT / "01_세계_대륙.png",
        "asia": OUT / "02_아시아.png",
        "europe": OUT / "03_유럽.png",
        "africa": OUT / "04_아프리카.png",
        "americas": OUT / "05_아메리카.png",
        "oceania": OUT / "06_오세아니아.png",
        "korea": OUT / "07_우리나라_중부남부북부.png",
        "latitude": OUT / "08_위도대_모식도.png",
        "scale": OUT / "09_스케일.png",
    }
    render_world(paths["world"], None, "세계 대륙: 위치부터 읽기", ["Seoul", "London", "Cairo", "New York", "São Paulo", "Sydney"])
    render_world(paths["asia"], {"Asia"}, "아시아", ["Seoul", "Tokyo", "Beijing", "Shanghai", "Jakarta", "Singapore"], (25, -10, 150, 55))
    render_world(paths["europe"], {"Europe"}, "유럽", ["London", "Paris", "Berlin", "Moscow"], (-12, 35, 50, 70))
    render_world(paths["africa"], {"Africa"}, "아프리카", ["Cairo", "Lagos", "Nairobi", "Johannesburg"], (-20, -36, 55, 38))
    render_world(paths["americas"], {"North America", "South America"}, "아메리카", ["New York", "Mexico City", "São Paulo", "Buenos Aires"], (-125, -56, -30, 55))
    render_world(paths["oceania"], {"Oceania"}, "오세아니아", ["Sydney", "Auckland"], (110, -48, 180, 0))
    render_korea(paths["korea"])
    render_latitude(paths["latitude"])
    render_scale(paths["scale"])
    return paths
