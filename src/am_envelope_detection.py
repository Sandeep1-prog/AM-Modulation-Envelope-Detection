import os
import numpy as np
import matplotlib.pyplot as plt

def envelope_detector(signal, fs, rc):
    """
    Simulates a physical diode-RC envelope detector:
    - Diode acts as a half-wave rectifier.
    - Parallel RC network discharges exponentially when input drops below capacitor voltage.
    """
    dt = 1.0 / fs
    decay = np.exp(-dt / rc)
    
    # Half-wave rectification (ideal diode)
    rectified = np.maximum(signal, 0.0)
    
    # Capacitor charge/discharge simulation
    v_out = np.zeros(len(signal))
    v_cap = 0.0
    for i in range(len(signal)):
        if rectified[i] >= v_cap:
            v_cap = rectified[i]  # Instantaneous charge through forward-biased diode
        else:
            v_cap = v_cap * decay # Exponential discharge through load resistor R
        v_out[i] = v_cap
        
    return v_out

def run_simulation(output_dir="assets"):
    os.makedirs(output_dir, exist_ok=True)
    print("Initializing AM Modulation and Envelope Detection Simulation...")

    # ==========================================
    # 1. System Parameters
    # ==========================================
    fs = 1e6               # Sampling frequency (1 MHz)
    t_end = 0.004          # Duration = 4 ms (covers 4 cycles of 1 kHz tone)
    t = np.arange(0, t_end, 1 / fs)

    fm = 1000.0            # Modulating message frequency (1 kHz)
    fc = 25000.0           # Carrier frequency (25 kHz)
    Ac = 2.0               # Carrier amplitude (2 V)

    print(f"Sampling Frequency (fs)  : {fs / 1e3:.0f} kHz")
    print(f"Message Frequency (fm)   : {fm / 1e3:.1f} kHz")
    print(f"Carrier Frequency (fc)   : {fc / 1e3:.1f} kHz")
    print(f"Carrier Amplitude (Ac)   : {Ac} V")

    # Modulating message signal m(t) = cos(2*pi*fm*t)
    m = np.cos(2 * np.pi * fm * t)
    c = np.cos(2 * np.pi * fc * t)

    # 3 Modulation index test cases
    mu_cases = [0.5, 1.0, 1.5]
    case_labels = [
        "Under-modulation (µ = 0.5)",
        "Critical modulation (µ = 1.0)",
        "Over-modulation (µ = 1.5)"
    ]

    # Optimal RC time constant for mu = 0.5:
    # 1/fc << RC <= sqrt(1 - mu^2) / (mu * 2 * pi * fm)
    rc_optimal = 25e-6     # 25 microseconds

    # ==========================================
    # 2. Time-Domain Waveforms Comparison
    # ==========================================
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    am_signals = []

    for i, mu in enumerate(mu_cases):
        # Standard AM equation: s(t) = Ac * [1 + mu * cos(2*pi*fm*t)] * cos(2*pi*fc*t)
        s_am = Ac * (1.0 + mu * m) * c
        am_signals.append(s_am)
        upper_env = Ac * (1.0 + mu * m)
        lower_env = -upper_env

        axes[i].plot(t * 1e3, s_am, color='royalblue', lw=0.8, label="AM Waveform")
        axes[i].plot(t * 1e3, upper_env, color='crimson', linestyle='--', lw=1.5, label="Upper Envelope")
        axes[i].plot(t * 1e3, lower_env, color='crimson', linestyle=':', lw=1.2, label="Lower Envelope")
        axes[i].axhline(0, color='gray', lw=0.6, linestyle='-')
        axes[i].set_title(f"{case_labels[i]} | Peak Envelope = {Ac*(1+mu):.1f}V, Min = {Ac*(1-mu):.1f}V", fontsize=11, fontweight='bold')
        axes[i].set_ylabel("Amplitude (V)")
        axes[i].grid(True, linestyle="--", alpha=0.4)
        if i == 0:
            axes[i].legend(loc="upper right")

    axes[-1].set_xlabel("Time (ms)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "am_time_domain_cases.png"), dpi=300)
    plt.close()
    print("Saved: am_time_domain_cases.png")

    # ==========================================
    # 3. Envelope Detection & Demodulation
    # ==========================================
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)

    for i, mu in enumerate(mu_cases):
        s_am = am_signals[i]
        # Pass through physical diode-RC detector
        v_env = envelope_detector(s_am, fs, rc=rc_optimal)
        
        # Remove DC offset to recover original message waveform
        v_demod = v_env - np.mean(v_env)
        # Normalize for direct comparison with original m(t)
        v_demod_norm = v_demod / (Ac * mu)

        axes[i].plot(t * 1e3, m, color='darkgreen', lw=2.0, label="Original Message m(t)")
        axes[i].plot(t * 1e3, v_demod_norm, color='crimson', linestyle='--', lw=1.5, label="Detected Output")
        axes[i].set_title(f"Demodulation Result: {case_labels[i]}", fontsize=11, fontweight='bold')
        axes[i].set_ylabel("Normalized Amplitude")
        axes[i].grid(True, linestyle="--", alpha=0.4)
        
        # Compute Mean Squared Error (MSE) to quantify distortion
        mse = np.mean((m - v_demod_norm)**2)
        if mu <= 1.0:
            status = f"CLEAN RECOVERY (MSE = {mse:.4f})"
            color = 'green'
        else:
            status = f"SEVERE DISTORTION / PHASE INVERSION (MSE = {mse:.4f})"
            color = 'red'
        axes[i].text(0.02, 0.15, status, transform=axes[i].transAxes, fontsize=10, fontweight='bold', color=color,
                     bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=color, alpha=0.8))
        if i == 0:
            axes[i].legend(loc="upper right")

    axes[-1].set_xlabel("Time (ms)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "envelope_detection_comparison.png"), dpi=300)
    plt.close()
    print("Saved: envelope_detection_comparison.png")

    # ==========================================
    # 4. Diagonal Clipping Distortion Analysis
    # ==========================================
    # Condition to avoid diagonal clipping: RC <= sqrt(1 - mu^2) / (mu * wm)
    s_test = am_signals[0] # mu = 0.5
    rc_values = [5e-6, 25e-6, 250e-6]
    rc_labels = [
        "Too Small RC (5 µs) -> Carrier Ripple Present",
        "Optimal RC (25 µs) -> Accurate Envelope Tracking",
        "Too Large RC (250 µs) -> Severe Diagonal Peak Clipping!"
    ]
    rc_colors = ['darkorange', 'forestgreen', 'firebrick']

    plt.figure(figsize=(11, 6))
    for rc_val, label, col in zip(rc_values, rc_labels, rc_colors):
        v_det = envelope_detector(s_test, fs, rc=rc_val)
        plt.plot(t * 1e3, v_det, label=label, color=col, lw=1.5)

    plt.plot(t * 1e3, Ac * (1 + 0.5 * m), color='black', linestyle=':', lw=2, label="True Envelope")
    plt.title("Effect of RC Time Constant on Envelope Detector (Diagonal Clipping Analysis)", fontsize=12, fontweight='bold')
    plt.xlabel("Time (ms)")
    plt.ylabel("Detector Voltage (V)")
    plt.legend(loc="upper right")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "diagonal_clipping_effect.png"), dpi=300)
    plt.close()
    print("Saved: diagonal_clipping_effect.png")

    # ==========================================
    # 5. Frequency Spectrum & Power Distribution
    # ==========================================
    # FFT of mu = 1.0 signal
    s_spectrum = am_signals[1]
    N = len(s_spectrum)
    freqs = np.fft.fftfreq(N, 1 / fs)[:N // 2]
    fft_mag = 2.0 / N * np.abs(np.fft.fft(s_spectrum)[:N // 2])

    plt.figure(figsize=(10, 5))
    plt.plot(freqs / 1e3, fft_mag, color='navy', lw=1.2)
    plt.axvline((fc - fm) / 1e3, color='crimson', linestyle='--', label=f"LSB ({ (fc - fm) / 1e3:.1f} kHz)")
    plt.axvline(fc / 1e3, color='black', linestyle='-', lw=1.5, label=f"Carrier ({fc / 1e3:.1f} kHz)")
    plt.axvline((fc + fm) / 1e3, color='forestgreen', linestyle='--', label=f"USB ({ (fc + fm) / 1e3:.1f} kHz)")

    plt.title("AM Frequency Spectrum (Carrier + Upper & Lower Sidebands)", fontsize=12, fontweight='bold')
    plt.xlabel("Frequency (kHz)")
    plt.ylabel("Magnitude (V)")
    plt.xlim([(fc - 3 * fm) / 1e3, (fc + 3 * fm) / 1e3])
    plt.legend(loc="upper right")
    plt.grid(True, linestyle="--", alpha=0.5)

    # Theoretical power efficiency annotations:
    # Efficiency eta = mu^2 / (2 + mu^2)
    eta = (1.0**2) / (2 + 1.0**2) * 100
    info_text = (
        f"Bandwidth = 2 * fm = {2 * fm / 1e3:.1f} kHz\n"
        f"Carrier Power Pc = Ac^2 / 2 = 2.0 W (into 1 Ohm)\n"
        f"Sideband Power (Total) = (mu^2 / 2) * Pc = 1.0 W\n"
        f"Total Power Pt = 3.0 W\n"
        f"Modulation Efficiency eta = {eta:.1f}%"
    )
    plt.gca().text(0.03, 0.65, info_text, transform=plt.gca().transAxes, fontsize=10,
                   bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="goldenrod"))

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "am_frequency_spectrum.png"), dpi=300)
    plt.close()
    print("Saved: am_frequency_spectrum.png")

    print("\nAM Simulation finished successfully! All assets saved.")

if __name__ == "__main__":
    run_simulation()
