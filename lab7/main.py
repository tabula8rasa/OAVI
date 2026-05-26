from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import shutil
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw


# ============================================================
# Настройки
# ============================================================
BASE_DIR = Path('/home/ilya/OAVI/lab7')
SYMBOLS_DIR = BASE_DIR / 'symbols'
IMGS_DIR = BASE_DIR / 'img'
OUT_DIR = BASE_DIR / 'result'
REPORT_PATH = BASE_DIR / 'result.md'

PHRASE_PATH = IMGS_DIR / 'phrase.bmp'
PHRASE_ALT_PATH = IMGS_DIR / 'phrase_alt.bmp'

GROUND_TRUTH = 'ЭТОЛИШЬИГРА'

AUTO_CROP = True
CROP_PADDING = 2
ROW_THRESHOLD = 1
ROW_GAP_TO_MERGE = 2
MIN_LINE_HEIGHT = 5

COL_THRESHOLD = 0
COL_GAP_TO_MERGE = 0
MIN_SYMBOL_WIDTH = 2

SLANT_DEGREES = 0.0
TRY_BOTH_SLANT_DIRECTIONS = False
DEFAULT_SLANT_DIRECTION = 1
BOX_PADDING = 1

PROFILE_LEN_X = 20
PROFILE_LEN_Y = 20
PROFILE_WEIGHT = 1.0

ALT_SCALE = 0.8

HYPOTHESES_NAME = 'hypotheses_{stem}_{mode}.txt'
SEGMENTED_NAME = 'segmented_boxes_{stem}.png'


@dataclass
class Interval:
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1


@dataclass
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1 + 1

    @property
    def height(self) -> int:
        return self.y2 - self.y1 + 1


@dataclass
class Template:
    symbol: str
    filename: str
    image: np.ndarray
    features_raw: np.ndarray
    features_norm: np.ndarray | None = None


def cleanup_previous_results() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()


def auto_create_phrase_alt() -> None:
    """
    Автоматически создаёт phrase_alt.bmp из phrase.bmp,
    уменьшая изображение в ALT_SCALE раз.
    """
    if not PHRASE_PATH.exists():
        return

    img = Image.open(PHRASE_PATH).convert('L')
    w, h = img.size
    new_size = (max(1, int(w * ALT_SCALE)), max(1, int(h * ALT_SCALE)))

    # NEAREST лучше для монохромных изображений, чтобы не появлялась серая полутоновая кайма.
    alt = img.resize(new_size, Image.Resampling.NEAREST)
    alt.save(PHRASE_ALT_PATH)


def load_binary_image(path: Path) -> np.ndarray:
    img = Image.open(path).convert('L')
    arr = np.array(img)
    return (arr < 128).astype(np.uint8)


def crop_to_content(binary: np.ndarray, padding: int = 0) -> np.ndarray:
    ys, xs = np.where(binary > 0)
    if len(xs) == 0:
        return binary.copy()

    y1 = max(0, int(ys.min()) - padding)
    y2 = min(binary.shape[0] - 1, int(ys.max()) + padding)
    x1 = max(0, int(xs.min()) - padding)
    x2 = min(binary.shape[1] - 1, int(xs.max()) + padding)
    return binary[y1:y2 + 1, x1:x2 + 1]


def save_binary_image(binary: np.ndarray, path: Path) -> None:
    img = Image.fromarray((1 - binary) * 255).convert('L')
    img.save(path)


def horizontal_profile(binary: np.ndarray) -> np.ndarray:
    return binary.sum(axis=1).astype(int)


def vertical_profile(binary: np.ndarray) -> np.ndarray:
    return binary.sum(axis=0).astype(int)


def extract_intervals_from_profile(
    profile: np.ndarray,
    threshold: int,
    gap_to_merge: int,
    min_length: int,
) -> List[Interval]:
    active = profile > threshold
    intervals: List[Interval] = []

    start = None
    for i, flag in enumerate(active):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            intervals.append(Interval(start, i - 1))
            start = None
    if start is not None:
        intervals.append(Interval(start, len(profile) - 1))

    if not intervals:
        return []

    merged = [intervals[0]]
    for current in intervals[1:]:
        prev = merged[-1]
        gap = current.start - prev.end - 1
        if gap <= gap_to_merge:
            merged[-1] = Interval(prev.start, current.end)
        else:
            merged.append(current)

    return [it for it in merged if it.length >= min_length]


