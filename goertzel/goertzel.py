import matplotlib.pyplot as plt
from math import sin, cos, pi


class Goertzel():
    def __init__(self, f, N, Fs):
        self.k = int(0.5 + N * f/Fs)
        self.w = 2 * pi * self.k / N
        self.c = 2 * cos(self.w)
        self.q1 = 0
        self.q2 = 0
        self.n = 0
        self.N = N
        self.f = f

    # Update with a sample. Returns true when enough samples.
    def update(self, s):
        self.n += 1
        q = s + self.c * self.q1 - self.q2
        self.q2 = self.q1
        self.q1 = q
        return self.ready()

    # Enough samples updated
    def ready(self):
        return self.n >= self.N

    # Returns normalized power at the target frequency
    def power(self):
        P = self.q1**2 + self.q2**2 - (self.c * self.q1 * self.q2)
        return P / self.N

    def reset(self):
        self.q1 = 0
        self.q2 = 0
        self.n = 0


def goertzel(f, x, N, Fs):
    """Compute Goertzel algorithm on time series.
    Works best when frequency is integer multiple of Fs/N.

    f -- Target frequency
    x -- Time series
    N -- Time series length
    Fs -- Sampling rate of the time series

    Returns normalized power spectrum DFT term for the target frequency in the signal.
    """
    k = int(0.5 + N * f / Fs)  # select k based on target frequency
    w = 2 * pi * k / N
    c = 2 * cos(w)

    q1 = 0
    q2 = 0
    for n in range(0, N):
        q = x[n] + c * q1 - q2
        q2 = q1
        q1 = q

    P = q1**2 + q2**2 - (c * q1 * q2)
    return P / N


def main():
    def generate(T, Fs, f1, f2):
        N = int(T * Fs)
        x = [0.5*sin(2*pi*f1*n/Fs) + 0.5*sin(2*pi*f2*n/Fs)
             for n in range(0, N)]
        # x = [0.5*sin(2*pi*1000*n/Fs) for n in range(0, N)]  # 1kHz test
        t = [n/Fs for n in range(0, N)]
        return (t, x, N)

    FREQ_LOW1 = 697
    FREQ_LOW2 = 770
    FREQ_LOW3 = 852
    FREQ_LOW4 = 941
    FREQ_HIGH1 = 1209
    FREQ_HIGH2 = 1336
    FREQ_HIGH3 = 1477
    FREQ_HIGH4 = 1633

    Fs = 8000  # sample rate (Hz).
    # Sample rate must be at least 2 times the target frequency (Fs > 2 * f)
    T = 50e-3  # sample duration (s)
    # Optimal sample duration/sample size for a given target frequency and sample rate is
    # integer multiples of frequency divided by the sample rate
    T = FREQ_LOW2 / Fs * 2
    # N = T * Fs
    # Higher frequencies require longer sample time.

    # N = int(T * Fs)
    # x = [0.5*sin(2*pi*fl1*n/Fs) + 0.5*sin(2*pi*fh1*n/Fs) for n in range(0, N)]
    # x = [0.5*sin(2*pi*1000*n/Fs) for n in range(0, N)]  # 1kHz test
    # t = [n/Fs for n in range(0, N)]
    f1 = FREQ_LOW2
    f2 = FREQ_HIGH2
    (t, x, N) = generate(T, Fs, f1, f2)
    plt.figure(1)
    # plt.plot(t[:int(0.01*Fs)+1], x[:int(0.01*Fs)+1])
    plt.plot(t, x)
    plt.title(f'{f1}Hz + {f2}Hz')
    # plt.plot(t, x)
    # plt.show()
    # print(x[:int(0.001*Fs)+1])
    f = [f for f in range(f1 - 200, f2 + 200)]
    P = [goertzel(f, x, N, Fs) for f in f]
    plt.figure(2)
    plt.plot(f, P)
    plt.ylabel('Power')
    plt.xlabel('Frequency')
    plt.show()
    # print(f'{f} {goertzel(f, x, N, Fs)}')


if __name__ == "__main__":
    main()
