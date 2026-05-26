from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import math
import shutil

import numpy as np
from PIL import Image, ImageDraw

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


# =========================
# Настройки проекта
# =========================
BASE_DIR = Path('/home/ilya/OAVI/lab6')
IMGS_DIR = BASE_DIR / 'img'
OUT_DIR = BASE_DIR / 'result'
SYMBOLS_OUT_DIR = OUT_DIR / 'symbols'
PROFILES_OUT_DIR = OUT_DIR / 'profiles'
REPORT_PATH = BASE_DIR / 'result.md'

INPUT_PATH = IMGS_DIR / 'phrase.bmp'
SOURCE_COPY_PATH = OUT_DIR / 'phrase_source.bmp'
HORIZONTAL_PROFILE_PATH = OUT_DIR / 'horizontal_profile.png'
SEGMENTED_PATH = OUT_DIR / 'segmented_boxes.png'

# Если вокруг текста всё же остался небольшой белый фон — можно оставить True.
AUTO_CROP = True
CROP_PADDING = 2

# Порог для строк: строки считаются там, где горизонтальный профиль больше этого значения.
ROW_THRESHOLD = 1
ROW_GAP_TO_MERGE = 2
MIN_LINE_HEIGHT = 5

# Порог для символов в косом вертикальном профиле.
COL_THRESHOLD = 1
COL_GAP_TO_MERGE = 1
MIN_SYMBOL_WIDTH = 2

# Оценка наклона: обычная вертикаль = 90 градусов,
# если символы "стоят" примерно под 78 градусов, то отклонение 12 градусов.
SLANT_DEGREES = 0.0

# Если знак наклона неизвестен, код попробует оба направления и выберет лучшее.
TRY_BOTH_SLANT_DIRECTIONS = True
DEFAULT_SLANT_DIRECTION = 1   # 1 или -1

# Небольшой отступ при рисовании рамок вокруг найденных символов.
BOX_PADDING = 1


@dataclass
class Interval:
    start: int
    end: int  # inclusive

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


def load_binary_image(path: Path) -> np.ndarray:
    """
    Загружает изображение и возвращает бинарную матрицу:
    чёрный пиксель -> 1
    белый пиксель -> 0
    """
    img = Image.open(path).convert('L')
    arr = np.array(img)
    binary = (arr < 128).astype(np.uint8)
    return binary


def crop_to_content(binary: np.ndarray, padding: int = 0) -> np.ndarray:
    ys, xs = np.where(binary > 0)
    if len(xs) == 0:
        return binary.copy()

    y1 = max(0, ys.min() - padding)
    y2 = min(binary.shape[0] - 1, ys.max() + padding)
    x1 = max(0, xs.min() - padding)
    x2 = min(binary.shape[1] - 1, xs.max() + padding)
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
    """
    Возвращает интервалы, где профиль > threshold.
    Маленькие промежутки между интервалами можно склеить через gap_to_merge.
    """
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

    merged = [it for it in merged if it.length >= min_length]
    return merged


def save_profile_plot(
    values: np.ndarray,
    path: Path,
    title: str,
    xlabel: str,
    ylabel: str,
    horizontal: bool = False,
) -> None:
    values = np.asarray(values, dtype=int)

    if horizontal:
        fig_height = max(4, len(values) * 0.18)
        fig, ax = plt.subplots(figsize=(7, fig_height))
        y = np.arange(len(values))
        ax.barh(y, values)
        ax.invert_yaxis()
        ax.set_ylabel(xlabel)
        ax.set_xlabel(ylabel)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        fig_width = max(7, len(values) * 0.12)
        fig, ax = plt.subplots(figsize=(fig_width, 4))
        x = np.arange(len(values))
        ax.bar(x, values)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def slanted_x_for_pixel(x: int, y: int, h: int, slant_direction: int, slant_degrees: float) -> int:
    """
    Преобразование для косого вертикального профиля.
    Мы не искажаем изображение явно, а считаем координату x' после сдвига строки.
    Это эквивалентно сдвигу строк, который в методичке предложен для курсива.
    """
    shear = math.tan(math.radians(slant_degrees))
    shift = int(round((h - 1 - y) * shear * slant_direction))
    return x + shift


def build_slanted_vertical_profile(
    line_binary: np.ndarray,
    slant_direction: int,
    slant_degrees: float,
) -> Tuple[np.ndarray, int, np.ndarray]:
    """
    Возвращает:
    - сам косой вертикальный профиль,
    - минимальную x' координату,
    - матрицу x' для всех пикселей строки.
    """
    h, w = line_binary.shape
    ys, xs = np.indices((h, w))

    x_slanted = np.zeros_like(xs, dtype=int)
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
    """
    Чем больше столбцов с малыми значениями и чем выше дисперсия профиля,
    тем лучше профиль разделяет символы.
    """
    low_columns = int((profile <= threshold).sum())
    variance = float(profile.var())
    return low_columns, variance


