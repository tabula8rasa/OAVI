from pathlib import Path
import csv
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


# ------------------------------------------------------------
# Полный путь к папке лабораторной работы
# ------------------------------------------------------------
BASE_DIR = Path('/home/ilya/OAVI/lab5')
FONTS_DIR = BASE_DIR / 'fonts'
SYMBOLS_DIR = BASE_DIR / 'symbols'
PROFILES_DIR = BASE_DIR / 'profiles'
CSV_PATH = BASE_DIR / 'scalara.csv'
REPORT_PATH = BASE_DIR / 'result.md'

# Вариант 4: кириллица заглавная
ALPHABET_NAME = 'Кириллица заглавная'
ALPHABET = list('АБВГДЕЖЅЗИIКЛМНОПРСТѸФХЦЧШЩЪЫЬѢЮѴѮѰѠѲѦѪ')
VARIANT = 4
FONT_SIZE = 52

BACKGROUND = 255  # white
FOREGROUND = 0    # black
PADDING = 20
THRESHOLD = 200   # threshold for symbol binarization


# ------------------------------------------------------------
# Генерация эталонных изображений символов
# ------------------------------------------------------------
def find_font_path() -> Path:
    fonts = sorted(list(FONTS_DIR.glob('*.ttf')) + list(FONTS_DIR.glob('*.otf')))
    if not fonts:
        raise FileNotFoundError(
            f'В папке {FONTS_DIR} не найден файл шрифта .ttf или .otf.\n'
            'Положи туда шрифт с поддержкой кириллицы, например times.ttf, arial.ttf или DejaVuSerif.ttf.'
        )
    return fonts[0]


def trim_white(img: Image.Image) -> Image.Image:
    """Crop outer white margins."""
    inv = ImageChops.invert(img)
    bbox = inv.getbbox()
    if bbox is None:
        return img
    return img.crop(bbox)


def binarize_symbol(img: Image.Image, threshold: int = THRESHOLD) -> Image.Image:
    """Convert grayscale image to clean black/white."""
    return img.point(lambda p: BACKGROUND if p > threshold else FOREGROUND, mode='L')


