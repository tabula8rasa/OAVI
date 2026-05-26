from pathlib import Path
from PIL import Image
import shutil

# =========================
# Настройки лабораторной
# =========================
BASE_DIR = Path(__file__).parent

INPUT_DIR = BASE_DIR / "img"
OUTPUT_DIR = BASE_DIR / "result"
REPORT_PATH = BASE_DIR / "result.md"

M = 2  # коэффициент растяжения
N = 3  # коэффициент сжатия

SUPPORTED_EXT = {".png", ".bmp"}


# =========================
# Вспомогательные функции
# =========================
def find_input_image(input_dir: Path) -> Path:
    """Находит первое bmp/png изображение в папке img."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Папка {input_dir} не найдена")

    images = [p for p in input_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXT]
    if not images:
        raise FileNotFoundError("В папке img нет изображений формата PNG или BMP")

    return images[0]


def clamp(value: float) -> int:
    """Ограничивает значение диапазоном 0..255."""
    return max(0, min(255, int(round(value))))


# =========================
# 1. Цветовые модели
# =========================
def save_rgb_components(img: Image.Image, out_dir: Path) -> tuple[Path, Path, Path]:
    """Выделяет R, G, B компоненты и сохраняет их как отдельные изображения."""
    width, height = img.size
    src = img.load()

    r_img = Image.new("RGB", (width, height))
    g_img = Image.new("RGB", (width, height))
    b_img = Image.new("RGB", (width, height))

    r_pix = r_img.load()
    g_pix = g_img.load()
    b_pix = b_img.load()

    for y in range(height):
        for x in range(width):
            r, g, b = src[x, y]
            r_pix[x, y] = (r, 0, 0)
            g_pix[x, y] = (0, g, 0)
            b_pix[x, y] = (0, 0, b)

    r_path = out_dir / "red.png"
    g_path = out_dir / "green.png"
    b_path = out_dir / "blue.png"

    r_img.save(r_path)
    g_img.save(g_path)
    b_img.save(b_path)

    return r_path, g_path, b_path


def rgb_to_hsi_intensity(img: Image.Image, out_dir: Path) -> Path:
    """
    Переводит изображение в HSI частично: вычисляет компоненту интенсивности I.
    Для HSI: I = (R + G + B) / 3.
    """
    width, height = img.size
    src = img.load()
    intensity_img = Image.new("L", (width, height))
    dst = intensity_img.load()

    for y in range(height):
        for x in range(width):
            r, g, b = src[x, y]
            i = (r + g + b) / 3
            dst[x, y] = clamp(i)

    path = out_dir / "intensity.png"
    intensity_img.save(path)
    return path


def invert_intensity_in_rgb(img: Image.Image, out_dir: Path) -> Path:
    """
    Инвертирует яркостную компоненту I в исходном изображении.

    Используется HSI-идея:
    I = (R + G + B) / 3
    I' = 255 - I
    Каждый канал корректируется на разницу delta = I' - I.
    Так сохраняется цветовой оттенок лучше, чем при обычном RGB-инвертировании.
    """
    width, height = img.size
    src = img.load()
    out_img = Image.new("RGB", (width, height))
    dst = out_img.load()

    for y in range(height):
        for x in range(width):
            r, g, b = src[x, y]
            i = (r + g + b) / 3
            inv_i = 255 - i
            delta = inv_i - i

            r2 = clamp(r + delta)
            g2 = clamp(g + delta)
            b2 = clamp(b + delta)

            dst[x, y] = (r2, g2, b2)

    path = out_dir / "inv_intensity.png"
    out_img.save(path)
    return path


# =========================
# 2. Передискретизация
# =========================
def stretch_nearest(img: Image.Image, m: int) -> Image.Image:
    """Растяжение изображения в m раз методом ближайшего соседа."""
    width, height = img.size
    new_width = width * m
    new_height = height * m

    src = img.load()
    out_img = Image.new("RGB", (new_width, new_height))
    dst = out_img.load()

    for y in range(new_height):
        for x in range(new_width):
            old_x = x // m
            old_y = y // m
            dst[x, y] = src[old_x, old_y]

    return out_img


def compress_average(img: Image.Image, n: int) -> Image.Image:
    """Сжатие изображения в n раз усреднением по блокам n x n."""
    width, height = img.size
    new_width = width // n
    new_height = height // n

    src = img.load()
    out_img = Image.new("RGB", (new_width, new_height))
    dst = out_img.load()

    for y in range(new_height):
        for x in range(new_width):
            sum_r = sum_g = sum_b = 0
            count = 0

            for dy in range(n):
                for dx in range(n):
                    old_x = x * n + dx
                    old_y = y * n + dy
                    r, g, b = src[old_x, old_y]
                    sum_r += r
                    sum_g += g
                    sum_b += b
                    count += 1

            dst[x, y] = (
                clamp(sum_r / count),
                clamp(sum_g / count),
                clamp(sum_b / count),
            )

    return out_img


def resample_one_pass_nearest(img: Image.Image, m: int, n: int) -> Image.Image:
    """
    Передискретизация за один проход с коэффициентом K = M / N.
    Размер результата: old_size * M / N.
    Используется обратное отображение координат и ближайший сосед.
    """
    width, height = img.size
    k = m / n
    new_width = max(1, int(width * k))
    new_height = max(1, int(height * k))

    src = img.load()
    out_img = Image.new("RGB", (new_width, new_height))
    dst = out_img.load()

    for y in range(new_height):
        for x in range(new_width):
            old_x = min(width - 1, int(x / k))
            old_y = min(height - 1, int(y / k))
            dst[x, y] = src[old_x, old_y]

    return out_img


# =========================
# Markdown-отчёт
# =========================
def rel(path: Path) -> str:
    return path.relative_to(BASE_DIR).as_posix()

def create_report(original_path: Path, out_dir: Path, m: int, n: int) -> None:
    k = m / n

    text = f"""# Лабораторная работа №1