def choose_best_slant_direction(line_binary: np.ndarray) -> int:
    if not TRY_BOTH_SLANT_DIRECTIONS:
        return DEFAULT_SLANT_DIRECTION

    candidates = []
    for direction in (-1, 1):
        profile, _, _ = build_slanted_vertical_profile(line_binary, direction, SLANT_DEGREES)
        score = profile_separation_score(profile, COL_THRESHOLD)
        candidates.append((score, direction))

    candidates.sort(reverse=True)
    return candidates[0][1]


def intervals_from_slanted_profile(profile: np.ndarray) -> List[Interval]:
    return extract_intervals_from_profile(
        profile=profile,
        threshold=COL_THRESHOLD,
        gap_to_merge=COL_GAP_TO_MERGE,
        min_length=MIN_SYMBOL_WIDTH,
    )


def intervals_to_bboxes_on_original_line(
    line_binary: np.ndarray,
    intervals: Iterable[Interval],
    min_xp: int,
    x_slanted: np.ndarray,
    line_y_offset: int,
) -> List[BBox]:
    """
    Переводит интервалы в косом пространстве x' обратно в обычные рамки на исходной строке.
    """
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


def draw_bboxes_on_image(binary: np.ndarray, bboxes: List[BBox], path: Path) -> None:
    img = Image.fromarray((1 - binary) * 255).convert('RGB')
    draw = ImageDraw.Draw(img)

    for i, box in enumerate(bboxes, start=1):
        draw.rectangle((box.x1, box.y1, box.x2, box.y2), outline=(255, 0, 0), width=1)
        draw.text((box.x1, max(0, box.y1 - 10)), str(i), fill=(0, 0, 255))

    img.save(path)


def save_line_image(binary: np.ndarray, line: Interval, path: Path) -> None:
    line_img = binary[line.start:line.end + 1, :]
    save_binary_image(line_img, path)


def crop_box(binary: np.ndarray, box: BBox) -> np.ndarray:
    return binary[box.y1:box.y2 + 1, box.x1:box.x2 + 1]


def md_path(path: Path) -> str:
    return './' + path.relative_to(BASE_DIR).as_posix()

def cleanup_previous_results() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

def create_report(lines: List[Interval], boxes: List[BBox]) -> None:
    report_lines: list[str] = []
    report_lines.extend([
        '# Лабораторная работа №6. Сегментация текста',
        '',
        '**Алфавит:** кириллица заглавная  ',
        '**Исходное изображение:** `phrase.bmp`',
        '',
        '---',
        '',
        '## Используемые методы',
        '',
        'Изображение загружается как монохромное: чёрный пиксель принимается за 1, белый пиксель — за 0.',
        '',
        'Для выделения строк строится горизонтальный профиль изображения: сумма чёрных пикселей по каждой строке `Y`.',
        '',
        'Для выделения символов внутри каждой строки строится косой вертикальный профиль. Он нужен для наклонного шрифта: пиксельные строки сдвигаются, после чего символы лучше разделяются по вертикальным проекциям.',
        '',
        'Сегментация выполняется по профилям с прореживанием: разрез допускается не только при нулевом профиле, но и при малых значениях профиля.',
        '',
        '---',
        '',
        '## 1. Исходное изображение',
        '',
        f'![]({md_path(SOURCE_COPY_PATH)})',
        '',
        '---',
        '',
        '## 2. Горизонтальный профиль и выделение строк',
        '',
        f'![]({md_path(HORIZONTAL_PROFILE_PATH)})',
        '',
        '| № строки | Начало Y | Конец Y | Высота |',
        '|---:|---:|---:|---:|',
    ])

    for i, line in enumerate(lines, start=1):
        report_lines.append(f'| {i} | {line.start} | {line.end} | {line.length} |')

    report_lines.extend([
        '',
        '---',
        '',
        '## 3. Косые вертикальные профили строк',
        '',
    ])

    for i, _line in enumerate(lines, start=1):
        report_lines.extend([
            f'### Строка {i}',
            '',
            f'![]({md_path(OUT_DIR / f"line_{i}.bmp")})',
            '',
            f'![]({md_path(PROFILES_OUT_DIR / f"vertical_profile_line_{i}.png")})',
            '',
        ])

    report_lines.extend([
        '---',
        '',
        '## 4. Результат сегментации символов',
        '',
        f'![]({md_path(SEGMENTED_PATH)})',
        '',
        'Координаты обрамляющих прямоугольников упорядочены в порядке чтения: слева направо, сверху вниз.',
        '',
        '| № | x1 | y1 | x2 | y2 | Ширина | Высота |',
        '|---:|---:|---:|---:|---:|---:|---:|',
    ])

    for i, box in enumerate(boxes, start=1):
        report_lines.append(f'| {i} | {box.x1} | {box.y1} | {box.x2} | {box.y2} | {box.width} | {box.height} |')

    report_lines.extend([
        '',
        '---',
        '',
        '## 5. Вырезанные символы и их профили',
        '',
    ])

    for i, _box in enumerate(boxes, start=1):
        report_lines.extend([
            f'### Символ {i}',
            '',
            f'![]({md_path(SYMBOLS_OUT_DIR / f"symbol_{i:02d}.bmp")})',
            '',
            '| Профиль X | Профиль Y |',
            '|:---:|:---:|',
            f'| ![]({md_path(PROFILES_OUT_DIR / f"symbol_{i:02d}_profile_x.png")}) | ![]({md_path(PROFILES_OUT_DIR / f"symbol_{i:02d}_profile_y.png")}) |',
            '',
        ])


    REPORT_PATH.write_text('\n'.join(report_lines), encoding='utf-8')