def slanted_x_for_pixel(x: int, y: int, h: int, slant_direction: int, slant_degrees: float) -> int:
    shear = math.tan(math.radians(slant_degrees))
    shift = int(round((h - 1 - y) * shear * slant_direction))
    return x + shift


def build_slanted_vertical_profile(
    line_binary: np.ndarray,
    slant_direction: int,
    slant_degrees: float,
) -> Tuple[np.ndarray, int, np.ndarray]:
    h, w = line_binary.shape
    x_slanted = np.zeros((h, w), dtype=int)

    for y in range(h):
        for x in range(w):
            x_slanted[y, x] = slanted_x_for_pixel(x, y, h, slant_direction, slant_degrees)

    min_xp = int(x_slanted.min())
    max_xp = int(x_slanted.max())
    width_slanted = max_xp - min_xp + 1

    profile = np.zeros(width_slanted, dtype=int)
    black_points = np.argwhere(line_binary > 0)
    for y, x in black_points:
        xp = x_slanted[y, x] - min_xp
        profile[xp] += 1

    return profile, min_xp, x_slanted


def profile_separation_score(profile: np.ndarray, threshold: int) -> Tuple[int, float]:
    low_columns = int((profile <= threshold).sum())
    variance = float(profile.var())
    return low_columns, variance


def choose_best_slant_direction(line_binary: np.ndarray) -> int:
    if not TRY_BOTH_SLANT_DIRECTIONS:
        return DEFAULT_SLANT_DIRECTION

    candidates: List[Tuple[Tuple[int, float], int]] = []
    for direction in (-1, 1):
        profile, _, _ = build_slanted_vertical_profile(line_binary, direction, SLANT_DEGREES)
        score = profile_separation_score(profile, COL_THRESHOLD)
        candidates.append((score, direction))

    candidates.sort(reverse=True)
    return candidates[0][1]


def intervals_to_bboxes_on_original_line(
    line_binary: np.ndarray,
    intervals: List[Interval],
    min_xp: int,
    x_slanted: np.ndarray,
    line_y_offset: int,
) -> List[BBox]:
    bboxes: List[BBox] = []
    black_points = np.argwhere(line_binary > 0)
    if len(black_points) == 0:
        return bboxes

    xp_values = x_slanted[black_points[:, 0], black_points[:, 1]]

    for interval in intervals:
        left = interval.start + min_xp
        right = interval.end + min_xp

        mask = (xp_values >= left) & (xp_values <= right)
        pts = black_points[mask]
        if len(pts) == 0:
            continue

        ys = pts[:, 0]
        xs = pts[:, 1]

        x1 = max(0, int(xs.min()) - BOX_PADDING)
        x2 = min(line_binary.shape[1] - 1, int(xs.max()) + BOX_PADDING)
        y1 = max(0, int(ys.min()) - BOX_PADDING)
        y2 = min(line_binary.shape[0] - 1, int(ys.max()) + BOX_PADDING)

        bboxes.append(BBox(
            x1=x1,
            y1=y1 + line_y_offset,
            x2=x2,
            y2=y2 + line_y_offset,
        ))

    return bboxes


def segment_image_to_boxes(binary: np.ndarray) -> tuple[np.ndarray, List[BBox]]:
    working = crop_to_content(binary, padding=CROP_PADDING) if AUTO_CROP else binary.copy()

    h_profile = horizontal_profile(working)
    lines = extract_intervals_from_profile(
        profile=h_profile,
        threshold=ROW_THRESHOLD,
        gap_to_merge=ROW_GAP_TO_MERGE,
        min_length=MIN_LINE_HEIGHT,
    )
    if not lines:
        raise RuntimeError('Не удалось выделить строки по горизонтальному профилю.')

    all_boxes: List[BBox] = []
    for line in lines:
        line_binary = working[line.start:line.end + 1, :]
        slant_direction = choose_best_slant_direction(line_binary)
        v_profile, min_xp, x_slanted = build_slanted_vertical_profile(
            line_binary=line_binary,
            slant_direction=slant_direction,
            slant_degrees=SLANT_DEGREES,
        )
        intervals = extract_intervals_from_profile(
            profile=v_profile,
            threshold=COL_THRESHOLD,
            gap_to_merge=COL_GAP_TO_MERGE,
            min_length=MIN_SYMBOL_WIDTH,
        )
        boxes = intervals_to_bboxes_on_original_line(
            line_binary=line_binary,
            intervals=intervals,
            min_xp=min_xp,
            x_slanted=x_slanted,
            line_y_offset=line.start,
        )
        boxes.sort(key=lambda b: b.x1)
        all_boxes.extend(boxes)

    return working, all_boxes


