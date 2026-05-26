from pathlib import Path
import numpy as np
from PIL import Image

# ============================================================
# Лабораторная работа №3
# Фильтрация изображений и морфологические операции
# Вариант 4: медианный фильтр, маска — равнина 3x3
# ============================================================

BASE_DIR = Path('/home/ilya/OAVI/lab3')
IMG_DIR = BASE_DIR / 'img'
RESULT_DIR = BASE_DIR / 'result'
REPORT_PATH = BASE_DIR / 'result.md'

# Исходные изображения, которые скрипт будет искать в папке img
INPUT_FILES = [
    'text1.png',
    'text2.png',
    'text3.png',
    'text4.png',
    'text5.png',
]

# Для варианта 4 используется плоская маска 3x3 и медиана 5/9
WINDOW_SIZE = 3
MEDIAN_RANK = 5


# ------------------------------------------------------------
# Преобразование RGB в полутон, библиотечное convert('L') не используется
# ------------------------------------------------------------
def rgb_to_grayscale(img_array: np.ndarray) -> np.ndarray:
    r = img_array[..., 0].astype(np.float32)
    g = img_array[..., 1].astype(np.float32)
    b = img_array[..., 2].astype(np.float32)

    gray = 0.299 * r + 0.587 * g + 0.114 * b
    return np.clip(np.round(gray), 0, 255).astype(np.uint8)


# ------------------------------------------------------------
# Медианная фильтрация с плоской маской 3x3
# ------------------------------------------------------------
def median_filter_plain(image: np.ndarray, window_size: int = 3) -> np.ndarray:
    """
    Медианный фильтр для полутонового изображения.
    Для варианта 4 используется маска-равнина 3x3:

        1 1 1
        1 1 1
        1 1 1

    В окне 3x3 всего 9 значений, медиана соответствует рангу 5/9.
    """
    if window_size % 2 == 0:
        raise ValueError('window_size must be odd')

    h, w = image.shape
    pad = window_size // 2
    padded = np.pad(image, pad, mode='reflect')
    result = np.zeros_like(image, dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            window = padded[y:y + window_size, x:x + window_size].flatten()
            sorted_values = np.sort(window)
            result[y, x] = sorted_values[len(sorted_values) // 2]

    return result


# ------------------------------------------------------------
# Сохранение изображений
# ------------------------------------------------------------
def save_gray(image: np.ndarray, path: Path) -> None:
    Image.fromarray(image, mode='L').save(path)


# ------------------------------------------------------------
# Обработка одного изображения
# ------------------------------------------------------------
def process_one_image(input_path: Path) -> dict[str, str]:
    base = input_path.stem

    img_color = Image.open(input_path).convert('RGB')
    img_array = np.array(img_color, dtype=np.uint8)

    gray = rgb_to_grayscale(img_array)
    filtered = median_filter_plain(gray, WINDOW_SIZE)

    diff = np.abs(gray.astype(np.int16) - filtered.astype(np.int16)).astype(np.uint8)
    diff_x10 = np.clip(diff.astype(np.uint16) * 10, 0, 255).astype(np.uint8)

    original_path = RESULT_DIR / f'{base}_original.png'
    gray_path = RESULT_DIR / f'{base}_gray.png'
    filtered_path = RESULT_DIR / f'{base}_median_3x3.png'
    diff_path = RESULT_DIR / f'{base}_diff.png'
    diff_x10_path = RESULT_DIR / f'{base}_diff_x10.png'

    img_color.save(original_path)
    save_gray(gray, gray_path)
    save_gray(filtered, filtered_path)
    save_gray(diff, diff_path)
    save_gray(diff_x10, diff_x10_path)

    print(f'[OK] {input_path.name}')
    print(f'     original -> {original_path}')
    print(f'     gray     -> {gray_path}')
    print(f'     filtered -> {filtered_path}')
    print(f'     diff     -> {diff_path}')
    print(f'     diff x10 -> {diff_x10_path}')

    return {
        'name': base,
        'original': f'./result/{original_path.name}',
        'gray': f'./result/{gray_path.name}',
        'filtered': f'./result/{filtered_path.name}',
        'diff': f'./result/{diff_path.name}',
        'diff_x10': f'./result/{diff_x10_path.name}',
    }


# ------------------------------------------------------------
# Создание Markdown-отчёта по структуре примера
# ------------------------------------------------------------
def make_report(items: list[dict[str, str]]) -> None:
    lines: list[str] = []

    lines.extend([
        '# Лабораторная работа №3',
        '## Фильтрация изображений и морфологические операции',
        '',
        '**Вариант:** 4',
        '',
        '---',
        '',
        'Фильтрация полутоновых изображений медианным фильтром с окном 3×3.',
        '',
        '$$\\text{Mask} =',
        '\\begin{bmatrix}',
        '1 & 1 & 1 \\\\',
        '1 & 1 & 1 \\\\',
        '1 & 1 & 1',
        '\\end{bmatrix}$$',
        '',
        '### Используемые методы',
        '- **Полутоновое преобразование**: взвешенное усреднение каналов RGB по формуле',
        '',
        '$$',
        'Y = 0.299 R + 0.587 G + 0.114 B',
        '$$',
        '',
        '- **Медианная фильтрация**: для каждого пикселя рассматривается окно 3×3. Значения яркости в окне сортируются, после чего центральному пикселю присваивается медианное значение. Для окна 3×3 медиана соответствует рангу 5/9.',
        '- **Разностное изображение**: модуль разности между исходным полутоновым изображением и отфильтрованным изображением. Для улучшения видимости слабых изменений применяется умножение на 10 с ограничением значений до 255.',
        '',
        '---',
        '',
        '## 1. Исходные цветные и полутоновые изображения',
        '',
    ])

    for item in items:
        name = item['name']
        lines.extend([
            f'| **{name}** | **{name}_gray** |',
            '|:---:|:---:|',
            f'| ![{name}]({item["original"]}) | ![{name}_gray]({item["gray"]}) |',
            '',
        ])

    lines.extend([
        '---',
        '',
        '## 2. Полутоновые и отфильтрованные изображения',
        '### Медианный фильтр, маска 3×3, ранг 5/9',
        '',
    ])

    for item in items:
        name = item['name']
        lines.extend([
            f'| **{name}_gray** | **{name}_median_3x3** |',
            '|:---:|:---:|',
            f'| ![{name}_gray]({item["gray"]}) | ![{name}_median_3x3]({item["filtered"]}) |',
            '',
        ])

    lines.extend([
        '---',
        '',
        '## 3. Разностные изображения и контрастированные версии',
        '',
    ])

    for item in items:
        name = item['name']
        lines.extend([
            f'| **{name}_diff** | **{name}_diff_x10** |',
            '|:---:|:---:|',
            f'| ![{name}_diff]({item["diff"]}) | ![{name}_diff_x10]({item["diff_x10"]}) |',
            '',
        ])


    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\n[OK] Report created: {REPORT_PATH}')


# ------------------------------------------------------------
# Основная программа
# ------------------------------------------------------------
def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    found_paths: list[Path] = []
    for filename in INPUT_FILES:
        path = IMG_DIR / filename
        if path.exists():
            found_paths.append(path)
        else:
            print(f'[WARN] File not found: {path}')

    if not found_paths:
        raise FileNotFoundError(
            f'No input images found in {IMG_DIR}. '
            f'Expected names: {", ".join(INPUT_FILES)}'
        )

    print('Processing images:')
    items = [process_one_image(path) for path in found_paths]
    make_report(items)
    print('\nDone.')


if __name__ == '__main__':
    main()
