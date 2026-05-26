from pathlib import Path
import shutil
from typing import Iterable

import numpy as np
from PIL import Image


# Полный путь к папке лабораторной работы
BASE_DIR = Path('/home/ilya/OAVI/lab2')
IMGS_DIR = BASE_DIR / 'img'
OUT_DIR = BASE_DIR / 'result'
REPORT_PATH = BASE_DIR / 'result.md'

# Для обесцвечивания возьмем sRGB-взвешивание
# Y = 0.2126R + 0.7152G + 0.0722B
# Можно заменить на BT.601: 0.3, 0.59, 0.11
R_COEF = 0.299
G_COEF = 0.587
B_COEF = 0.114

# Вариант 4: адаптивная бинаризация Брэдли и Рота
# По таблице варианта используются окна 3x3 и 25x25
WINDOW_SIZES = [3, 25]
T_PERCENT = 15.0  # параметр t = 15%, как в классическом методе Bradley-Roth

# Имена исходных изображений. Файлы должны лежать в папке img.
EXPECTED_FILES = [
    'cartoon.png',
    'xray.png',
    'map.png',
    'text1.png',
    'text2.png',
]

IMAGE_TITLES = {
    'cartoon': 'Мультфильм',
    'xray': 'Рентгеновский снимок',
    'map': 'Контурная карта',
    'text1': 'Текст 1',
    'text2': 'Текст 2',
}

CONCLUSIONS = {
    'cartoon': 'Для cartoon лучше подходит окно $25 \\times 25$. Линии силуета не потерялись и образ читаем.',
    'xray': 'Для xray результат слабый. Окно $3 \\times 3$ как и в случае с мультком потеряли целостность. А окно $25 \\times 25$ увеличило все линии и потерло внутренние детали.',
    'map': 'Для map показало себя хорошо.  Окно $3 \\times 3$ избавилось от меридианы и широты, а контур берегов остались. А окно $25 \\times 25$ наоборот усилило все линии и стало легче понимать пересечение стран с меридианами и широтами.',
    'text1': 'Для text1 окно $25 \\times 25$ отработало неодназначно: текст местами стал более читаемый, а в других потерялся.',
    'text2': 'Для text2 оба окна отработали плохо. Повысилась зернистоть и текст стал почти нечитаем.',
}


def load_rgb_image(path: Path) -> np.ndarray:
    """Load image as RGB uint8 array of shape (H, W, 3)."""
    img = Image.open(path).convert('RGB')
    return np.array(img, dtype=np.uint8)


def rgb_to_grayscale(rgb: np.ndarray) -> np.ndarray:
    """
    Convert RGB image to grayscale using weighted averaging.
    No library grayscale conversion is used.
    """
    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)

    y = R_COEF * r + G_COEF * g + B_COEF * b
    gray = np.clip(np.round(y), 0, 255).astype(np.uint8)
    return gray


def integral_image(gray: np.ndarray) -> np.ndarray:
    """
    Build integral image with additional zero row and zero column.
    This is not a library binarization function; it is only a fast way to sum windows.
    """
    gray_f = gray.astype(np.float64)
    integral = np.zeros((gray.shape[0] + 1, gray.shape[1] + 1), dtype=np.float64)
    integral[1:, 1:] = gray_f.cumsum(axis=0).cumsum(axis=1)
    return integral