def draw_bboxes_on_image(binary: np.ndarray, bboxes: List[BBox], path: Path) -> None:
    img = Image.fromarray((1 - binary) * 255).convert('RGB')
    draw = ImageDraw.Draw(img)

    for i, box in enumerate(bboxes, start=1):
        draw.rectangle((box.x1, box.y1, box.x2, box.y2), outline=(255, 0, 0), width=1)
        draw.text((box.x1, max(0, box.y1 - 10)), str(i), fill=(0, 0, 255))

    img.save(path)


def crop_box(binary: np.ndarray, box: BBox) -> np.ndarray:
    return binary[box.y1:box.y2 + 1, box.x1:box.x2 + 1]


def calc_relative_weight(binary: np.ndarray) -> float:
    h, w = binary.shape
    area = h * w
    return float(binary.sum() / area) if area > 0 else 0.0


def calc_center_of_mass(binary: np.ndarray) -> Tuple[float, float]:
    h, w = binary.shape
    weight = binary.sum()
    if weight == 0:
        return 0.0, 0.0

    ys, xs = np.indices((h, w))
    x_center = float((xs * binary).sum() / weight)
    y_center = float((ys * binary).sum() / weight)
    return x_center, y_center


def calc_normalized_center_of_mass(binary: np.ndarray, x_center: float, y_center: float) -> Tuple[float, float]:
    h, w = binary.shape
    x_rel = float(x_center / (w - 1)) if w > 1 else 0.0
    y_rel = float(y_center / (h - 1)) if h > 1 else 0.0
    return x_rel, y_rel


def calc_inertia_moments(binary: np.ndarray, x_center: float, y_center: float) -> Tuple[float, float]:
    h, w = binary.shape
    ys, xs = np.indices((h, w))
    ix = float((((ys - y_center) ** 2) * binary).sum())
    iy = float((((xs - x_center) ** 2) * binary).sum())
    return ix, iy


def calc_normalized_inertia_moments(binary: np.ndarray, ix: float, iy: float) -> Tuple[float, float]:
    h, w = binary.shape
    denom = float((w ** 2) * (h ** 2))
    if denom == 0:
        return 0.0, 0.0
    return ix / denom, iy / denom


def resize_profile(profile: np.ndarray, target_len: int) -> np.ndarray:
    profile = np.asarray(profile, dtype=float)
    if target_len <= 0:
        raise ValueError('target_len must be positive')

    if profile.size == 0:
        return np.zeros(target_len, dtype=float)

    if profile.size == 1:
        return np.full(target_len, profile[0], dtype=float)

    old_x = np.linspace(0.0, 1.0, profile.size)
    new_x = np.linspace(0.0, 1.0, target_len)
    return np.interp(new_x, old_x, profile)


def normalized_profile(profile: np.ndarray, target_len: int) -> np.ndarray:
    resized = resize_profile(profile, target_len)
    max_value = float(resized.max())
    if max_value <= 0:
        return resized
    return resized / max_value


def profile_features(binary: np.ndarray) -> np.ndarray:
    px = vertical_profile(binary)
    py = horizontal_profile(binary)

    px_norm = normalized_profile(px, PROFILE_LEN_X)
    py_norm = normalized_profile(py, PROFILE_LEN_Y)

    return np.concatenate([px_norm, py_norm]) * PROFILE_WEIGHT


def extract_feature_vector(binary: np.ndarray, use_profiles: bool) -> np.ndarray:
    symbol = crop_to_content(binary, padding=0)

    rel_weight = calc_relative_weight(symbol)
    x_center, y_center = calc_center_of_mass(symbol)
    x_rel, y_rel = calc_normalized_center_of_mass(symbol, x_center, y_center)
    ix, iy = calc_inertia_moments(symbol, x_center, y_center)
    ix_rel, iy_rel = calc_normalized_inertia_moments(symbol, ix, iy)

    scalar_features = np.array([rel_weight, x_rel, y_rel, ix_rel, iy_rel], dtype=float)

    if not use_profiles:
        return scalar_features

    xy_profile_features = profile_features(symbol)
    return np.concatenate([scalar_features, xy_profile_features])


