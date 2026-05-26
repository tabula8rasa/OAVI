from pathlib import Path
import shutil
from typing import Iterable

import numpy as np
from PIL import Image


# Полный путь к папке лабораторной работы
# Если папка называется иначе, поменяй только эту строку.
BASE_DIR = Path('/home/ilya/OAVI/lab4')
IMGS_DIR = BASE_DIR / 'img'
OUT_DIR = BASE_DIR / 'result'
REPORT_PATH = BASE_DIR / 'result.md'

# Преобразование RGB в полутон по BT.601
R_COEF = 0.299
G_COEF = 0.587
B_COEF = 0.114

# Вариант 4: оператор Собеля 3x3, модуль градиента G = |Gx| + |Gy|
METHOD_NAME = 'Оператор Собеля 3×3'
VARIANT = 4
THRESHOLDS = [10, 20, 30, 40, 50, 60, 70]

# Имена исходных изображений. Файлы должны лежать в папке img.
EXPECTED_FILES = [
    'text1.png',
    'text2.png',
    'text3.png',
    'text4.png',
    'text5.png',
]

IMAGE_TITLES = {
    'text1': 'Текст 1',
    'text2': 'Текст 2',
    'text3': 'Текст 3',
    'text4': 'Текст 4',
    'text5': 'Текст 5',
}

# Выводы можно редактировать отдельно для каждого изображения.
CONCLUSIONS = {
    'text1': 'Итог: для первого изображения оптимальным можно считать T=20, так как при меньших значениях высокий уровень шума, а при значениях выше пропадает четкоть букв.',
    'text2': 'Итог: для второго изображения алгоритм показал себя ужасно при всех значениях T. Высокая зернистость мешает разобрать какие либо буквы до T=60 - после уже можно увидеть некоторые из них.',
    'text3': 'Итог: для третьего изображения оператор Собеля показал аналогичную ситуацию с фото 2',
    'text4': 'Итог: для четвертого изображения оптимальным порогом является T=70 где появляется баланс между сохранением полезных границ и подавлением лишнего шума.',
    'text5': 'Итог: для пятого изображения приемлимый результат получается начиная с T=50 и улучшается по мере увеличения T.',
}


# ------------------------------------------------------------
# Преобразование RGB в полутон (взвешенное)
# ------------------------------------------------------------
def rgb_to_grayscale(img_array: np.ndarray) -> np.ndarray:
    r, g, b = img_array[..., 0], img_array[..., 1], img_array[..., 2]
    gray = R_COEF * r + G_COEF * g + B_COEF * b
    return np.clip(gray, 0, 255).astype(np.uint8)


# ------------------------------------------------------------
# Оператор Собеля 3×3
# ------------------------------------------------------------
def sobel_gradients(gray: np.ndarray):
    """
    Вычисляет Gx, Gy и модуль градиента G = |Gx| + |Gy|.
    Возвращает (Gx, Gy, G) – массивы float (ненормализованные).
    """
    h, w = gray.shape

    # Ядра Собеля для варианта 4
    kernel_x = np.array([[-1, 0, 1],
                         [-2, 0, 2],
                         [-1, 0, 1]], dtype=np.float32)
    kernel_y = np.array([[1, 2, 1],
                         [0, 0, 0],
                         [-1, -2, -1]], dtype=np.float32)

    # Дополнение отражением
    padded = np.pad(gray, 1, mode='reflect')
    Gx = np.zeros((h, w), dtype=np.float32)
    Gy = np.zeros((h, w), dtype=np.float32)

    for i in range(h):
        for j in range(w):
            window = padded[i:i + 3, j:j + 3]
            Gx[i, j] = np.sum(window * kernel_x)
            Gy[i, j] = np.sum(window * kernel_y)

    G = np.abs(Gx) + np.abs(Gy)
    return Gx, Gy, G


