import wave
import struct
import math
import random
import os

SAMPLE_RATE = 44100
MAX_AMP = 32767

def write_wav(filename: str, samples: list[float]):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        for s in samples:
            # clamp and convert to 16-bit integer
            val = int(max(-1.0, min(1.0, s)) * MAX_AMP)
            f.writeframesraw(struct.pack('<h', val))

def generate_fire():
    duration = 0.3
    samples = []
    num_samples = int(SAMPLE_RATE * duration)
    
    # Pitch drop from 600Hz down to 100Hz
    start_freq = 800.0
    end_freq = 150.0
    
    phase = 0.0
    for i in range(num_samples):
        t = i / num_samples
        # exponential decay for volume
        env = math.exp(-t * 8)
        
        # interpolate frequency
        freq = start_freq * (1.0 - t) + end_freq * t
        phase += (freq * 2.0 * math.pi) / SAMPLE_RATE
        
        # simple square/sine blend
        val = math.sin(phase)
        # add a little noise for crunch
        val += random.uniform(-0.1, 0.1)
        
        samples.append(val * env * 0.7)
        
    write_wav("assets/fire.wav", samples)
    print("Generated assets/fire.wav")

def generate_explosion():
    duration = 0.8
    samples = []
    num_samples = int(SAMPLE_RATE * duration)
    
    last_val = 0.0
    for i in range(num_samples):
        t = i / num_samples
        # exponential decay
        env = math.exp(-t * 5)
        
        # generate white noise
        noise = random.uniform(-1.0, 1.0)
        
        # simple lowpass filter to make it sound "boomy" instead of "hissy"
        val = last_val + 0.1 * (noise - last_val)
        last_val = val
        
        # boost bass
        samples.append(val * env * 3.0)
        
    write_wav("assets/explosion.wav", samples)
    print("Generated assets/explosion.wav")

if __name__ == "__main__":
    generate_fire()
    generate_explosion()
