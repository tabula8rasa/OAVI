from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import stft, istft, wiener


# ============================================================
# Настройки лабораторной
# ============================================================
BASE_DIR = Path('/home/ilya/OAVI/lab9')
AUDIO_DIR = BASE_DIR / 'audio'
RESULT_DIR = BASE_DIR / 'result'
REPORT_PATH = BASE_DIR / 'result.md'

# Основной файл. Если его нет, скрипт попробует найти первый *.wav в audio/, img/ или lab9/.
INPUT_PATH = AUDIO_DIR / 'input.wav'

# STFT: окно Ханна около 50 мс, перекрытие 75%.
WINDOW_SECONDS = 0.05
OVERLAP = 0.75

# Анализ энергии по условию: dt = 0.1 c, df = 40-50 Гц.
ENERGY_DT = 0.1
ENERGY_DF = 50.0
TOP_ENERGY_POINTS = 12

# Оценка шума: берём самые тихие STFT-кадры по энергии.
NOISE_FRAME_PERCENTILE = 15
SPECTRAL_SUBTRACTION_K = 1.4
SPECTRAL_FLOOR = 0.03

SUPPORTED_EXT = {'.wav'}


@dataclass
class AudioData:
    sample_rate: int
    samples: np.ndarray
    original_channels: int
    original_dtype: str


@dataclass
class NoiseMetrics:
    signal_rms: float
    estimated_noise_rms: float
    estimated_snr_db: float
    residual_rms: float
    residual_ratio: float


def cleanup_previous_results() -> None:
    if RESULT_DIR.exists():
        shutil.rmtree(RESULT_DIR)
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()


def find_input_audio() -> Path:
    candidates = [INPUT_PATH]
    for folder_name in ['audio', 'img', '.']:
        folder = BASE_DIR / folder_name
        if folder.exists():
            candidates.extend(sorted(folder.glob('*.wav')))

    for path in candidates:
        if path.exists() and path.suffix.lower() in SUPPORTED_EXT:
            return path

    raise FileNotFoundError(
        'Не найден входной WAV-файл. Положи запись как:\n'
        f'{INPUT_PATH}\n'
        'или любой .wav в папку audio/, img/ или корень lab9/.'
    )


def read_wav_mono(path: Path) -> AudioData:
    sr, data = wavfile.read(path)
    original_dtype = str(data.dtype)

    if data.ndim == 1:
        channels = 1
        mono = data
    else:
        channels = data.shape[1]
        mono = data.astype(np.float64).mean(axis=1)

    # Нормировка в float [-1, 1].
    if np.issubdtype(data.dtype, np.integer):
        max_abs = float(np.iinfo(data.dtype).max)
        samples = mono.astype(np.float64) / max_abs
    else:
        samples = mono.astype(np.float64)
        max_val = np.max(np.abs(samples))
        if max_val > 1.0:
            samples = samples / max_val

    samples = np.asarray(samples, dtype=np.float64)
    samples = np.clip(samples, -1.0, 1.0)
    return AudioData(sr, samples, channels, original_dtype)


def save_wav_float(path: Path, sample_rate: int, samples: np.ndarray) -> None:
    samples = np.asarray(samples, dtype=np.float64)
    samples = np.clip(samples, -1.0, 1.0)
    pcm16 = np.round(samples * 32767.0).astype(np.int16)
    wavfile.write(path, sample_rate, pcm16)


def get_stft_params(sample_rate: int) -> tuple[int, int]:
    nperseg = int(round(sample_rate * WINDOW_SECONDS))
    nperseg = max(256, nperseg)
    # Лучше брать степень двойки для FFT.
    nperseg = int(2 ** np.ceil(np.log2(nperseg)))
    noverlap = int(round(nperseg * OVERLAP))
    noverlap = min(nperseg - 1, noverlap)
    return nperseg, noverlap