# ------------------------------------------------------------
# Нормализация в [0, 255]
# ------------------------------------------------------------
def normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    """Линейное растяжение до [0, 255] и преобразование в uint8."""
    min_val = arr.min()
    max_val = arr.max()
    if max_val - min_val < 1e-6:
        return np.zeros_like(arr, dtype=np.uint8)
    norm = (arr - min_val) / (max_val - min_val) * 255
    return norm.astype(np.uint8)


# ------------------------------------------------------------
# Бинаризация
# ------------------------------------------------------------
def binarize(arr: np.ndarray, threshold: int) -> np.ndarray:
    return np.where(arr >= threshold, 255, 0).astype(np.uint8)


# ------------------------------------------------------------
# Основная обработка одного изображения
# ------------------------------------------------------------
def process_image(input_path: Path) -> str:
    base = input_path.stem
    image_out_dir = OUT_DIR / base
    image_out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Цветное исходное
    img_color = Image.open(input_path).convert('RGB')
    img_color.save(image_out_dir / f'{base}_original.png')

    # 2. Полутон
    gray = rgb_to_grayscale(np.array(img_color))
    Image.fromarray(gray).save(image_out_dir / f'{base}_gray.png')
    print(f'Сохранён полутон: {image_out_dir / f"{base}_gray.png"}')

    # 3. Градиенты
    Gx, Gy, G = sobel_gradients(gray)

    # 4. Нормализация
    Gx_norm = normalize_to_uint8(Gx)
    Gy_norm = normalize_to_uint8(Gy)
    G_norm = normalize_to_uint8(G)

    Image.fromarray(Gx_norm).save(image_out_dir / f'{base}_Gx.png')
    Image.fromarray(Gy_norm).save(image_out_dir / f'{base}_Gy.png')
    Image.fromarray(G_norm).save(image_out_dir / f'{base}_G.png')

    # 5. Бинаризация G с разными порогами
    for threshold in THRESHOLDS:
        binary = binarize(G_norm, threshold)
        Image.fromarray(binary).save(image_out_dir / f'{base}_binary_T{threshold}.png')

    print(f'[OK] {base}')
    return base


def collect_input_paths() -> list[Path]:
    paths: list[Path] = []

    for filename in EXPECTED_FILES:
        path = IMGS_DIR / filename
        if path.exists():
            paths.append(path)
        else:
            print(f'[WARN] Файл не найден: {path}')

    known = {p.resolve() for p in paths}
    for path in sorted(list(IMGS_DIR.glob('*.png')) + list(IMGS_DIR.glob('*.bmp'))):
        if path.resolve() not in known:
            paths.append(path)

    if not paths:
        raise FileNotFoundError(f'No PNG/BMP images found in {IMGS_DIR}')

    return paths


def md_path(path: Path) -> str:
    """Return markdown path relative to result.md location."""
    return './' + path.relative_to(BASE_DIR).as_posix()