def main() -> None:
    IMGS_DIR.mkdir(parents=True, exist_ok=True)

    cleanup_previous_results()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SYMBOLS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    SYMBOLS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f'Не найден файл {INPUT_PATH}.\n'
            'Положи исходное изображение в папку img под именем phrase.bmp'
        )

    source_binary = load_binary_image(INPUT_PATH)
    binary = crop_to_content(source_binary, padding=CROP_PADDING) if AUTO_CROP else source_binary
    save_binary_image(binary, SOURCE_COPY_PATH)

    # 1. Горизонтальный профиль и строки
    h_profile = horizontal_profile(binary)
    save_profile_plot(
        values=h_profile,
        path=HORIZONTAL_PROFILE_PATH,
        title='Горизонтальный профиль изображения',
        xlabel='Y',
        ylabel='Сумма чёрных пикселей',
        horizontal=True,
    )

    lines = extract_intervals_from_profile(
        profile=h_profile,
        threshold=ROW_THRESHOLD,
        gap_to_merge=ROW_GAP_TO_MERGE,
        min_length=MIN_LINE_HEIGHT,
    )

    if not lines:
        raise RuntimeError('Не удалось выделить строки по горизонтальному профилю.')

    all_boxes: List[BBox] = []

    # 2. Для каждой строки — косой вертикальный профиль и сегментация символов
    for line_idx, line in enumerate(lines, start=1):
        line_binary = binary[line.start:line.end + 1, :]

        save_line_image(binary, line, OUT_DIR / f'line_{line_idx}.bmp')

        slant_direction = choose_best_slant_direction(line_binary)
        v_profile, min_xp, x_slanted = build_slanted_vertical_profile(
            line_binary=line_binary,
            slant_direction=slant_direction,
            slant_degrees=SLANT_DEGREES,
        )

        sign = '+' if slant_direction > 0 else '-'
        save_profile_plot(
            values=v_profile,
            path=PROFILES_OUT_DIR / f'vertical_profile_line_{line_idx}.png',
            title=f'Косой вертикальный профиль строки {line_idx} (наклон {sign}{SLANT_DEGREES:.1f}°)',
            xlabel="X'",
            ylabel='Сумма чёрных пикселей',
            horizontal=False,
        )

        symbol_intervals = intervals_from_slanted_profile(v_profile)
        boxes = intervals_to_bboxes_on_original_line(
            line_binary=line_binary,
            intervals=symbol_intervals,
            min_xp=min_xp,
            x_slanted=x_slanted,
            line_y_offset=line.start,
        )

        boxes.sort(key=lambda b: b.x1)
        all_boxes.extend(boxes)

    # 3. Итоговая картинка с прямоугольниками
    #all_boxes.sort(key=lambda b: (b.y1, b.x1))
    draw_bboxes_on_image(binary, all_boxes, SEGMENTED_PATH)

    # 4. Вырезанные символы и профили каждого символа
    for i, box in enumerate(all_boxes, start=1):
        symbol_img = crop_box(binary, box)
        symbol_path = SYMBOLS_OUT_DIR / f'symbol_{i:02d}.bmp'
        save_binary_image(symbol_img, symbol_path)

        px = vertical_profile(symbol_img)
        py = horizontal_profile(symbol_img)
        save_profile_plot(
            values=px,
            path=PROFILES_OUT_DIR / f'symbol_{i:02d}_profile_x.png',
            title=f'Профиль X символа {i}',
            xlabel='X',
            ylabel='Сумма чёрных пикселей',
            horizontal=False,
        )
        save_profile_plot(
            values=py,
            path=PROFILES_OUT_DIR / f'symbol_{i:02d}_profile_y.png',
            title=f'Профиль Y символа {i}',
            xlabel='Y',
            ylabel='Сумма чёрных пикселей',
            horizontal=True,
        )

    create_report(lines, all_boxes)

    print('Готово.')
    print(f'Исходное изображение: {INPUT_PATH}')
    print(f'Горизонтальный профиль: {HORIZONTAL_PROFILE_PATH}')
    print(f'Сегментация символов: {SEGMENTED_PATH}')
    print(f'Отчёт: {REPORT_PATH}')
    print(f'Найдено строк: {len(lines)}')
    print(f'Найдено символов: {len(all_boxes)}')


if __name__ == '__main__':
    main()