def compute_stft(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    nperseg, noverlap = get_stft_params(sample_rate)
    freqs, times, zxx = stft(
        samples,
        fs=sample_rate,
        window='hann',
        nperseg=nperseg,
        noverlap=noverlap,
        boundary='zeros',
        padded=True,
    )
    return freqs, times, zxx, nperseg, noverlap


def spectral_subtraction(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, dict[str, object]]:
    freqs, times, zxx, nperseg, noverlap = compute_stft(samples, sample_rate)
    magnitude = np.abs(zxx)
    phase = np.angle(zxx)

    frame_energy = np.mean(magnitude ** 2, axis=0)
    if frame_energy.size == 0:
        return samples.copy(), {}

    limit = np.percentile(frame_energy, NOISE_FRAME_PERCENTILE)
    noise_frame_mask = frame_energy <= limit
    if not np.any(noise_frame_mask):
        noise_frame_mask[0] = True

    noise_spectrum = np.mean(magnitude[:, noise_frame_mask], axis=1, keepdims=True)

    # Спектральное вычитание: Y = max(X - kW, floor*X)
    subtracted = magnitude - SPECTRAL_SUBTRACTION_K * noise_spectrum
    floor = SPECTRAL_FLOOR * magnitude
    clean_magnitude = np.maximum(subtracted, floor)
    zxx_clean = clean_magnitude * np.exp(1j * phase)

    _, clean = istft(
        zxx_clean,
        fs=sample_rate,
        window='hann',
        nperseg=nperseg,
        noverlap=noverlap,
        input_onesided=True,
        boundary=True,
    )

    clean = clean[: len(samples)]
    max_abs = np.max(np.abs(clean))
    if max_abs > 1.0:
        clean = clean / max_abs

    info = {
        'freqs': freqs,
        'times': times,
        'zxx_before': zxx,
        'zxx_after': zxx_clean,
        'noise_frame_count': int(noise_frame_mask.sum()),
        'noise_frame_percentile': NOISE_FRAME_PERCENTILE,
        'nperseg': nperseg,
        'noverlap': noverlap,
    }
    return clean.astype(np.float64), info


def apply_wiener_filter(samples: np.ndarray) -> np.ndarray:
    # Дополнительный вариант шумопонижения для сравнения.
    filtered = wiener(samples, mysize=31)
    filtered = np.asarray(filtered, dtype=np.float64)
    max_abs = np.max(np.abs(filtered))
    if max_abs > 1.0:
        filtered = filtered / max_abs
    return np.clip(filtered, -1.0, 1.0)


def estimate_noise_metrics(original: np.ndarray, denoised: np.ndarray, stft_info: dict[str, object]) -> NoiseMetrics:
    residual = original[: len(denoised)] - denoised[: len(original)]
    signal_rms = float(np.sqrt(np.mean(original ** 2)))
    residual_rms = float(np.sqrt(np.mean(residual ** 2)))

    zxx = stft_info.get('zxx_before')
    if isinstance(zxx, np.ndarray):
        magnitude = np.abs(zxx)
        frame_energy = np.mean(magnitude ** 2, axis=0)
        limit = np.percentile(frame_energy, NOISE_FRAME_PERCENTILE)
        noise_power = float(np.mean(frame_energy[frame_energy <= limit])) if np.any(frame_energy <= limit) else 0.0
        estimated_noise_rms = float(np.sqrt(noise_power))
    else:
        estimated_noise_rms = residual_rms

    eps = 1e-12
    estimated_snr_db = float(20.0 * np.log10((signal_rms + eps) / (estimated_noise_rms + eps)))
    residual_ratio = float(residual_rms / (signal_rms + eps))
    return NoiseMetrics(signal_rms, estimated_noise_rms, estimated_snr_db, residual_rms, residual_ratio)


def amplitude_to_db(mag: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(mag, 1e-10))


def save_waveform_plot(original: np.ndarray, denoised: np.ndarray, sample_rate: int, out_path: Path) -> None:
    duration = len(original) / sample_rate
    t = np.arange(len(original)) / sample_rate

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(t, original, linewidth=0.7, label='Оригинал')
    ax.plot(t[: len(denoised)], denoised, linewidth=0.7, alpha=0.8, label='После шумопонижения')
    ax.set_title('Сравнение формы сигнала до и после шумопонижения')
    ax.set_xlabel('Время, с')
    ax.set_ylabel('Амплитуда')
    ax.set_xlim(0, duration)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_residual_plot(original: np.ndarray, denoised: np.ndarray, sample_rate: int, out_path: Path) -> None:
    residual = original[: len(denoised)] - denoised[: len(original)]
    t = np.arange(len(residual)) / sample_rate

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(t, residual, linewidth=0.7)
    ax.set_title('Разность сигналов: оригинал - восстановленный')
    ax.set_xlabel('Время, с')
    ax.set_ylabel('Амплитуда')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_spectrogram(freqs: np.ndarray, times: np.ndarray, zxx: np.ndarray, out_path: Path, title: str) -> None:
    power_db = amplitude_to_db(np.abs(zxx))

    fig, ax = plt.subplots(figsize=(11, 5.5))
    mesh = ax.pcolormesh(times, freqs, power_db, shading='auto')
    ax.set_title(title)
    ax.set_xlabel('Время, с')
    ax.set_ylabel('Частота, Гц')
    ax.set_yscale('log')
    ax.set_ylim(max(20, freqs[1] if len(freqs) > 1 else 20), max(freqs.max(), 100))
    fig.colorbar(mesh, ax=ax, label='Амплитуда, дБ')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_spectrogram_linear(freqs: np.ndarray, times: np.ndarray, zxx: np.ndarray, out_path: Path, title: str) -> None:
    power_db = amplitude_to_db(np.abs(zxx))
    fig, ax = plt.subplots(figsize=(11, 5.5))
    mesh = ax.pcolormesh(times, freqs, power_db, shading='auto')
    ax.set_title(title)
    ax.set_xlabel('Время, с')
    ax.set_ylabel('Частота, Гц')
    ax.set_ylim(0, min(8000, freqs.max()))
    fig.colorbar(mesh, ax=ax, label='Амплитуда, дБ')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def find_energy_maxima(samples: np.ndarray, sample_rate: int, dt: float, df: float, top_n: int) -> list[dict[str, float]]:
    window_len = max(1, int(round(dt * sample_rate)))
    n_windows = len(samples) // window_len
    if n_windows == 0:
        return []

    rows: list[dict[str, float]] = []
    for i in range(n_windows):
        start = i * window_len
        end = start + window_len
        frame = samples[start:end]

        if frame.size == 0:
            continue

        windowed = frame * np.hanning(frame.size)
        spectrum = np.abs(np.fft.rfft(windowed)) ** 2
        freqs = np.fft.rfftfreq(frame.size, d=1.0 / sample_rate)

        max_freq = min(sample_rate / 2.0, 8000.0)
        band_edges = np.arange(0.0, max_freq + df, df)
        for f1, f2 in zip(band_edges[:-1], band_edges[1:]):
            mask = (freqs >= f1) & (freqs < f2)
            if not np.any(mask):
                continue
            energy = float(spectrum[mask].sum())
            rows.append({
                'time_start': start / sample_rate,
                'time_end': end / sample_rate,
                'freq_start': float(f1),
                'freq_end': float(f2),
                'energy': energy,
            })

    rows.sort(key=lambda x: x['energy'], reverse=True)
    return rows[:top_n]


def save_energy_table_plot(maxima: list[dict[str, float]], out_path: Path) -> None:
    if not maxima:
        return

    labels = [f"{row['time_start']:.1f}-{row['time_end']:.1f} c\n{row['freq_start']:.0f}-{row['freq_end']:.0f} Гц" for row in maxima]
    values = [row['energy'] for row in maxima]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(np.arange(len(values)), values)
    ax.set_title('Окна с наибольшей энергией')
    ax.set_xlabel('Временное и частотное окно')
    ax.set_ylabel('Энергия')
    ax.set_xticks(np.arange(len(values)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_energy_csv(maxima: list[dict[str, float]], out_path: Path) -> None:
    with out_path.open('w', encoding='utf-8') as f:
        f.write('rank;time_start;time_end;freq_start;freq_end;energy\n')
        for i, row in enumerate(maxima, start=1):
            f.write(
                f"{i};{row['time_start']:.3f};{row['time_end']:.3f};"
                f"{row['freq_start']:.1f};{row['freq_end']:.1f};{row['energy']:.8e}\n"
            )


def create_report(
    input_path: Path,
    audio: AudioData,
    metrics: NoiseMetrics,
    maxima: list[dict[str, float]],
) -> None:
    lines = [
        '# Лабораторная работа №9. Анализ шума',
        '',
        '## Исходные данные',
        '',
        f'- Входной файл: `{input_path.name}`',
        f'- Частота дискретизации: **{audio.sample_rate} Гц**',
        f'- Количество каналов в исходной дорожке: **{audio.original_channels}**',
        f'- Исходный тип данных WAV: `{audio.original_dtype}`',
        f'- Длительность: **{len(audio.samples) / audio.sample_rate:.2f} с**',
        '---',
        '',
        '## 1. Спектрограмма исходного сигнала',
        '',
        'Спектрограмма построена с помощью оконного преобразования Фурье STFT с окном Ханна. Частотная ось дополнительно визуализирована в логарифмическом масштабе.',
        '',
        '![](./result/spectrogram_before_log.png)',
        '',
        'Линейная версия спектрограммы:',
        '',
        '![](./result/spectrogram_before_linear.png)',
        '',
        '---',
        '',
        '## 2. Оценка и вычитание шума',
        '',
        f'Для оценки шума были использованы самые тихие STFT-кадры: нижние **{NOISE_FRAME_PERCENTILE}%** по энергии. Затем выполнено спектральное вычитание по формуле:',
        '',
        '$$',
        r'Y(f,t)=\max(X(f,t)-kW(f,t),\ \alpha X(f,t))',
        '$$',
        '',
        f'где `k = {SPECTRAL_SUBTRACTION_K}`, `alpha = {SPECTRAL_FLOOR}`.',
        '',
        'После вычитания шума сигнал был восстановлен обратным STFT и сохранён в файл:',
        '',
        '- [`denoised.wav`](./result/denoised.wav)',
        '',
        'Дополнительно сохранён вариант с фильтром Винера:',
        '',
        '- [`denoised_wiener.wav`](./result/denoised_wiener.wav)',
        '',
        '---',
        '',
        '## 3. Сравнение спектрограмм до и после шумопонижения',
        '',
        '### После спектрального вычитания',
        '',
        '![](./result/spectrogram_after_log.png)',
        '',
        'Линейная версия:',
        '',
        '![](./result/spectrogram_after_linear.png)',
        '',
        '---',
        '',
        '## 4. Сравнение восстановленного файла с оригиналом',
        '',
        'Ниже показаны формы сигналов до и после обработки.',
        '',
        '![](./result/waveform_comparison.png)',
        '',
        'Разностный сигнал показывает, какая часть была удалена или изменена в результате шумопонижения.',
        '',
        '![](./result/residual_signal.png)',
        '',
        '| Метрика | Значение |',
        '|---|---:|',
        f'| RMS исходного сигнала | {metrics.signal_rms:.6f} |',
        f'| Оценка RMS шума | {metrics.estimated_noise_rms:.6f} |',
        f'| Оценка SNR | {metrics.estimated_snr_db:.2f} дБ |',
        f'| RMS разности original - denoised | {metrics.residual_rms:.6f} |',
        f'| Доля разности относительно исходного RMS | {metrics.residual_ratio:.4f} |',
        '',
        '---',
        '',
        '## 5. Моменты времени с наибольшей энергией',
        '',
        f'По условию использованы окна: `Δt = {ENERGY_DT} c`, `Δf = {ENERGY_DF:.0f} Гц`.',
        '',
        '![](./result/max_energy_windows.png)',
        '',
        '| № | Время, с | Частоты, Гц | Энергия |',
        '|---:|---:|---:|---:|',
    ]

    for i, row in enumerate(maxima, start=1):
        lines.append(
            f"| {i} | {row['time_start']:.2f}–{row['time_end']:.2f} | "
            f"{row['freq_start']:.0f}–{row['freq_end']:.0f} | {row['energy']:.4e} |"
        )

    lines.extend([
        '',
        'Полная таблица сохранена в CSV:',
        '',
        '- [`energy_maxima.csv`](./result/energy_maxima.csv)',
        '',
        '---',
        '',
        '## Вывод',
        '',
        'В работе была построена спектрограмма исходного аудиосигнала, выполнена оценка шума по тихим участкам записи и применено спектральное вычитание. Восстановленный звуковой файл сохранён отдельно и сравнен с оригиналом по форме сигнала, разностному сигналу и численным метрикам. Также найдены временно-частотные окна с максимальной энергией.',
        '',
    ])

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    cleanup_previous_results()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    input_path = find_input_audio()
    audio = read_wav_mono(input_path)

    denoised, stft_info = spectral_subtraction(audio.samples, audio.sample_rate)
    denoised_wiener = apply_wiener_filter(audio.samples)

    denoised_path = RESULT_DIR / 'denoised.wav'
    denoised_wiener_path = RESULT_DIR / 'denoised_wiener.wav'
    original_mono_path = RESULT_DIR / 'original_mono.wav'

    save_wav_float(original_mono_path, audio.sample_rate, audio.samples)
    save_wav_float(denoised_path, audio.sample_rate, denoised)
    save_wav_float(denoised_wiener_path, audio.sample_rate, denoised_wiener)

    freqs_before, times_before, zxx_before, _, _ = compute_stft(audio.samples, audio.sample_rate)
    freqs_after, times_after, zxx_after, _, _ = compute_stft(denoised, audio.sample_rate)

    save_spectrogram(freqs_before, times_before, zxx_before, RESULT_DIR / 'spectrogram_before_log.png', 'Спектрограмма до шумопонижения, логарифмическая шкала частот')
    save_spectrogram_linear(freqs_before, times_before, zxx_before, RESULT_DIR / 'spectrogram_before_linear.png', 'Спектрограмма до шумопонижения')
    save_spectrogram(freqs_after, times_after, zxx_after, RESULT_DIR / 'spectrogram_after_log.png', 'Спектрограмма после шумопонижения, логарифмическая шкала частот')
    save_spectrogram_linear(freqs_after, times_after, zxx_after, RESULT_DIR / 'spectrogram_after_linear.png', 'Спектрограмма после шумопонижения')

    save_waveform_plot(audio.samples, denoised, audio.sample_rate, RESULT_DIR / 'waveform_comparison.png')
    save_residual_plot(audio.samples, denoised, audio.sample_rate, RESULT_DIR / 'residual_signal.png')

    metrics = estimate_noise_metrics(audio.samples, denoised, stft_info)

    maxima = find_energy_maxima(audio.samples, audio.sample_rate, ENERGY_DT, ENERGY_DF, TOP_ENERGY_POINTS)
    save_energy_table_plot(maxima, RESULT_DIR / 'max_energy_windows.png')
    write_energy_csv(maxima, RESULT_DIR / 'energy_maxima.csv')

    create_report(input_path, audio, metrics, maxima)

    print('Готово.')
    print(f'Исходный файл: {input_path}')
    print(f'Моно-копия оригинала: {original_mono_path}')
    print(f'Восстановленный файл после спектрального вычитания: {denoised_path}')
    print(f'Дополнительный файл после фильтра Винера: {denoised_wiener_path}')
    print(f'Отчёт: {REPORT_PATH}')


if __name__ == '__main__':
    main()

