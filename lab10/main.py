from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile


# ============================================================
# Настройки лабораторной работы
# ============================================================
BASE_DIR = Path('/home/ilya/OAVI/lab10')
AUDIO_DIR = BASE_DIR / 'audio'
OUT_DIR = BASE_DIR / 'result'
REPORT_PATH = BASE_DIR / 'result.md'

# Какие файлы нужно записать и положить в audio/
AUDIO_FILES = {
    'a': 'voice_a.wav',       # протяжный звук А от низкого к высокому
    'i': 'voice_i.wav',       # протяжный звук И от низкого к высокому
    'imit': 'imit.wav',       # лай / мяуканье / крик Тарзана
}

# STFT: окно Ханна. Для шага по частоте около 10 Гц при sr=44100 нужно n_fft >= 4410.
# 8192 даёт шаг около 5.38 Гц при sr=44100.
N_FFT = 8192
HOP_SECONDS = 0.1          # шаг по времени Δt = 0.1 с
FORMANT_BAND_HZ = 50       # окрестность Δf = 40-50 Гц
MIN_VOICE_FREQ = 60        # нижняя граница поиска голоса
MAX_VOICE_FREQ = 4000      # верхняя граница поиска голоса
FORMANT_MIN_FREQ = 150
FORMANT_MAX_FREQ = 3500
TOP_FORMANTS = 3


@dataclass
class AudioAnalysis:
    key: str
    label: str
    input_path: Path
    mono_path: Path
    waveform_path: Path
    spectrogram_path: Path
    spectrum_path: Path
    sample_rate: int
    duration: float
    min_freq: float
    max_freq: float
    timbre_tone: float
    timbre_overtone_count: int
    formants: list[tuple[float, float]]  # frequency, energy


def cleanup() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_audio_path(filename: str) -> Path:
    path = AUDIO_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f'Не найден файл {path}\n'
            f'Запиши дорожку и положи её в папку {AUDIO_DIR}'
        )
    return path


def read_wav_mono(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)

    # int -> float [-1, 1]
    if data.dtype == np.int16:
        x = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        x = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        x = (data.astype(np.float32) - 128.0) / 128.0
    else:
        x = data.astype(np.float32)
        max_abs = np.max(np.abs(x)) if x.size else 1.0
        if max_abs > 1.0:
            x = x / max_abs

    # stereo -> mono
    if x.ndim == 2:
        x = x.mean(axis=1)

    # remove DC and normalize safely
    x = x - np.mean(x)
    peak = np.max(np.abs(x)) if x.size else 0.0
    if peak > 0:
        x = x / peak * 0.95

    return sr, x.astype(np.float32)


def save_wav(path: Path, sr: int, x: np.ndarray) -> None:
    y = np.clip(x, -1.0, 1.0)
    y_i16 = (y * 32767).astype(np.int16)
    wavfile.write(path, sr, y_i16)


