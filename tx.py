#!/usr/bin/env python3
# Copyright 2026 hobisatelit
# https://github.com/hobisatelit/file2afsk
# License: GPL-3.0-or-later

import socket
import sys
import time
import subprocess
import os
import hashlib
import string
import argparse

# Configuration
HOST = "localhost"
KISS_PORT = 8001
SRC_CALL = "ABC"                  # Change to your actual callsign

# Default values
DEFAULT_MAX_INFO = 128
DEFAULT_DELAY = 1

parser = argparse.ArgumentParser(
    description="Transmit a binary file over 1200 baud AFSK using Direwolf KISS.",
    epilog="Example: ./tx.py image.bin"
)
parser.add_argument("filename", help="Binary file to transmit (e.g. image.bin)")
parser.add_argument("--max", type=int, default=DEFAULT_MAX_INFO,
                    help=f"Max data bytes per frame (default: {DEFAULT_MAX_INFO}, recommended 100-150 for noisy channels, up to 1024 for strong links)")
parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                    help=f"Delay between frames in seconds (default: {DEFAULT_DELAY}, use 1-5 for noisy links, and 0.1 for strong links)")

args = parser.parse_args()

# Updated validation: allow up to 1024
if args.max < 16 or args.max > 1024:
    print("Error: --max should be between 16 and 1024")
    sys.exit(1)
if args.delay < 0:
    print("Error: --delay cannot be negative")
    sys.exit(1)

MAX_INFO = args.max
FRAME_DELAY = args.delay

ALPHANUM = string.ascii_uppercase + string.digits

def generate_file_id_from_filename(filename):
    hash_obj = hashlib.sha256(filename.encode('utf-8')).digest()
    byte1, byte2 = hash_obj[0], hash_obj[1]
    return ALPHANUM[byte1 % 36] + ALPHANUM[byte2 % 36]

def start_recording(output_filename):
    command = ["sox", "-d", "-r", "44100", "-c", "1", "-t", "wav", "-q", "-V1", output_filename]
    return subprocess.Popen(command)

def stop_recording(process):
    process.terminate()

FEND = b'\xC0'
FESC = b'\xDB'
TFEND = b'\xDC'
TFESC = b'\xDD'

def kiss_escape(data):
    data = data.replace(FESC, FESC + TFESC)
    data = data.replace(FEND, FESC + TFEND)
    return data

def ax25_address(call, last=False):
    call_padded = call.ljust(6).upper()[:6] + " "
    addr = bytes([ord(c) << 1 for c in call_padded[:6]])
    ssid = (ord(call_padded[6]) << 1) | 0x60
    if last:
        ssid |= 1
    addr += bytes([ssid])
    return addr

# === Main ===
filename = args.filename

if not os.path.exists(filename):
    print(f"Error: File '{filename}' not found!")
    sys.exit(1)

basename = os.path.basename(filename)

FILE_ID = generate_file_id_from_filename(basename)

# WAV filename includes FILE_ID
output_wav = f"audio_{FILE_ID}_{basename}.wav"

print(f"Transmitting file : {basename}")
print(f"FILE_ID           : {FILE_ID}")
print(f"MAX_INFO          : {MAX_INFO} bytes/frame")
print(f"Frame delay       : {FRAME_DELAY} seconds")
print(f"Audio output      : {output_wav}")
print(f"KISS target       : {HOST}:{KISS_PORT}\n")

# === KISS CONNECTION CHECK ===
print("Checking KISS connection to Direwolf...", end=" ")
sys.stdout.flush()

sock = None
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((HOST, KISS_PORT))
    print("SUCCESS ✓")
except socket.timeout:
    print("\nError: Connection timed out.")
    print("   → Is Direwolf running with KISSPORT 8001 enabled?")
    sys.exit(1)
except ConnectionRefusedError:
    print("\nError: Connection refused.")
    print("   → Direwolf not listening on port 8001.")
    sys.exit(1)
except Exception as e:
    print(f"\nError: Unexpected connection error: {e}")
    sys.exit(1)

# === Proceed ===
data = open(filename, 'rb').read()
src_addr = ax25_address(SRC_CALL)
dest_addr = ax25_address(FILE_ID, last=True)

print("Starting WAV recording...")
wav_process = start_recording(output_wav)
time.sleep(1)

frame_num = 0
offset = 0
total_bytes = len(data)
total_frames = (total_bytes + MAX_INFO - 1) // MAX_INFO

print(f"Sending {total_bytes} bytes in ~{total_frames} frames...\n")

while offset < total_bytes:
    chunk_size = min(MAX_INFO, total_bytes - offset)
    chunk = data[offset:offset + chunk_size]
    offset += chunk_size
    
    payload = frame_num.to_bytes(2, 'big') + chunk
    frame = dest_addr + src_addr + b'\x03\xf0' + payload
    kiss_frame = FEND + b'\x00' + kiss_escape(frame) + FEND
    
    try:
        sock.sendall(kiss_frame)
    except BrokenPipeError:
        print("\nError: Connection lost during transmission.")
        sock.close()
        stop_recording(wav_process)
        sys.exit(1)
    
    print(f"Frame {frame_num:4d}/{total_frames-1} → {chunk_size:3d} bytes")
    frame_num += 1
    
    time.sleep(FRAME_DELAY)

sock.close()
print("Press Enter to stop recording and save WAV...")
input()
stop_recording(wav_process)

time.sleep(1)
if os.path.exists(output_wav):
    size_mb = os.path.getsize(output_wav) / (1024 * 1024)
    print(f"WAV file saved: {output_wav} ({size_mb:.2f} MB)")
    print(f"Ready for playback over radio (FILE_ID: {FILE_ID})")
else:
    print("Warning: No WAV file created — check sox/audio setup.")
