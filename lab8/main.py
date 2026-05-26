from __future__ import annotations

import csv
import colorsys
import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


# === Настройки ===
BASE_DIR = Path('/home/ilya/OAVI/lab8')
IMGS_DIR = BASE_DIR / 'img'
if not IMGS_DIR.exists():
    IMGS_DIR = BASE_DIR / 'imgs'

OUTPUT_DIR = BASE_DIR / 'result'
REPORT_PATH = BASE_DIR / 'result.md'

# Вариант 4: NGTDM, d = 1, признаки COS, CON, BUS, линейное контрастирование
VARIANT = 4
MATRIX_NAME = 'NGTDM'
D = 1
NUM_LEVELS = 16

IMAGE_EXTENSIONS = {'.png', '.bmp', '.tif', '.tiff', '.webp'}


@dataclass
class NGTDMFeatures:
    cos: float
    con: float
    bus: float
    total_pixels: int
    active_levels: int


def cleanup_previous_results() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()


def find_images(imgs_dir: Path) -> list[Path]:
    if not imgs_dir.exists():
        raise FileNotFoundError(f'Не найдена папка с изображениями: {imgs_dir}')

    paths = sorted(p for p in imgs_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    if not paths:
        raise FileNotFoundError(f'В папке {imgs_dir} не найдено изображений PNG/BMP/TIF/WEBP.')
    return paths


def pil_to_rgb_array(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert('RGB'), dtype=np.uint8)


# colorsys использует HLS, где L = Lightness.
# Это соответствует HSL по набору компонент, просто порядок H, L, S.
def rgb_to_hls_arrays(rgb_u8: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rgb = rgb_u8.astype(np.float32) / 255.0
    flat = rgb.reshape(-1, 3)
    h, l, s = np.vectorize(colorsys.rgb_to_hls)(flat[:, 0], flat[:, 1], flat[:, 2])
    shape = rgb.shape[:2]
    return h.reshape(shape), l.reshape(shape), s.reshape(shape)


def hls_arrays_to_rgb_u8(h: np.ndarray, l: np.ndarray, s: np.ndarray) -> np.ndarray:
    flat_h = h.reshape(-1)
    flat_l = l.reshape(-1)
    flat_s = s.reshape(-1)
    r, g, b = np.vectorize(colorsys.hls_to_rgb)(flat_h, flat_l, flat_s)
    rgb = np.stack([r, g, b], axis=1).reshape(h.shape[0], h.shape[1], 3)
    return np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)


def lightness_to_u8(lightness: np.ndarray) -> np.ndarray:
    return np.clip(np.round(lightness * 255.0), 0, 255).astype(np.uint8)


def save_image(array: np.ndarray, path: Path) -> None:
    if array.ndim == 2:
        Image.fromarray(array.astype(np.uint8), mode='L').save(path)
    elif array.ndim == 3:
        Image.fromarray(array.astype(np.uint8), mode='RGB').save(path)
    else:
        raise ValueError('Ожидался массив 2D или 3D.')


def linear_contrast(gray: np.ndarray, low_percentile: float = 1.0, high_percentile: float = 99.0) -> np.ndarray:
    gray_f = gray.astype(np.float32)
    fmin = float(np.percentile(gray_f, low_percentile))
    fmax = float(np.percentile(gray_f, high_percentile))

    if np.isclose(fmin, fmax):
        return gray.copy()

    clipped = np.clip(gray_f, fmin, fmax)
    out = (clipped - fmin) * 255.0 / (fmax - fmin)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def quantize_gray(gray: np.ndarray, levels: int = NUM_LEVELS) -> np.ndarray:
    if levels < 2:
        raise ValueError('Количество уровней яркости должно быть не меньше 2.')
    q = np.floor(gray.astype(np.float32) * levels / 256.0).astype(np.int32)
    return np.clip(q, 0, levels - 1)


def build_ngtdm(image_q: np.ndarray, levels: int = NUM_LEVELS, d: int = D) -> tuple[np.ndarray, np.ndarray]:
    """
    Строит NGTDM для квантованного полутонового изображения.

    n_i — количество пикселей уровня i, для которых можно вычислить окрестность;
    s_i — сумма |i - A_i|, где A_i — средняя яркость соседей в окне (2d+1)x(2d+1), без центра.
    """
    h, w = image_q.shape
    n = np.zeros(levels, dtype=np.int64)
    s = np.zeros(levels, dtype=np.float64)

    if h <= 2 * d or w <= 2 * d:
        return n, s

    for y in range(d, h - d):
        for x in range(d, w - d):
            center = int(image_q[y, x])
            total = 0.0
            count = 0

            for yy in range(y - d, y + d + 1):
                for xx in range(x - d, x + d + 1):
                    if yy == y and xx == x:
                        continue
                    total += float(image_q[yy, xx])
                    count += 1

            avg = total / count if count else 0.0
            n[center] += 1
            s[center] += abs(float(center) - avg)

    return n, s


def compute_ngtdm_features(n: np.ndarray, s: np.ndarray) -> NGTDMFeatures:
    eps = 1e-12
    total_pixels = int(n.sum())
    if total_pixels == 0:
        return NGTDMFeatures(cos=0.0, con=0.0, bus=0.0, total_pixels=0, active_levels=0)

    p = n.astype(np.float64) / float(total_pixels)
    active = n > 0
    levels = np.arange(len(n), dtype=np.float64)
    active_levels = int(active.sum())

    # COS / Coarseness: чем больше значение, тем грубее текстура.
    cos = 1.0 / (np.sum(p[active] * s[active]) + eps)

    # CON / Contrast.
    if active_levels > 1:
        contrast_sum = 0.0
        active_indices = np.where(active)[0]
        for i in active_indices:
            for j in active_indices:
                contrast_sum += p[i] * p[j] * ((i - j) ** 2)
        con = (contrast_sum / (active_levels * (active_levels - 1))) * (np.sum(s[active]) / total_pixels)
    else:
        con = 0.0

    # BUS / Busyness.
    numerator = np.sum(p[active] * s[active])
    denominator = 0.0
    active_indices = np.where(active)[0]
    for i in active_indices:
        for j in active_indices:
            denominator += abs(levels[i] * p[i] - levels[j] * p[j])
    bus = float(numerator / (denominator + eps))

    return NGTDMFeatures(
        cos=float(cos),
        con=float(con),
        bus=float(bus),
        total_pixels=total_pixels,
        active_levels=active_levels,
    )


def save_histogram(gray: np.ndarray, out_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    hist, bins = np.histogram(gray.flatten(), bins=256, range=(0, 255))
    ax.bar(bins[:-1], hist, width=1.0)
    ax.set_title(title)
    ax.set_xlabel('Яркость')
    ax.set_ylabel('Количество пикселей')
    ax.set_xlim(0, 255)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_ngtdm_visualization(n: np.ndarray, s: np.ndarray, out_path: Path, title: str) -> None:
    levels = np.arange(len(n))

    fig, ax1 = plt.subplots(figsize=(9, 4.8))
    ax1.bar(levels - 0.2, n, width=0.4, label='n_i')
    ax1.set_xlabel('Уровень яркости i')
    ax1.set_ylabel('Количество пикселей n_i')

    ax2 = ax1.twinx()
    ax2.bar(levels + 0.2, s, width=0.4, label='s_i')
    ax2.set_ylabel('Сумма отличий s_i')

    ax1.set_title(title)
    ax1.set_xticks(levels)

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper right')

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_ngtdm_csv(n: np.ndarray, s: np.ndarray, out_path: Path) -> None:
    with out_path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['level_i', 'n_i', 's_i'])
        for i in range(len(n)):
            writer.writerow([i, int(n[i]), f'{float(s[i]):.8f}'])


def save_feature_csv(rows: list[dict[str, object]], out_path: Path) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with out_path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def save_comparison_figure(
    original_rgb: np.ndarray,
    original_gray: np.ndarray,
    contrasted_rgb: np.ndarray,
    contrasted_gray: np.ndarray,
    ngtdm_before: tuple[np.ndarray, np.ndarray],
    ngtdm_after: tuple[np.ndarray, np.ndarray],
    out_path: Path,
    title: str,
) -> None:
    n_before, s_before = ngtdm_before
    n_after, s_after = ngtdm_after
    levels = np.arange(len(n_before))

    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    ax = axes.ravel()

    ax[0].imshow(original_rgb)
    ax[0].set_title('Исходное цветное')
    ax[0].axis('off')

    ax[1].imshow(original_gray, cmap='gray', vmin=0, vmax=255)
    ax[1].set_title('Исходное полутоновое (L)')
    ax[1].axis('off')

    ax[2].bar(levels - 0.2, n_before, width=0.4, label='n_i')
    ax[2].bar(levels + 0.2, s_before, width=0.4, label='s_i')
    ax[2].set_title('NGTDM до')
    ax[2].set_xlabel('i')
    ax[2].legend(fontsize=8)

    ax[3].imshow(contrasted_rgb)
    ax[3].set_title('Контрастированное цветное')
    ax[3].axis('off')

    ax[4].imshow(contrasted_gray, cmap='gray', vmin=0, vmax=255)
    ax[4].set_title('Контрастированное полутоновое (L)')
    ax[4].axis('off')

    ax[5].bar(levels - 0.2, n_after, width=0.4, label='n_i')
    ax[5].bar(levels + 0.2, s_after, width=0.4, label='s_i')
    ax[5].set_title('NGTDM после')
    ax[5].set_xlabel('i')
    ax[5].legend(fontsize=8)

    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def md_path(path: Path) -> str:
    return './' + path.relative_to(BASE_DIR).as_posix()


def process_image(image_path: Path) -> list[dict[str, object]]:
    stem = image_path.stem
    out_dir = OUTPUT_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(image_path)
    rgb = pil_to_rgb_array(img)

    h, l, s_hls = rgb_to_hls_arrays(rgb)
    gray_before = lightness_to_u8(l)

    # Линейное контрастирование только канала L
    gray_after = linear_contrast(gray_before)
    l_after = gray_after.astype(np.float32) / 255.0
    rgb_after = hls_arrays_to_rgb_u8(h, l_after, s_hls)

    save_image(rgb, out_dir / 'original_color.png')
    save_image(gray_before, out_dir / 'original_lightness.png')
    save_image(rgb_after, out_dir / 'contrasted_color.png')
    save_image(gray_after, out_dir / 'contrasted_lightness.png')

    save_histogram(gray_before, out_dir / 'hist_before.png', f'{stem}: гистограмма яркости до')
    save_histogram(gray_after, out_dir / 'hist_after.png', f'{stem}: гистограмма яркости после')

    q_before = quantize_gray(gray_before, NUM_LEVELS)
    q_after = quantize_gray(gray_after, NUM_LEVELS)

    n_before, s_before = build_ngtdm(q_before, NUM_LEVELS, D)
    n_after, s_after = build_ngtdm(q_after, NUM_LEVELS, D)

    save_ngtdm_csv(n_before, s_before, out_dir / 'ngtdm_before.csv')
    save_ngtdm_csv(n_after, s_after, out_dir / 'ngtdm_after.csv')

    save_ngtdm_visualization(n_before, s_before, out_dir / 'ngtdm_before.png', f'{stem}: NGTDM до')
    save_ngtdm_visualization(n_after, s_after, out_dir / 'ngtdm_after.png', f'{stem}: NGTDM после')

    feats_before = compute_ngtdm_features(n_before, s_before)
    feats_after = compute_ngtdm_features(n_after, s_after)

    save_comparison_figure(
        original_rgb=rgb,
        original_gray=gray_before,
        contrasted_rgb=rgb_after,
        contrasted_gray=gray_after,
        ngtdm_before=(n_before, s_before),
        ngtdm_after=(n_after, s_after),
        out_path=out_dir / 'comparison.png',
        title=f'{stem}: сравнение до и после линейного контрастирования',
    )

    rows = [
        {
            'image': stem,
            'stage': 'before',
            'cos': f'{feats_before.cos:.8f}',
            'con': f'{feats_before.con:.8f}',
            'bus': f'{feats_before.bus:.8f}',
            'total_pixels': feats_before.total_pixels,
            'active_levels': feats_before.active_levels,
            'lightness_min': int(gray_before.min()),
            'lightness_max': int(gray_before.max()),
            'num_levels': NUM_LEVELS,
            'd': D,
        },
        {
            'image': stem,
            'stage': 'after',
            'cos': f'{feats_after.cos:.8f}',
            'con': f'{feats_after.con:.8f}',
            'bus': f'{feats_after.bus:.8f}',
            'total_pixels': feats_after.total_pixels,
            'active_levels': feats_after.active_levels,
            'lightness_min': int(gray_after.min()),
            'lightness_max': int(gray_after.max()),
            'num_levels': NUM_LEVELS,
            'd': D,
        },
    ]

    save_feature_csv(rows, out_dir / 'features.csv')
    return rows


def create_report(all_rows: list[dict[str, object]]) -> None:
    images = []
    seen = set()
    for row in all_rows:
        name = str(row['image'])
        if name not in seen:
            seen.add(name)
            images.append(name)

    by_image: dict[str, dict[str, dict[str, object]]] = {}
    for row in all_rows:
        by_image.setdefault(str(row['image']), {})[str(row['stage'])] = row

    lines: list[str] = []
    lines.extend([
        '# Лабораторная работа №8. Текстурный анализ и контрастирование',
        '',
        f'**Вариант:** {VARIANT}  ',
        f'**Матрица:** {MATRIX_NAME}, d = {D}  ',
        '**Признаки:** COS, CON, BUS  ',
        '**Метод преобразования яркости:** линейное контрастирование',
        '',
        '## Использованные методы',
        '',
        'В работе используется матрица NGTDM. Для каждого уровня яркости вычисляются два значения:',
        '',
        '- $n_i$ — количество пикселей уровня яркости $i$;',
        '- $s_i$ — сумма отличий яркости пикселя от средней яркости его соседей в окрестности с расстоянием $d = 1$.',
        '',
        'По матрице NGTDM рассчитываются признаки COS, CON и BUS. Для улучшения изображения применяется линейное контрастирование яркостного канала L в модели HSL.',
        '',
        '---',
        '',
    ])

    for idx, name in enumerate(images, start=1):
        before = by_image[name]['before']
        after = by_image[name]['after']
        out_dir = OUTPUT_DIR / name

        lines.extend([
            f'# {idx}. Изображение `{name}`',
            '',
            '## Исходное и преобразованное изображения',
            '',
            '### Исходное цветное изображение',
            f'![]({md_path(out_dir / "original_color.png")})',
            '',
            '### Исходное полутоновое изображение',
            f'![]({md_path(out_dir / "original_lightness.png")})',
            '',
            '### Контрастированное цветное изображение',
            f'![]({md_path(out_dir / "contrasted_color.png")})',
            '',
            '### Контрастированное полутоновое изображение',
            f'![]({md_path(out_dir / "contrasted_lightness.png")})',
            '',
            '## Гистограммы яркости',
            '',
            '### До контрастирования',
            f'![]({md_path(out_dir / "hist_before.png")})',
            '',
            '### После контрастирования',
            f'![]({md_path(out_dir / "hist_after.png")})',
            '',
            '## Матрицы NGTDM',
            '',
            '### До контрастирования',
            f'![]({md_path(out_dir / "ngtdm_before.png")})',
            '',
            '### После контрастирования',
            f'![]({md_path(out_dir / "ngtdm_after.png")})',
            '',
            '## Текстурные признаки',
            '',
            '| Признак | До контрастирования | После контрастирования |',
            '|---|---:|---:|',
            f'| COS | `{before["cos"]}` | `{after["cos"]}` |',
            f'| CON | `{before["con"]}` | `{after["con"]}` |',
            f'| BUS | `{before["bus"]}` | `{after["bus"]}` |',
            '',
            '---',
            '',
        ])

    lines.extend([
        '# Сравнение результатов',
        '',
        '| Изображение | COS до | COS после | CON до | CON после | BUS до | BUS после |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ])

    for name in images:
        before = by_image[name]['before']
        after = by_image[name]['after']
        lines.append(
            f'| {name} | `{before["cos"]}` | `{after["cos"]}` | '
            f'`{before["con"]}` | `{after["con"]}` | '
            f'`{before["bus"]}` | `{after["bus"]}` |'
        )

    lines.extend([
        '',
        '## Вывод',
        '',
        'После линейного контрастирования изменяется распределение яркости и, соответственно, значения NGTDM-признаков. Это показывает, что текстурные характеристики зависят не только от структуры изображения, но и от преобразования яркостного канала.',
        '',
    ])

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    cleanup_previous_results()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = find_images(IMGS_DIR)
    all_rows: list[dict[str, object]] = []

    for path in image_paths:
        print(f'Обработка: {path.name}')
        all_rows.extend(process_image(path))

    save_feature_csv(all_rows, OUTPUT_DIR / 'summary_features.csv')
    create_report(all_rows)

    print('Готово.')
    print(f'Результаты сохранены в: {OUTPUT_DIR}')
    print(f'Отчёт сохранён: {REPORT_PATH}')


if __name__ == '__main__':
    main()