# ------------------------------------------------------------
# Генерация Markdown-отчёта
# ------------------------------------------------------------
def create_report(processed_names: Iterable[str]) -> None:
    names = list(processed_names)

    lines: list[str] = []
    lines.extend([
        '# Лабораторная работа №4. Выделение контуров на изображении',
        '',
        f'**Вариант:** {VARIANT}',
        f'**Метод:** {METHOD_NAME}',
        '',
        '---',
        '',
        '## Используемые методы',
        '',
        '### Преобразование в полутон',
        'Исходные цветные изображения переводятся в полутоновые по формуле взвешенного усреднения:',
        '',
        '$$',
        r'Y = 0.299 \cdot R + 0.587 \cdot G + 0.114 \cdot B',
        '$$',
        '',
        '### Оператор Собеля 3×3',
        'Ядра для вычисления горизонтальной и вертикальной составляющих градиента:',
        '',
        '$$',
        r'G_x = \begin{bmatrix}',
        r'-1 & 0 & 1 \\',
        r'-2 & 0 & 2 \\',
        r'-1 & 0 & 1',
        r'\end{bmatrix}, \quad',
        r'G_y = \begin{bmatrix}',
        r'1 & 2 & 1 \\',
        r'0 & 0 & 0 \\',
        r'-1 & -2 & -1',
        r'\end{bmatrix}',
        '$$',
        '',
        'Модуль градиента вычисляется как сумма модулей:',
        '',
        '$$',
        r'|G| = |G_x| + |G_y|',
        '$$',
        '',
        '### Нормализация',
        'Каждая градиентная матрица линейно растягивается в диапазон [0, 255] для визуализации.',
        '',
        '### Бинаризация',
        'Для выделения контуров применяется пороговая обработка: пиксели со значением выше порога становятся белыми, остальные — чёрными. Для каждого изображения приведены результаты бинаризации при порогах 10, 20, 30, 40, 50, 60, 70.',
        '',
        '---',
        '',
        '## Результаты',
        '',
        '### 1. Исходные и полутоновые изображения',
        '',
        '| № | Исходное (цветное) | Полутоновое |',
        '|---|--------------------|-------------|',
    ])

    for name in names:
        original = md_path(OUT_DIR / name / f'{name}_original.png')
        gray = md_path(OUT_DIR / name / f'{name}_gray.png')
        lines.append(f'| **{name}** | ![{name}]({original}) | ![{name}_gray]({gray}) |')

    lines.extend([
        '',
        '---',
        '',
        '### 2. Градиентные матрицы $G_x$, $G_y$ и модуль градиента $G$ (нормализованные)',
        '',
    ])

    for name in names:
        gx = md_path(OUT_DIR / name / f'{name}_Gx.png')
        gy = md_path(OUT_DIR / name / f'{name}_Gy.png')
        g = md_path(OUT_DIR / name / f'{name}_G.png')
        lines.extend([
            f'#### {name}',
            '| $G_x$ | $G_y$ | $G$ |',
            '|---------|---------|-------|',
            f'| ![{name}_Gx]({gx}) | ![{name}_Gy]({gy}) | ![{name}_G]({g}) |',
            '',
        ])

    lines.extend([
        '---',
        '',
        '### 3. Бинаризация модуля градиента $G$ (различные пороги)',
        '',
        'Для каждого изображения показаны результаты бинаризации при порогах 10, 20, 30, 40, 50, 60 и 70.',
        '',
    ])

    for name in names:
        lines.extend([
            f'#### {name}',
            '',
            '| T=10 | T=20 |',
            '|------|------|',
            f'| ![{name}_binary_T10]({md_path(OUT_DIR / name / f"{name}_binary_T10.png")}) | ![{name}_binary_T20]({md_path(OUT_DIR / name / f"{name}_binary_T20.png")}) |',
            '',
            '| T=30 | T=40 |',
            '|------|------|',
            f'| ![{name}_binary_T30]({md_path(OUT_DIR / name / f"{name}_binary_T30.png")}) | ![{name}_binary_T40]({md_path(OUT_DIR / name / f"{name}_binary_T40.png")}) |',
            '',
            '| T=50 | T=60 |',
            '|------|------|',
            f'| ![{name}_binary_T50]({md_path(OUT_DIR / name / f"{name}_binary_T50.png")}) | ![{name}_binary_T60]({md_path(OUT_DIR / name / f"{name}_binary_T60.png")}) |',
            '',
            '| T=70 |',
            '|------|',
            f'| ![{name}_binary_T70]({md_path(OUT_DIR / name / f"{name}_binary_T70.png")}) |',
            '',
            CONCLUSIONS.get(name, 'Итог: оптимальный порог подбирается опытным путём по качеству выделения контуров.'),
            '',
        ])

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'[OK] report -> {REPORT_PATH}')


# ------------------------------------------------------------
# Основная программа
# ------------------------------------------------------------
def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    input_paths = collect_input_paths()

    print('Processing images:')
    processed_names = []
    for path in input_paths:
        processed_names.append(process_image(path))

    create_report(processed_names)
    print('\nDone.')


if __name__ == '__main__':
    main()
