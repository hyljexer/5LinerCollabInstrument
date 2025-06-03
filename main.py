import serial
import threading
import sounddevice as sd
import numpy as np
from pydub import AudioSegment
from time import sleep
from math import pow
import json

# --- CONFIGURATION ---
SERIAL_PORT = 'COM3'
BAUDRATE = 115200
THRESHOLD = 150
SAMPLE_FILE = 'C4.wav'
SAMPLE_RATE = 44100

# --- NOTE MAPPING ---
# Assume analog pins A0–A5 → Notes C4, D4, E4, F4, G4, A4 (semitone offsets from C4)
NOTE_SEMITONES = [0, 4, 7, 9 ]

# --- PITCH SHIFT FUNCTION ---
def pitch_shift(samples, semitones):
    factor = pow(2.0, semitones / 12.0)
    indices = np.round(np.arange(0, len(samples), 1 / factor)).astype(int)
    indices = indices[indices < len(samples)]
    return samples[indices]

# --- AUDIO PLAYER THREAD ---
class NotePlayer(threading.Thread):
    def __init__(self, samples):
        super().__init__()
        self.samples = samples
        self.ptr = 0
        self.playing = True
        
    def run(self):
        def callback(outdata, frames, time, status):
            if not self.playing:
                raise sd.CallbackStop()
            out_len = min(frames, len(self.samples) - self.ptr)
            outdata[:out_len, 0] = self.samples[self.ptr:self.ptr + out_len]
            if out_len < frames:
                outdata[out_len:] = 0
                raise sd.CallbackStop()
            self.ptr += out_len

        with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=callback):
            while self.playing and self.ptr < len(self.samples):
                sleep(0.01)

    def stop(self):
        self.playing = False

# --- LOAD BASE SAMPLE (C4) ---
base = AudioSegment.from_wav(SAMPLE_FILE).set_channels(1).set_frame_rate(SAMPLE_RATE)
base_samples = np.array(base.get_array_of_samples()).astype(np.float32) / 32768.0

shifted_samples = []
for i in range(6):
    if i < 4:
        shifted_samples.append(pitch_shift(base_samples, NOTE_SEMITONES[i]))
    elif i == 4:
        kick = AudioSegment.from_wav('kick.wav').set_channels(1).set_frame_rate(SAMPLE_RATE)
        kick_samples = np.array(kick.get_array_of_samples()).astype(np.float32) / 32768.0
        shifted_samples.append(kick_samples)
    elif i == 5:
        snare = AudioSegment.from_wav('snare.wav').set_channels(1).set_frame_rate(SAMPLE_RATE)
        snare_samples = np.array(snare.get_array_of_samples()).astype(np.float32) / 32768.0
        snare_samples = snare_samples * 0.00001 
        shifted_samples.append(snare_samples)



    def run(self):
        def callback(outdata, frames, time, status):
            if not self.playing:
                raise sd.CallbackStop()
            out_len = min(frames, len(self.samples) - self.ptr)
            outdata[:out_len, 0] = self.samples[self.ptr:self.ptr + out_len]
            if out_len < frames:
                outdata[out_len:] = 0
                raise sd.CallbackStop()
            self.ptr += out_len

        with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=callback):
            while self.playing and self.ptr < len(self.samples):
                sleep(0.01)

    def stop(self):
        self.playing = False

# --- MAIN LOOP ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    print(f"Listening on {SERIAL_PORT}...")

    players = [None] * 6

    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue

        try:
            data = json.loads(line)
            # Expecting: {"A0":val, "A1":val, ..., "A5":val}
            analog_values = [data.get(f"A{i}", 1023) for i in range(6)]
            print(analog_values)
            if len(analog_values) != 6:
                print(f"Ignoring invalid input: {line}")
                continue

            for i, val in enumerate(analog_values):
                if val < THRESHOLD:
                    if not players[i] or not players[i].is_alive():
                        players[i] = NotePlayer(shifted_samples[i])
                        players[i].start()
                else:
                    if players[i]:
                        players[i].stop()
                        players[i] = None

        except (ValueError, json.JSONDecodeError):
            print(f"Ignoring invalid input: {line}")

except KeyboardInterrupt:
    print("Exiting...")
    for player in players:
        if player:
            player.stop()

except serial.SerialException as e:
    print(f"Serial error: {e}")