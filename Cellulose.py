# This Python file uses the following encoding: utf-8
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import os, re

def calculate_frequency_scale(Time):
    numberp = len(Time)

    dt = Time[1] - Time[0]
    f_range = 1 / dt
    f_nyquist = f_range / 2
    df = 2 * (f_nyquist / numberp)
    Freq = np.arange(-f_nyquist, f_nyquist + df, df)
    Freq = Freq[:-1]

    return Freq

def time_domain_phase(Real, Imaginary):
    delta = np.zeros(360)
    
    for phi in range(360):
        Re_phased = Real * np.cos(np.deg2rad(phi)) - Imaginary * np.sin(np.deg2rad(phi))
        Im_phased = Real * np.sin(np.deg2rad(phi)) + Imaginary * np.cos(np.deg2rad(phi))
        Magnitude_phased = calculate_amplitude(Re_phased, Im_phased)
        
        Re_cut = Re_phased[:5]
        Ma_cut = Magnitude_phased[:5]
        
        delta[phi] = np.mean(Ma_cut - Re_cut)
    
    idx = np.argmin(delta)
    #print(idx)

    Re = Real * np.cos(np.deg2rad(idx)) - Imaginary * np.sin(np.deg2rad(idx))
    Im = Real * np.sin(np.deg2rad(idx)) + Imaginary * np.cos(np.deg2rad(idx))

    return Re, Im

def adjust_frequency(Frequency, Re, Im):
    # Create complex FID
    Fid_unshifted = np.array(Re + 1j * Im)

    # FFT
    FFT = np.fft.fftshift(np.fft.fft(Fid_unshifted))

    # Check the length of FFT and Frequency (it is always the same, this is just in case)
    if len(Frequency) != len(FFT):
        Frequency = np.linspace(Frequency[0], Frequency[-1], len(FFT))

    # Find index of max spectrum (amplitude)
    index_max = np.argmax(FFT)

    # Find index of zero (frequency)
    index_zero = find_nearest(Frequency, 0)

    # Find difference
    delta_index = index_max - index_zero

    # Shift the spectra (amplitude) by the difference in indices
    FFT_shifted = np.concatenate((FFT[delta_index:], FFT[:delta_index]))

    # iFFT
    Fid_shifted = np.fft.ifft(np.fft.fftshift(FFT_shifted))

    # Define Real, Imaginary and Amplitude
    Re_shifted = np.real(Fid_shifted)
    Im_shifted = np.imag(Fid_shifted)

    return Re_shifted, Im_shifted

# Find nearest value in array
def find_nearest(array, value):
    idx = (np.abs(np.asarray(array) - value)).argmin()
    return idx

# Gaussian functions
def gauss(x, A, mu, sigma):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2))

def gauss1(x, A, sigma):
    return A * np.exp(-x**2 / (2 * sigma**2))

def gauss2(A_const):
    def gauss_const(x, sigma):
        return gauss1(x, A_const, sigma)
    return gauss_const

# Read data from file
def read_data(file_path):
    data = np.loadtxt(file_path)
    return data[:, 0], data[:, 1], data[:, 2]

# Calculate amplitude
def calculate_amplitude(real, imaginary):
    return np.sqrt(real**2 + imaginary**2)

# Directory and pattern setup
parent_directory = os.path.join(os.getcwd(), 'SE_Cycle')
pattern = re.compile(r'Cellulose.*.dat$')
pattern2 = re.compile(r'Empty.*.dat$')
pattern3 = re.compile(r'Cellulose.*_\s*(\d+)_c\.dat')
pattern_FID = re.compile(r'FID_C.*.dat$')
pattern_FID_empty = re.compile(r'FID_Empty.*.dat$')
pattern_FID_water = re.compile(r'FID_Water.*.dat$')

measurement_files = {}
baseline = {}