def parse_symbol_from_name(stem: str) -> str:
    parts = stem.split('_')
    for part in parts:
        if part.startswith('U'):
            try:
                return chr(int(part[1:], 16))
            except ValueError:
                pass
    return stem[0]


def load_templates(symbols_dir: Path, use_profiles: bool) -> List[Template]:
    templates: List[Template] = []
    paths = sorted(symbols_dir.glob('*.png')) + sorted(symbols_dir.glob('*.bmp'))
    if not paths:
        raise FileNotFoundError(f'В папке {symbols_dir} не найдено эталонных изображений.')

    for path in paths:
        binary = load_binary_image(path)
        binary = crop_to_content(binary, padding=0)
        features = extract_feature_vector(binary, use_profiles=use_profiles)
        symbol = parse_symbol_from_name(path.stem)
        templates.append(Template(
            symbol=symbol,
            filename=path.name,
            image=binary,
            features_raw=features,
        ))

    return templates


def fit_minmax_normalizer(vectors: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mins = vectors.min(axis=0)
    maxs = vectors.max(axis=0)
    maxs = np.where(maxs == mins, mins + 1.0, maxs)
    return mins, maxs


def apply_minmax_normalizer(vector: np.ndarray, mins: np.ndarray, maxs: np.ndarray) -> np.ndarray:
    return (vector - mins) / (maxs - mins)


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(((a - b) ** 2).sum()))


def similarity_from_distance(distance: float) -> float:
    return 1.0 / (1.0 + distance)


def classify_symbol(
    symbol_image: np.ndarray,
    templates: List[Template],
    mins: np.ndarray,
    maxs: np.ndarray,
    use_profiles: bool,
) -> Tuple[np.ndarray, List[Tuple[str, float]]]:
    raw = extract_feature_vector(symbol_image, use_profiles=use_profiles)
    norm = apply_minmax_normalizer(raw, mins, maxs)

    hypotheses: List[Tuple[str, float]] = []
    for template in templates:
        assert template.features_norm is not None
        dist = euclidean_distance(norm, template.features_norm)
        sim = similarity_from_distance(dist)
        hypotheses.append((template.symbol, sim))

    hypotheses.sort(key=lambda x: x[1], reverse=True)
    return norm, hypotheses


def levenshtein_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[m][n]


def positional_matches(s1: str, s2: str) -> int:
    return sum(c1 == c2 for c1, c2 in zip(s1, s2))


def save_hypotheses(hypotheses_per_symbol: List[List[Tuple[str, float]]], path: Path) -> None:
    with path.open('w', encoding='utf-8') as f:
        for idx, hypotheses in enumerate(hypotheses_per_symbol, start=1):
            formatted = ', '.join(f"('{char}', {score:.4f})" for char, score in hypotheses)
            f.write(f'{idx}: [{formatted}]\n')


def prepare_templates(use_profiles: bool) -> tuple[List[Template], np.ndarray, np.ndarray]:
    templates = load_templates(SYMBOLS_DIR, use_profiles=use_profiles)
    template_matrix = np.vstack([tpl.features_raw for tpl in templates])
    mins, maxs = fit_minmax_normalizer(template_matrix)

    for tpl in templates:
        tpl.features_norm = apply_minmax_normalizer(tpl.features_raw, mins, maxs)

    return templates, mins, maxs