def stft_analysis(x: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    hop = max(1, int(sr * HOP_SECONDS))
    nperseg = min(N_FFT, len(x))
    if nperseg < 256:
        nperseg = min(len(x), 256)
    noverlap = max(0, nperseg - hop)

    freqs, times, zxx = signal.stft(
        x,
        fs=sr,
        window='hann',
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=N_FFT,
        boundary=None,
        padded=False,
    )
    magnitude = np.abs(zxx)
    power = magnitude ** 2
    return freqs, times, magnitude, power


def save_waveform(x: np.ndarray, sr: int, path: Path, title: str) -> None:
    t = np.arange(len(x)) / sr
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(t, x, linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel('Время, с')
    ax.set_ylabel('Амплитуда')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_spectrogram(freqs: np.ndarray, times: np.ndarray, power: np.ndarray, path: Path, title: str) -> None:
    db = 10 * np.log10(power + 1e-12)
    mask = (freqs >= 50) & (freqs <= 8000)

    fig, ax = plt.subplots(figsize=(10, 5))
    mesh = ax.pcolormesh(times, freqs[mask], db[mask, :], shading='auto')
    ax.set_yscale('log')
    ax.set_ylim(50, min(8000, freqs[-1]))
    ax.set_title(title)
    ax.set_xlabel('Время, с')
    ax.set_ylabel('Частота, Гц, лог. шкала')
    fig.colorbar(mesh, ax=ax, label='Мощность, dB')
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_mean_spectrum(freqs: np.ndarray, power: np.ndarray, formants: list[tuple[float, float]], path: Path, title: str) -> None:
    mean_power = power.mean(axis=1)
    db = 10 * np.log10(mean_power + 1e-12)
    mask = (freqs >= 50) & (freqs <= 5000)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(freqs[mask], db[mask], linewidth=1.0)
    for idx, (f, _e) in enumerate(formants, start=1):
        ax.axvline(f, linestyle='--', linewidth=1.0)
        ax.text(f, np.max(db[mask]) - idx * 5, f'F{idx}: {f:.0f} Гц', rotation=90, va='top')
    ax.set_title(title)
    ax.set_xlabel('Частота, Гц')
    ax.set_ylabel('Средняя мощность, dB')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def estimate_voice_range(freqs: np.ndarray, power: np.ndarray) -> tuple[float, float]:
    # Берём частоты, где энергия заметно выше общего фона.
    mean_power = power.mean(axis=1)
    mask = (freqs >= MIN_VOICE_FREQ) & (freqs <= MAX_VOICE_FREQ)
    f = freqs[mask]
    p = mean_power[mask]
    if p.size == 0 or np.max(p) <= 0:
        return 0.0, 0.0

    threshold = np.max(p) * 0.08
    active = f[p >= threshold]
    if active.size == 0:
        return 0.0, 0.0
    return float(active.min()), float(active.max())


def find_prominent_formants(freqs: np.ndarray, power: np.ndarray) -> list[tuple[float, float]]:
    # Усреднение по времени, затем поиск максимумов энергии в диапазоне формант.
    mean_power = power.mean(axis=1)
    mask = (freqs >= FORMANT_MIN_FREQ) & (freqs <= FORMANT_MAX_FREQ)
    f = freqs[mask]
    p = mean_power[mask]
    if p.size == 0:
        return []

    # Сглаживание примерно в окне 40-50 Гц.
    df = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 10.0
    win = max(3, int(round(FORMANT_BAND_HZ / max(df, 1e-9))))
    if win % 2 == 0:
        win += 1
    kernel = np.ones(win) / win
    p_smooth = np.convolve(p, kernel, mode='same')

    min_distance = max(1, int(round(150 / max(df, 1e-9))))
    peaks, _ = signal.find_peaks(p_smooth, distance=min_distance)
    if peaks.size == 0:
        top = np.argsort(p_smooth)[-TOP_FORMANTS:][::-1]
    else:
        top = peaks[np.argsort(p_smooth[peaks])[-TOP_FORMANTS:]][::-1]

    formants = [(float(f[i]), float(p_smooth[i])) for i in top]
    formants.sort(key=lambda pair: pair[0])
    return formants[:TOP_FORMANTS]


def estimate_timbre_tone(freqs: np.ndarray, power: np.ndarray) -> tuple[float, int]:
    # Ищем частоту основного тона, у которой прослеживается больше всего гармоник.
    mean_power = power.mean(axis=1)
    if np.max(mean_power) <= 0:
        return 0.0, 0

    df = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 10.0
    p_norm = mean_power / np.max(mean_power)

    candidates = np.arange(80, 800, 5)
    best_f0 = 0.0
    best_count = -1
    best_score = -1.0

    for f0 in candidates:
        count = 0
        score = 0.0
        harmonic = 1
        while harmonic * f0 <= 4000:
            target = harmonic * f0
            idx = int(np.argmin(np.abs(freqs - target)))
            radius = max(1, int(round(20 / max(df, 1e-9))))
            left = max(0, idx - radius)
            right = min(len(freqs), idx + radius + 1)
            local_energy = float(np.max(p_norm[left:right]))
            if local_energy > 0.08:
                count += 1
                score += local_energy
            harmonic += 1

        if count > best_count or (count == best_count and score > best_score):
            best_count = count
            best_score = score
            best_f0 = float(f0)

    return best_f0, int(best_count)


def analyze_one(key: str, filename: str, label: str) -> AudioAnalysis:
    input_path = find_audio_path(filename)
    out_dir = OUT_DIR / key
    out_dir.mkdir(parents=True, exist_ok=True)

    sr, x = read_wav_mono(input_path)
    duration = len(x) / sr if sr else 0.0

    mono_path = out_dir / f'{key}_mono.wav'
    waveform_path = out_dir / 'waveform.png'
    spectrogram_path = out_dir / 'spectrogram.png'
    spectrum_path = out_dir / 'mean_spectrum_formants.png'

    save_wav(mono_path, sr, x)
    save_waveform(x, sr, waveform_path, f'{label}: осциллограмма')

    freqs, times, _mag, power = stft_analysis(x, sr)
    save_spectrogram(freqs, times, power, spectrogram_path, f'{label}: спектрограмма STFT, окно Ханна')

    min_freq, max_freq = estimate_voice_range(freqs, power)
    timbre_tone, overtone_count = estimate_timbre_tone(freqs, power)
    formants = find_prominent_formants(freqs, power)
    save_mean_spectrum(freqs, power, formants, spectrum_path, f'{label}: средний спектр и форманты')

    return AudioAnalysis(
        key=key,
        label=label,
        input_path=input_path,
        mono_path=mono_path,
        waveform_path=waveform_path,
        spectrogram_path=spectrogram_path,
        spectrum_path=spectrum_path,
        sample_rate=sr,
        duration=duration,
        min_freq=min_freq,
        max_freq=max_freq,
        timbre_tone=timbre_tone,
        timbre_overtone_count=overtone_count,
        formants=formants,
    )


def md_path(path: Path) -> str:
    return './' + path.relative_to(BASE_DIR).as_posix()


def create_report(results: list[AudioAnalysis]) -> None:
    lines: list[str] = []
    lines.extend([
        '# Лабораторная работа №10. Обработка голоса',
        '## Вариант 1. Голосовой диапазон, тембр, форманты',
        '',
        '---',
        '',
        '## Используемые методы',
        '',
        'Для каждого аудиофайла выполняется перевод в моно, нормализация амплитуды, построение осциллограммы и спектрограммы.',
        '',
        'Спектрограмма строится с помощью оконного преобразования Фурье STFT с окном Ханна. Частоты на спектрограмме показаны на логарифмической шкале.',
        '',
        'Минимальная и максимальная частота голоса оцениваются по диапазону частот, где средняя энергия заметно превышает уровень фона.',
        '',
        'Наиболее тембрально окрашенный основной тон определяется как частота-кандидат, для которой в среднем спектре прослеживается наибольшее количество гармоник-обертонов.',
        '',
        f'Форманты ищутся как частоты с наибольшей средней энергией в диапазоне {FORMANT_MIN_FREQ}-{FORMANT_MAX_FREQ} Гц после сглаживания в окрестности около {FORMANT_BAND_HZ} Гц.',
        '',
        '---',
        '',
        '## Исходные аудиозаписи',
        '',
        '| Образец | Файл | Частота дискретизации | Длительность |',
        '|---|---|---:|---:|',
    ])

    for r in results:
        lines.append(f'| {r.label} | `{r.input_path.name}` | {r.sample_rate} Гц | {r.duration:.2f} с |')

    lines.extend([
        '',
        '---',
        '',
        '## Сводная таблица результатов',
        '',
        '| Образец | Мин. частота | Макс. частота | Основной тон с максимумом обертонов | Кол-во обертонов | Форманта 1 | Форманта 2 | Форманта 3 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ])

    for r in results:
        formant_values = [f'{f:.1f} Гц' for f, _e in r.formants]
        while len(formant_values) < 3:
            formant_values.append('—')
        lines.append(
            f'| {r.label} | {r.min_freq:.1f} Гц | {r.max_freq:.1f} Гц | '
            f'{r.timbre_tone:.1f} Гц | {r.timbre_overtone_count} | '
            f'{formant_values[0]} | {formant_values[1]} | {formant_values[2]} |'
        )

    for r in results:
        lines.extend([
            '',
            '---',
            '',
            f'## Образец: {r.label}',
            '',
            f'**Исходный файл:** `{r.input_path.name}`  ',
            f'**Моно-копия:** `{md_path(r.mono_path)}`  ',
            f'**Длительность:** {r.duration:.2f} с  ',
            f'**Диапазон частот голоса:** {r.min_freq:.1f}-{r.max_freq:.1f} Гц  ',
            f'**Наиболее тембрально окрашенный основной тон:** {r.timbre_tone:.1f} Гц, найдено обертонов: {r.timbre_overtone_count}',
            '',
            '### Осциллограмма',
            '',
            f'![]({md_path(r.waveform_path)})',
            '',
            '### Спектрограмма',
            '',
            f'![]({md_path(r.spectrogram_path)})',
            '',
            '### Средний спектр и три сильные форманты',
            '',
            f'![]({md_path(r.spectrum_path)})',
            '',
            '| Форманта | Частота | Относительная энергия |',
            '|---:|---:|---:|',
        ])
        for idx, (freq, energy) in enumerate(r.formants, start=1):
            lines.append(f'| F{idx} | {freq:.1f} Гц | {energy:.6e} |')

    if {'a', 'i'} <= {r.key for r in results}:
        a_res = next(r for r in results if r.key == 'a')
        i_res = next(r for r in results if r.key == 'i')
        a_formants = ', '.join(f'{f:.0f} Гц' for f, _ in a_res.formants)
        i_formants = ', '.join(f'{f:.0f} Гц' for f, _ in i_res.formants)
        lines.extend([
            '',
            '---',
            '',
            '## Сравнение формант звуков «А» и «И»',
            '',
            f'Для звука «А» найдены форманты: {a_formants}.',
            '',
            f'Для звука «И» найдены форманты: {i_formants}.',
            '',
            'Форманты различаются, поскольку при произнесении разных гласных изменяется положение языка, губ и резонансные частоты речевого тракта.',
        ])

    lines.extend([
        '',
        '---',
        '',
        '## Вывод',
        '',
        'В ходе работы были построены спектрограммы голосовых записей, оценён частотный диапазон голоса, найден основной тон с наибольшим количеством обертонов и определены три наиболее сильные форманты для каждого звукового образца.',
        '',
    ])

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    cleanup()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    labels = {
        'a': 'Звук «А»',
        'i': 'Звук «И»',
        'imit': 'Имитация лая / мяуканья / крика Тарзана',
    }

    results: list[AudioAnalysis] = []
    for key, filename in AUDIO_FILES.items():
        print(f'Обработка {filename}...')
        results.append(analyze_one(key, filename, labels[key]))

    create_report(results)

    print('Готово.')
    print(f'Результаты сохранены в: {OUT_DIR}')
    print(f'Отчёт: {REPORT_PATH}')


if __name__ == '__main__':
    main()