# FID part
for filename in os.listdir(parent_directory):
    if pattern_FID.match(filename):
        file_path_f = os.path.join(parent_directory, filename)
        Time, Re_original, Im_original = read_data(file_path_f)
        #Correct phase
        R_phased, I_phased = time_domain_phase(Re_original, Im_original)
        #Adjust frequency
        Frequency = calculate_frequency_scale(Time)
        Re_f, Im_f = adjust_frequency(Frequency, R_phased, I_phased)
        Time_f = Time
        Amp_f = calculate_amplitude(Re_f, Im_f)

    elif pattern_FID_empty.match(filename):
        file_path_fe = os.path.join(parent_directory, filename)
        Time, Re_original, Im_original = read_data(file_path_fe)
        #Correct phase
        R_phased, I_phased = time_domain_phase(Re_original, Im_original)
        #Adjust frequency
        Frequency = calculate_frequency_scale(Time)
        Re_fe, Im_fe = adjust_frequency(Frequency, R_phased, I_phased)
        Time_fe = Time
        Amp_fe = calculate_amplitude(Re_fe, Im_fe)
        
    elif pattern_FID_water.match(filename):
        file_path_w = os.path.join(parent_directory, filename)
        Time, Re_original, Im_original = read_data(file_path_w)
        #Correct phase
        R_phased, I_phased = time_domain_phase(Re_original, Im_original)
        #Adjust frequency
        Frequency = calculate_frequency_scale(Time)
        Re_w, Im_w = adjust_frequency(Frequency, R_phased, I_phased)
        Time_w = Time
        Amp_wa = calculate_amplitude(Re_w, Im_w)

Amp_w = Amp_wa -Amp_fe
Amp_FID = Amp_f - Amp_fe

# SE part
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 10))

for filename in os.listdir(parent_directory):
    if pattern.match(filename):
        file_path = os.path.join(parent_directory, filename)
        Time, Re, Im = read_data(file_path)
        Amp = calculate_amplitude(Re, Im)
        measurement_files[filename] = {'Time': Time, 'Amp': Amp}
    elif pattern2.match(filename):
        file_path = os.path.join(parent_directory, filename)
        Time, Re, Im = read_data(file_path)
        Amp = calculate_amplitude(Re, Im)
        baseline[filename] = {'Time': Time, 'Amp': Amp}

# Processing SE data
time_shift = 0
echo_time = np.arange(9, 26)
maximum = []
cmap = plt.get_cmap('winter')
num_files = len(measurement_files)

for filename1, filename2 in zip(measurement_files, baseline):
    amp_measurement_files = np.array(measurement_files[filename1]['Amp'])
    amp_baseline = np.array(baseline[filename2]['Amp'])

    if len(amp_measurement_files) != len(amp_baseline):
        amp_baseline = amp_baseline[:len(amp_measurement_files)]

    amp_difference = amp_measurement_files - amp_baseline
    measurement_files[filename1]['Amp_diff'] = amp_difference
    maximum.append(max(amp_difference))

    match = pattern3.search(filename1)
    file_key = match.group(1)

    shifted_time = np.array(measurement_files[filename1]['Time'])

    color = cmap(time_shift / num_files)
    time_shift += 1
    ax1.plot(shifted_time, amp_difference, label=file_key, color=color)

ax1.plot(Time_f, Amp_FID, 'r', label='FID')
ax1.legend(title="Echo time in μs")
ax1.set_xlabel('Time, μs')
ax1.set_ylabel('Amplitude')

# Gaussian fit for SE maximum amplitude
p1 = [10, 6] # Initial guess
popt1, _ = curve_fit(gauss1, echo_time, maximum, p0=p1)
echo_time_fit = np.arange(0, 25, 0.001)
fitting_line = gauss1(echo_time_fit, *popt1)
extrapolation = fitting_line[0]

ax2.plot(echo_time, maximum, 'o', label='Max SE Amplitude')
ax2.plot(0, extrapolation, 'ro', label='Exrapolated to time=0')
ax2.plot(echo_time_fit, fitting_line, 'r--', label='Gaussian Fit')
ax2.set_xlabel('Echo time, μs')
ax2.set_ylabel('Amplitude max')
ax2.set_title('Max Amplitudes of Solid Echo')

# plt.tight_layout()
plt.show()

# Normalize FID to the amplitude SE at t=0
time_shift = 0
for filename1 in measurement_files:
    amp_difference = np.array(measurement_files[filename1]['Amp_diff'])
    shifted_time = np.array(measurement_files[filename1]['Time'])

    match = pattern3.search(filename1)
    file_key = match.group(1)

    color = cmap(time_shift / num_files)
    cut_max_idx = np.argmax(amp_difference)

    # plt.plot(shifted_time[:-cut_max_idx] + abs(min(shifted_time)), amp_difference[cut_max_idx:], '--', label=file_key, color=color)
    # plt.legend(title="Echo time in μs")
    # plt.xlabel('Time, μs')
    # plt.ylabel('Amplitude')

    time_shift += 1