## Цветовые модели и передискретизация изображений

### 1. Цветовые модели

В качестве исходного изображения использован файл `{original_path.name}` из папки `img`.

**Исходное изображение:**

![Исходное]({rel(original_path)})

#### 1.1 Выделение компонент R, G, B

| Красный канал | Зелёный канал | Синий канал |
|---|---|---|
| ![R]({rel(out_dir / "red.png")}) | ![G]({rel(out_dir / "green.png")}) | ![B]({rel(out_dir / "blue.png")}) |

#### 1.2 Преобразование в HSI и сохранение яркостной компоненты

Яркостная компонента вычислялась по формуле:

`I = (R + G + B) / 3`

![Яркостная компонента I]({rel(out_dir / "intensity.png")})

#### 1.3 Инвертирование яркостной компоненты

Для каждого пикселя вычислялась новая яркость:

`I' = 255 - I`

После этого исходные каналы RGB корректировались на изменение яркости.

![Изображение с инвертированной яркостью]({rel(out_dir / "inv_intensity.png")})

---

### 2. Передискретизация

#### 2.1 Растяжение изображения в M = {m} раза

Метод: ближайший сосед. Библиотечные функции передискретизации не использовались.

![Растяжение]({rel(out_dir / f"stretched_{m}x.png")})

#### 2.2 Сжатие изображения в N = {n} раза

Метод: усреднение по блокам {n} × {n}.

![Сжатие]({rel(out_dir / f"compressed_{n}x.png")})

#### 2.3 Передискретизация в K = M / N за два прохода

Сначала изображение растягивалось в {m} раза, затем сжималось в {n} раза.

![Двухпроходная передискретизация]({rel(out_dir / f"twopass_{m}_{n}.png")})

#### 2.4 Передискретизация в K раз за один проход

Коэффициент передискретизации:

`K = {m} / {n} = {k:.3f}`

Метод: обратное отображение координат и ближайший сосед.

![Однопроходная передискретизация]({rel(out_dir / f"onepass_{k:.2f}.png")})
"""

    REPORT_PATH.write_text(text, encoding="utf-8")

def cleanup():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

# =========================
# Запуск программы
# =========================
def main() -> None:
    cleanup()
    OUTPUT_DIR.mkdir(exist_ok=True)

    original_path = find_input_image(INPUT_DIR)
    img = Image.open(original_path).convert("RGB")

    # 1. Цветовые модели
    save_rgb_components(img, OUTPUT_DIR)
    rgb_to_hsi_intensity(img, OUTPUT_DIR)
    invert_intensity_in_rgb(img, OUTPUT_DIR)

    # 2. Передискретизация
    stretched = stretch_nearest(img, M)
    stretched.save(OUTPUT_DIR / f"stretched_{M}x.png")

    compressed = compress_average(img, N)
    compressed.save(OUTPUT_DIR / f"compressed_{N}x.png")

    twopass = compress_average(stretched, N)
    twopass.save(OUTPUT_DIR / f"twopass_{M}_{N}.png")

    onepass = resample_one_pass_nearest(img, M, N)
    onepass.save(OUTPUT_DIR / f"onepass_{M / N:.2f}.png")

    # Отчёт
    create_report(original_path, OUTPUT_DIR, M, N)

    print("Готово")
    print(f"Исходное изображение: {original_path}")
    print(f"Результаты сохранены в папку: {OUTPUT_DIR}")
    print(f"Markdown-отчёт создан: {REPORT_PATH}")


if __name__ == "__main__":
    main()