def recognize_image(
    image_path: Path,
    templates: List[Template],
    mins: np.ndarray,
    maxs: np.ndarray,
    use_profiles: bool,
    mode_name: str,
) -> dict:
    source_binary = load_binary_image(image_path)
    working, boxes = segment_image_to_boxes(source_binary)
    if not boxes:
        raise RuntimeError(f'На изображении {image_path.name} не удалось найти символы.')

    image_out_dir = OUT_DIR / image_path.stem / mode_name
    symbols_out_dir = image_out_dir / 'symbols'
    image_out_dir.mkdir(parents=True, exist_ok=True)
    symbols_out_dir.mkdir(parents=True, exist_ok=True)

    source_copy_path = image_out_dir / 'source.bmp'
    segmented_path = image_out_dir / SEGMENTED_NAME.format(stem=image_path.stem)
    hypotheses_path = image_out_dir / HYPOTHESES_NAME.format(stem=image_path.stem, mode=mode_name)

    save_binary_image(working, source_copy_path)
    draw_bboxes_on_image(working, boxes, segmented_path)

    hypotheses_per_symbol: List[List[Tuple[str, float]]] = []
    best_chars: List[str] = []

    for idx, box in enumerate(boxes, start=1):
        symbol_img = crop_box(working, box)
        symbol_img = crop_to_content(symbol_img, padding=0)
        save_binary_image(symbol_img, symbols_out_dir / f'symbol_{idx:02d}.bmp')

        _, hypotheses = classify_symbol(
            symbol_img,
            templates,
            mins,
            maxs,
            use_profiles=use_profiles,
        )
        hypotheses_per_symbol.append(hypotheses)
        best_chars.append(hypotheses[0][0])

    recognized = ''.join(best_chars)
    errors = levenshtein_distance(GROUND_TRUTH, recognized)
    matches = positional_matches(GROUND_TRUTH, recognized)
    accuracy_pct = 100.0 * matches / len(GROUND_TRUTH) if GROUND_TRUTH else 0.0

    save_hypotheses(hypotheses_per_symbol, hypotheses_path)

    return {
        'mode_name': mode_name,
        'use_profiles': use_profiles,
        'image_path': image_path,
        'source_copy_path': source_copy_path,
        'recognized': recognized,
        'errors': errors,
        'matches': matches,
        'accuracy_pct': accuracy_pct,
        'boxes': boxes,
        'segmented_path': segmented_path,
        'hypotheses_path': hypotheses_path,
        'hypotheses_per_symbol': hypotheses_per_symbol,
        'feature_dim': templates[0].features_raw.size,
    }


def md_path(path: Path) -> str:
    return './' + path.relative_to(BASE_DIR).as_posix()


def make_hypothesis_preview(hypotheses: List[Tuple[str, float]], limit: int = 5) -> str:
    return ', '.join(f'{char}: {score:.4f}' for char, score in hypotheses[:limit])


def create_report(results: List[dict], templates_scalar: List[Template], templates_profiles: List[Template]) -> None:
    lines: list[str] = []
    lines.extend([
        '# Лабораторная работа №7. Классификация на основе признаков, анализ профилей',
        '',
        '**Алфавит:** кириллица заглавная  ',
        '**Эксперимент:** сравнение классификации до и после добавления профилей X/Y  ',
        '',
        '---',
        '',
        '## Использованные методы',
        '',
        'В работе выполнены два варианта распознавания:',
        '',
        '1. **Без профилей** — используются только скалярные признаки: удельная масса чёрного, нормированные координаты центра тяжести, нормированные осевые моменты инерции Ix и Iy.',
        '2. **С профилями X/Y** — к скалярным признакам добавляются нормированные профили X и Y, приведённые к фиксированной длине.',
        '',
        'Мера близости рассчитывается через евклидово расстояние в пространстве нормализованных признаков:',
        '',
        '$$',
        r'S = \frac{1}{1 + d}',
        '$$',
        '',
        f'Для эксперимента автоматически создан файл `phrase_alt.bmp`: исходное изображение уменьшено в {ALT_SCALE:.1f} раза.',
        '',
        '---',
        '',
        '## Подготовка эталонов',
        '',
        f'Эталонов загружено: **{len(templates_profiles)}**.',
        '',
        f'Размерность признаков без профилей: **{templates_scalar[0].features_raw.size}**.',
        '',
        f'Размерность признаков с профилями: **{templates_profiles[0].features_raw.size}**.',
        '',
        'Алфавит эталонов:',
        '',
        f'`{"".join(t.symbol for t in templates_profiles)}`',
        '',
    ])

    for idx, result in enumerate(results, start=1):
        mode_title = 'без профилей' if not result['use_profiles'] else 'с профилями X/Y'
        image_title = 'основное изображение' if result['image_path'].name == 'phrase.bmp' else 'уменьшенное изображение phrase_alt.bmp'

        lines.extend([
            '---',
            '',
            f'## {idx}. Распознавание: {image_title}, {mode_title}',
            '',
            f'**Файл:** `{result["image_path"].name}`  ',
            f'**Режим:** `{result["mode_name"]}`  ',
            f'**Размерность признакового вектора:** `{result["feature_dim"]}`',
            '',
            '### Исходное изображение',
            '',
            f'![]({md_path(result["source_copy_path"])})',
            '',
            '### Сегментация символов',
            '',
            f'![]({md_path(result["segmented_path"])})',
            '',
            '### Результат распознавания',
            '',
            f'- Эталонная строка: `{GROUND_TRUTH}`',
            f'- Распознанная строка: `{result["recognized"]}`',
            f'- Совпадений по позициям: **{result["matches"]} из {len(GROUND_TRUTH)}**',
            f'- Количество ошибок по Левенштейну: **{result["errors"]}**',
            f'- Доля верно распознанных символов: **{result["accuracy_pct"]:.2f}%**',
            '',
            f'Полный список гипотез сохранён в файл: `{md_path(result["hypotheses_path"])}`.',
            '',
            '### Лучшие гипотезы по символам',
            '',
            '| № | Лучшая гипотеза | Мера близости | Первые 5 гипотез |',
            '|---:|:---:|---:|---|',
        ])

        for i, hypotheses in enumerate(result['hypotheses_per_symbol'], start=1):
            best_char, best_score = hypotheses[0]
            lines.append(f'| {i} | `{best_char}` | {best_score:.4f} | {make_hypothesis_preview(hypotheses)} |')

        lines.append('')

    lines.extend([
        '---',
        '',
        '## Сводное сравнение',
        '',
        '| Изображение | Режим | Распознанная строка | Ошибки | Точность |',
        '|---|---|---|---:|---:|',
    ])

    for result in results:
        mode_title = 'без профилей' if not result['use_profiles'] else 'с профилями'
        lines.append(
            f'| `{result["image_path"].name}` | {mode_title} | `{result["recognized"]}` | {result["errors"]} | {result["accuracy_pct"]:.2f}% |'
        )

    lines.extend([
        '',
        '---',
        '',
        '## Вывод',
        '',
        'В ходе работы были выполнены два варианта классификации: только по скалярным признакам и по расширенному набору признаков с профилями X/Y. Добавление профилей позволяет учитывать форму символа, поэтому похожие по массе и моментам буквы различаются лучше.',
        '',
    ])

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')