def rect_sum(integral: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> float:
    """
    Sum pixels in rectangle [x1:x2, y1:y2), where x is column and y is row.
    """
    return float(integral[y2, x2] - integral[y1, x2] - integral[y2, x1] + integral[y1, x1])


def bradley_roth_binarization(gray: np.ndarray, window_size: int, t_percent: float = 15.0) -> np.ndarray:
    """
    Adaptive Bradley-Roth binarization.

    For each pixel, the local mean m is calculated in a square window D x D.
    Threshold:
        T = m * (1 - t / 100)

    Decision rule:
        if I(x, y) <= T -> black (0)
        else -> white (255)
    """
    if window_size % 2 == 0:
        raise ValueError('window_size must be odd')

    h, w = gray.shape
    radius = window_size // 2
    integ = integral_image(gray)
    out = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        y1 = max(0, y - radius)
        y2 = min(h, y + radius + 1)

        for x in range(w):
            x1 = max(0, x - radius)
            x2 = min(w, x + radius + 1)

            count = (x2 - x1) * (y2 - y1)
            local_sum = rect_sum(integ, x1, y1, x2, y2)
            mean = local_sum / count
            threshold = mean * (1.0 - t_percent / 100.0)

            out[y, x] = 0 if gray[y, x] <= threshold else 255

    return out


def save_grayscale_bmp(gray: np.ndarray, path: Path) -> None:
    Image.fromarray(gray, mode='L').save(path, format='BMP')


def save_binary_bmp(binary: np.ndarray, path: Path) -> None:
    Image.fromarray(binary, mode='L').save(path, format='BMP')


def process_one_image(path: Path) -> str:
    name = path.stem
    image_out_dir = OUT_DIR / name
    image_out_dir.mkdir(parents=True, exist_ok=True)

    rgb = load_rgb_image(path)
    gray = rgb_to_grayscale(rgb)

    Image.fromarray(rgb, mode='RGB').save(image_out_dir / f'{name}_original.png')
    save_grayscale_bmp(gray, image_out_dir / f'{name}_gray.bmp')

    for window_size in WINDOW_SIZES:
        binary = bradley_roth_binarization(
            gray,
            window_size=window_size,
            t_percent=T_PERCENT,
        )
        save_binary_bmp(binary, image_out_dir / f'{name}_bradley_{window_size}x{window_size}.bmp')

    print(f'[OK] {name}')
    return name


def collect_input_paths() -> list[Path]:
    paths: list[Path] = []

    for filename in EXPECTED_FILES:
        path = IMGS_DIR / filename
        if path.exists():
            paths.append(path)
        else:
            print(f'[WARN] File not found: {path}')

    # Если пользователь положил другие png/bmp, тоже обработаем их после основных файлов.
    known = {p.resolve() for p in paths}
    for path in sorted(list(IMGS_DIR.glob('*.png')) + list(IMGS_DIR.glob('*.bmp'))):
        if path.resolve() not in known:
            paths.append(path)

    if not paths:
        raise FileNotFoundError(f'No PNG/BMP images found in {IMGS_DIR}')

    return paths


def md_path(path: Path) -> str:
    """Return markdown path relative to report.md location."""
    return './' + path.relative_to(BASE_DIR).as_posix()


def create_report(processed_names: Iterable[str]) -> None:
    names = list(processed_names)

    lines: list[str] = []
    lines.extend([
        '# Лабораторная работа №2',
        '## Обесцвечивание и бинаризация растровых изображений',
        '',
        '**Вариант:** 4',
        '',
        '---',
        '',
        '## Результаты обработки',
        '',
        '### 1. Сравнение исходных цветных и полутоновых изображений',
        '',
        'Для каждого примера слева показано исходное цветное изображение, справа — полученное полутоновое изображение.',
        '',
        'Для каждого исходного цветного изображения выполнялось взвешенное усреднение каналов:',
        '',
        '$$',
        r'Y = 0.2126 \cdot R + 0.7152 \cdot G + 0.0722 \cdot B',
        '$$',
        '',
    ])

    for name in names:
        title = IMAGE_TITLES.get(name, name)
        original = md_path(OUT_DIR / name / f'{name}_original.png')
        gray = md_path(OUT_DIR / name / f'{name}_gray.bmp')
        lines.extend([
            f'| **{title}** | |',
            '|:---:|:---:|',
            f'| ![]({original}) | ![]({gray}) |',
            '',
        ])

    lines.extend([
        '---',
        '',
        '### 2. Бинаризация изображений методом Брэдли-Рота',
        '',
        'Для бинаризации использовался метод Брэдли-Рота. В варианте 4 выполняется обработка с окнами $3 \\times 3$ и $25 \\times 25$.',
        '',
        'Метод основан на вычислении локального среднего значения яркости в окне вокруг текущего пикселя.',
        '',
        'Порог вычисляется по формуле:',
        '',
        '$$',
        r'T(x,y) = m(x,y) \cdot \left(1 - \frac{t}{100}\right)',
        '$$',
        '',
        'где:',
        '- $m(x,y)$ — локальное среднее значение яркости в окне;',
        f'- $t = {int(T_PERCENT)}$% — коэффициент чувствительности метода;',
        '- если яркость пикселя меньше или равна порогу, пиксель становится чёрным;',
        '- иначе пиксель становится белым.',
        '',
    ])

    for idx, name in enumerate(names, start=1):
        title = IMAGE_TITLES.get(name, name)
        gray = md_path(OUT_DIR / name / f'{name}_gray.bmp')
        br3 = md_path(OUT_DIR / name / f'{name}_bradley_3x3.bmp')
        br25 = md_path(OUT_DIR / name / f'{name}_bradley_25x25.bmp')

        lines.extend([
            f'### 2.{idx}. Эксперимент с размером окна для `{name}`',
            '',
            f'Для изображения `{name}` были рассмотрены два размера окна:',
            '- $3 \\times 3$',
            '- $25 \\times 25$',
            '',
            '#### Исходное полутоновое изображение',
            '',
            f'![]({gray})',
            '',
            '#### Результаты бинаризации',
            '',
            '**Окно $3 \\times 3$**',
            '',
            f'![]({br3})',
            '',
            '**Окно $25 \\times 25$**',
            '',
            f'![]({br25})',
            '',
            'Вывод:',
            CONCLUSIONS.get(
                name,
                f'Для изображения `{name}` результат зависит от размера локального окна. '
                f'Малое окно сильнее учитывает мелкие локальные детали, а окно $25 \\times 25$ '
                f'сглаживает влияние отдельных пикселей и лучше учитывает общий фон.'
            ),
            '',
            '---',
            '',
        ])

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'[OK] report -> {REPORT_PATH}')




def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    input_paths = collect_input_paths()

    print('Processing images:')
    processed_names = []
    for path in input_paths:
        processed_names.append(process_one_image(path))

    create_report(processed_names)
    print('\nDone.')


if __name__ == '__main__':
    main()