# FID fitting and building
cut_idx = find_nearest(Time_f, 10)
cut2_idx = find_nearest(Time_f, 18)
Time_cut = Time_f[cut_idx:cut2_idx]
Amp_cut = Amp_FID[cut_idx:cut2_idx]

p = [max(Amp_cut), 18]
popt, _ = curve_fit(gauss1, Time_cut, Amp_cut, p0=p)

Time_fit = np.arange(0, 100, 0.1)
AMP_fit = gauss1(Time_fit, *popt)
coeff = extrapolation / max(AMP_fit)
Amp_n = coeff * AMP_fit

A_const = extrapolation
popt2, _ = curve_fit(gauss2(A_const), Time_cut, Amp_cut, p0=[8])
A_built = gauss1(Time_f, A_const, popt2[0])

# plt.plot(Time_f, A_built, 'r', label='FID Built')
# plt.plot(Time_f, Amp_FID, 'm', label='Original')
# plt.legend(title="Echo time in μs")
# plt.show()

# Find intersections
diff = A_built - Amp_FID
sign_changes = np.where(np.diff(np.sign(diff)))[0]
intersection_times = []
intersection_amps = []
intersection_idxs = []

for idx in sign_changes:
    t1, t2 = Time_f[idx], Time_f[idx + 1]
    y1, y2 = diff[idx], diff[idx + 1]
    t_intersection = t1 - y1 * (t2 - t1) / (y2 - y1)
    intersection_times.append(t_intersection)
    amp_intersection = A_built[idx] + (A_built[idx + 1] - A_built[idx]) * (t_intersection - t1) / (t2 - t1)
    intersection_amps.append(amp_intersection)
    intersection_idxs.append(idx)

# plot the fitted and original FID
plt.plot(Time_f, A_built, 'r', label='FID Built')
plt.plot(Time_f, Amp_FID, 'm', label='Original')
plt.scatter(intersection_times, intersection_amps, color='blue', zorder=5, label='Intersections')
plt.xlabel('Time')
plt.ylabel('Amplitude')
plt.legend()
plt.show()

# Build-up the FID
Time_build_from_zero = np.arange(0, intersection_times[0], 0.1)
Amp_build_from_zero = gauss1(Time_build_from_zero, A_const, popt2[0])

Time_build_end = Time_f[intersection_idxs[0]:]
Amp_build_end = Amp_FID[intersection_idxs[0]:]

Time_build_full = np.concatenate((Time_build_from_zero, Time_build_end))
Amp_build_full = np.concatenate((Amp_build_from_zero, Amp_build_end))

plt.plot(Time_build_full, Amp_build_full, 'r', label='FID Built')
plt.plot(Time_f, Amp_FID, 'm--', label='Original')
plt.xlabel('Time')
plt.ylabel('Amplitude')
plt.legend()
plt.show()

# Water
water_cut_1 = find_nearest(Time_w, 30)
water_cut_2 = find_nearest(Time_w, 40)
Time_water_cut = Time_w[water_cut_1:water_cut_2]
Amp_water_cut = Amp_w[water_cut_1:water_cut_2]
Amp_water = np.mean(Amp_w)
Amp_cellu = popt1[0]

plt.plot(Time_build_full, Amp_build_full, 'r', label='FID Built')
plt.plot(Time_w, Amp_w, 'b', label='FID water')
plt.plot(Time_water_cut, Amp_water_cut, 'c--', label='Mean')
plt.xlabel('Time')
plt.ylabel('Amplitude')
plt.legend()
plt.show()

mass_water = 0.0925
mass_cellu = 0.1334
Avogadro_number= 6.022*(10**23)
molar_mass_water = 18.01528
molar_mass_cellu = 162.1406

protons_water = (mass_water/molar_mass_water)*Avogadro_number*2
protons_cellu = (mass_cellu/molar_mass_cellu)*Avogadro_number*10

proton_density_water = Amp_water/protons_water
proton_density_cellu = Amp_cellu/protons_cellu

print(f'Proton density from water {proton_density_water}')
print(f'Proton density from cellulose {proton_density_cellu}')
# Print results
print(f'Maximum amplitude from SE: {popt1[0]}')
print(f'Maximum amplitude from FID: {popt[0]}')
print(f'Popt from SE: {popt1}')
print(f'Popt from FID: {popt}')
print('done')