def print_result(result: dict, title: str) -> None:
    print(f'=== {title} ===')
    print(f'Файл: {result["image_path"].name}')
    print(f'Режим: {result["mode_name"]}')
    print(f'Распознанная строка: {result["recognized"]}')
    print(f'Эталонная строка:    {GROUND_TRUTH}')
    print(f'Совпадений по позициям: {result["matches"]} из {len(GROUND_TRUTH)}')
    print(f'Количество ошибок (по Левенштейну): {result["errors"]}')
    print(f'Доля верно распознанных символов: {result["accuracy_pct"]:.2f}%')
    print(f'Гипотезы сохранены в: {result["hypotheses_path"]}')
    print(f'Сегментация сохранена в: {result["segmented_path"]}')


def main() -> None:
    IMGS_DIR.mkdir(parents=True, exist_ok=True)

    cleanup_previous_results()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not SYMBOLS_DIR.exists():
        raise FileNotFoundError(f'Не найдена папка {SYMBOLS_DIR} с эталонными символами.')
    if not PHRASE_PATH.exists():
        raise FileNotFoundError(f'Не найден файл {PHRASE_PATH}')

    auto_create_phrase_alt()

    templates_scalar, mins_scalar, maxs_scalar = prepare_templates(use_profiles=False)
    templates_profiles, mins_profiles, maxs_profiles = prepare_templates(use_profiles=True)

    print('=== Эталоны ===')
    print(f'Загружено эталонных символов: {len(templates_profiles)}')
    print('Алфавит эталонов:', ''.join(t.symbol for t in templates_profiles))
    print(f'Размерность без профилей: {templates_scalar[0].features_raw.size}')
    print(f'Размерность с профилями: {templates_profiles[0].features_raw.size}')
    print()

    input_images = [PHRASE_PATH, PHRASE_ALT_PATH]

    results: List[dict] = []
    for image_path in input_images:
        result_scalar = recognize_image(
            image_path=image_path,
            templates=templates_scalar,
            mins=mins_scalar,
            maxs=maxs_scalar,
            use_profiles=False,
            mode_name='without_profiles',
        )
        results.append(result_scalar)
        print_result(result_scalar, title='Без профилей')

        print()

        result_profiles = recognize_image(
            image_path=image_path,
            templates=templates_profiles,
            mins=mins_profiles,
            maxs=maxs_profiles,
            use_profiles=True,
            mode_name='with_profiles',
        )
        results.append(result_profiles)
        print_result(result_profiles, title='С профилями X/Y')
        print()

    create_report(results, templates_scalar, templates_profiles)
    print(f'Отчёт сохранён: {REPORT_PATH}')


if __name__ == '__main__':
    main()