def render_symbol(symbol: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    """Render one symbol to an image and trim white margins."""
    dummy = Image.new('L', (1, 1), BACKGROUND)
    draw = ImageDraw.Draw(dummy)

    bbox = draw.textbbox((0, 0), symbol, font=font)
    if bbox is None:
        raise ValueError(f'Не удалось вычислить bbox для символа {symbol!r}')

    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top

    img = Image.new('L', (width + 2 * PADDING, height + 2 * PADDING), BACKGROUND)
    draw = ImageDraw.Draw(img)
    draw.text((PADDING - left, PADDING - top), symbol, font=font, fill=FOREGROUND)

    img = binarize_symbol(img)
    img = trim_white(img)
    return img


def make_filename(index: int, symbol: str) -> str:
    codepoint = f'U{ord(symbol):04X}'
    return f'{index:02d}_{codepoint}.png'


def generate_symbols() -> None:
    font_path = find_font_path()
    SYMBOLS_DIR.mkdir(parents=True, exist_ok=True)

    font = ImageFont.truetype(str(font_path), FONT_SIZE)

    for i, symbol in enumerate(ALPHABET, start=1):
        img = render_symbol(symbol, font)
        filename = make_filename(i, symbol)
        out_path = SYMBOLS_DIR / filename
        img.save(out_path)
        print(f'Saved symbol: {out_path}')

    print(f'Использованный шрифт: {font_path.name}')


# ------------------------------------------------------------
# Расчёт признаков
# ------------------------------------------------------------
def load_binary_image(path: Path) -> np.ndarray:
    """
    Load image and convert it to binary numpy array:
    black pixel -> 1
    white pixel -> 0
    """
    img = Image.open(path).convert('L')
    arr = np.array(img)
    binary = (arr < 128).astype(np.uint8)
    return binary


def split_quarters(binary: np.ndarray) -> dict[str, np.ndarray]:
    h, w = binary.shape
    mid_y = h // 2
    mid_x = w // 2

    return {
        'q1': binary[:mid_y, :mid_x],
        'q2': binary[:mid_y, mid_x:],
        'q3': binary[mid_y:, :mid_x],
        'q4': binary[mid_y:, mid_x:],
    }


def calc_weight(binary: np.ndarray) -> int:
    return int(binary.sum())


def calc_relative_weight(binary: np.ndarray) -> float:
    h, w = binary.shape
    area = h * w
    return float(binary.sum() / area) if area > 0 else 0.0


def calc_center_of_mass(binary: np.ndarray) -> tuple[float, float]:
    h, w = binary.shape
    weight = binary.sum()

    if weight == 0:
        return 0.0, 0.0

    ys, xs = np.indices((h, w))
    x_center = float((xs * binary).sum() / weight)
    y_center = float((ys * binary).sum() / weight)
    return x_center, y_center


def calc_normalized_center_of_mass(binary: np.ndarray, x_center: float, y_center: float) -> tuple[float, float]:
    h, w = binary.shape
    x_rel = float(x_center / (w - 1)) if w > 1 else 0.0
    y_rel = float(y_center / (h - 1)) if h > 1 else 0.0
    return x_rel, y_rel


def calc_inertia_moments(binary: np.ndarray, x_center: float, y_center: float) -> tuple[float, float]:
    h, w = binary.shape
    ys, xs = np.indices((h, w))

    ix = float((((ys - y_center) ** 2) * binary).sum())
    iy = float((((xs - x_center) ** 2) * binary).sum())
    return ix, iy


def calc_normalized_inertia_moments(binary: np.ndarray, ix: float, iy: float) -> tuple[float, float]:
    h, w = binary.shape
    denom = float((w ** 2) * (h ** 2))
    if denom == 0:
        return 0.0, 0.0
    return ix / denom, iy / denom


def calc_profiles(binary: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    profile_x = binary.sum(axis=0).astype(int)
    profile_y = binary.sum(axis=1).astype(int)
    return profile_x, profile_y


def save_profile_x(profile_x: np.ndarray, out_path: Path, title: str) -> None:
    x = np.arange(len(profile_x))

    fig_width = max(6, len(profile_x) * 0.18)
    fig, ax = plt.subplots(figsize=(fig_width, 4))

    ax.bar(x, profile_x)
    ax.set_title(title)
    ax.set_xlabel('X')
    ax.set_ylabel('Сумма чёрных пикселей')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_profile_y(profile_y: np.ndarray, out_path: Path, title: str) -> None:
    y = np.arange(len(profile_y))

    fig_height = max(4, len(profile_y) * 0.18)
    fig, ax = plt.subplots(figsize=(6, fig_height))

    ax.barh(y, profile_y)
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_ylabel('Y')
    ax.set_xlabel('Сумма чёрных пикселей')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def parse_symbol_from_filename(path: Path) -> tuple[str, str]:
    stem = path.stem
    parts = stem.split('_')
    if len(parts) < 2:
        return '', ''

    codepoint = parts[1]
    if codepoint.startswith('U'):
        symbol = chr(int(codepoint[1:], 16))
        return symbol, codepoint

    return '', ''


def features_for_image(path: Path) -> dict[str, object]:
    binary = load_binary_image(path)
    h, w = binary.shape

    total_weight = calc_weight(binary)
    total_rel_weight = calc_relative_weight(binary)
    quarters = split_quarters(binary)

    quarter_weights = {}
    quarter_rel_weights = {}
    for name, q in quarters.items():
        quarter_weights[name] = calc_weight(q)
        quarter_rel_weights[name] = calc_relative_weight(q)

    x_center, y_center = calc_center_of_mass(binary)
    x_rel, y_rel = calc_normalized_center_of_mass(binary, x_center, y_center)

    ix, iy = calc_inertia_moments(binary, x_center, y_center)
    ix_rel, iy_rel = calc_normalized_inertia_moments(binary, ix, iy)

    symbol, codepoint = parse_symbol_from_filename(path)

    return {
        'filename': path.name,
        'symbol': symbol,
        'codepoint': codepoint,
        'width': w,
        'height': h,
        'weight_total': total_weight,
        'weight_total_rel': total_rel_weight,
        'weight_q1': quarter_weights['q1'],
        'weight_q2': quarter_weights['q2'],
        'weight_q3': quarter_weights['q3'],
        'weight_q4': quarter_weights['q4'],
        'weight_q1_rel': quarter_rel_weights['q1'],
        'weight_q2_rel': quarter_rel_weights['q2'],
        'weight_q3_rel': quarter_rel_weights['q3'],
        'weight_q4_rel': quarter_rel_weights['q4'],
        'center_x': x_center,
        'center_y': y_center,
        'center_x_rel': x_rel,
        'center_y_rel': y_rel,
        'ix': ix,
        'iy': iy,
        'ix_rel': ix_rel,
        'iy_rel': iy_rel,
    }


def write_csv(rows: list[dict[str, object]], csv_path: Path) -> None:
    if not rows:
        return

    fieldnames = [
        'filename', 'symbol', 'codepoint', 'width', 'height',
        'weight_total', 'weight_total_rel',
        'weight_q1', 'weight_q2', 'weight_q3', 'weight_q4',
        'weight_q1_rel', 'weight_q2_rel', 'weight_q3_rel', 'weight_q4_rel',
        'center_x', 'center_y', 'center_x_rel', 'center_y_rel',
        'ix', 'iy', 'ix_rel', 'iy_rel',
    ]

    with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for row in rows:
            formatted = {}
            for key in fieldnames:
                value = row[key]
                if isinstance(value, float):
                    formatted[key] = f'{value:.6f}'
                else:
                    formatted[key] = value
            writer.writerow(formatted)


def process_symbols() -> list[dict[str, object]]:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in sorted(SYMBOLS_DIR.glob('*.png')):
        row = features_for_image(path)
        rows.append(row)

        binary = load_binary_image(path)
        profile_x, profile_y = calc_profiles(binary)
        stem = path.stem
        symbol = row['symbol'] or stem

        save_profile_x(profile_x, PROFILES_DIR / f'{stem}_profile_x.png', f'Профиль X: {symbol}')
        save_profile_y(profile_y, PROFILES_DIR / f'{stem}_profile_y.png', f'Профиль Y: {symbol}')

        print(f'Processed features: {path.name}')

    write_csv(rows, CSV_PATH)
    print(f'CSV saved: {CSV_PATH}')
    return rows


# ------------------------------------------------------------
# Генерация Markdown-отчёта
# ------------------------------------------------------------
def format_value(v: object) -> str:
    if v == '':
        return '—'
    if isinstance(v, float):
        return f'{v:.6f}'
    return str(v)


def make_symbol_block(row: dict[str, object], index: int) -> str:
    symbol = str(row['symbol']) if row['symbol'] else ALPHABET[index - 1]
    stem = Path(str(row['filename'])).stem

    return f'''## Символ {index} — {symbol}

### Изображение символа

![](./symbols/{stem}.png)

### Скалярные характеристики

| Признак | Значение |
|---|---:|
| Ширина изображения | {format_value(row['width'])} |
| Высота изображения | {format_value(row['height'])} |
| Общий вес чёрного | {format_value(row['weight_total'])} |
| Общий удельный вес | {format_value(row['weight_total_rel'])} |
| Вес 1-й четверти | {format_value(row['weight_q1'])} |
| Вес 2-й четверти | {format_value(row['weight_q2'])} |
| Вес 3-й четверти | {format_value(row['weight_q3'])} |
| Вес 4-й четверти | {format_value(row['weight_q4'])} |
| Удельный вес 1-й четверти | {format_value(row['weight_q1_rel'])} |
| Удельный вес 2-й четверти | {format_value(row['weight_q2_rel'])} |
| Удельный вес 3-й четверти | {format_value(row['weight_q3_rel'])} |
| Удельный вес 4-й четверти | {format_value(row['weight_q4_rel'])} |
| Координата центра тяжести X | {format_value(row['center_x'])} |
| Координата центра тяжести Y | {format_value(row['center_y'])} |
| Нормированная координата X | {format_value(row['center_x_rel'])} |
| Нормированная координата Y | {format_value(row['center_y_rel'])} |
| Осевой момент инерции Ix | {format_value(row['ix'])} |
| Осевой момент инерции Iy | {format_value(row['iy'])} |
| Нормированный момент инерции Ix | {format_value(row['ix_rel'])} |
| Нормированный момент инерции Iy | {format_value(row['iy_rel'])} |

### Профиль X

![](./profiles/{stem}_profile_x.png)

### Профиль Y

![](./profiles/{stem}_profile_y.png)

---
'''


def make_report(rows: list[dict[str, object]], font_name: str) -> str:
    alphabet_text = ' '.join(ALPHABET)
    report = f'''# Лабораторная работа №5. Выделение признаков символов

**Вариант:** {VARIANT}  
**Алфавит:** {ALPHABET_NAME}  
**Символы алфавита:** {alphabet_text}  
**Шрифт:** {font_name}  
**Кегль:** {FONT_SIZE}  

Скалярные характеристики символов автоматически получены программой и экспортированы из файла `scalara.csv`.  
Изображения символов берутся из папки `symbols`, графики профилей — из папки `profiles`.

---

'''

    for i, row in enumerate(rows, start=1):
        report += make_symbol_block(row, i)

    return report


def main() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    # Пересоздаём только результаты, папку fonts не трогаем.
    if SYMBOLS_DIR.exists():
        shutil.rmtree(SYMBOLS_DIR)
    if PROFILES_DIR.exists():
        shutil.rmtree(PROFILES_DIR)

    font_path = find_font_path()
    generate_symbols()
    rows = process_symbols()

    REPORT_PATH.write_text(make_report(rows, font_path.name), encoding='utf-8')
    print(f'Отчёт сохранён: {REPORT_PATH}')
    print('Готово.')


if __name__ == '__main__':
    main()
