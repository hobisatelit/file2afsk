#!/usr/bin/env python3
# Copyright 2026 hobisatelit
# https://github.com/hobisatelit/file2afsk
# License: GPL-3.0-or-later

import socket
import os
import sys
import argparse

# Configuration
HOST = "localhost"
KISS_PORT = 8001
DEFAULT_MAX_INFO = 128

parser = argparse.ArgumentParser(
    description="Receive multiple files over 1200 baud AFSK (multi-station, multi-file support).",
    epilog="Files are saved as: received_[FILE_ID]_from_[SRC_CALL].bin\n"
           "Robust frame validation: short chunks padded, oversized chunks truncated."
)
parser.add_argument("--max", type=int, default=DEFAULT_MAX_INFO,
                    help=f"Expected max data bytes per frame (default: {DEFAULT_MAX_INFO}, must match transmitter)")

args = parser.parse_args()

if args.max < 16 or args.max > 1024:
    print("Error: --max should be between 16 and 1024")
    sys.exit(1)

MAX_INFO = args.max

# KISS constants
FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD

def unescape_kiss(data):
    i = 0
    unescaped = bytearray()
    while i < len(data):
        if data[i] == FESC:
            i += 1
            if i >= len(data):
                break
            if data[i] == TFESC:
                unescaped.append(FESC)
            elif data[i] == TFEND:
                unescaped.append(FEND)
        else:
            unescaped.append(data[i])
        i += 1
    return bytes(unescaped)

# === KISS CONNECTION CHECK ===
print(f"Multi-file receiver starting...")
print(f"Expected MAX_INFO : {MAX_INFO} bytes/frame")
print(f"KISS target       : {HOST}:{KISS_PORT}")
print("Checking KISS connection to Direwolf...", end=" ")
sys.stdout.flush()

sock = None
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((HOST, KISS_PORT))
    print("SUCCESS ✓\n")
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

active_transfers = {}

print("Receiver ready — waiting for transmissions...")
print("Frame validation: short → zero-padded | long → truncated | corrupt → skipped\n")

try:
    in_frame = False
    command_byte = None
    frame_data = bytearray()

    while True:
        try:
            byte = sock.recv(1)
            if not byte:
                print("\nWarning: Connection closed by Direwolf.")
                break
        except socket.timeout:
            continue
        except BrokenPipeError:
            print("\nWarning: Connection lost.")
            break

        b = byte[0]

        if not in_frame:
            if b == FEND:
                in_frame = True
                frame_data.clear()
                command_byte = None
        else:
            if b == FEND:
                if len(frame_data) > 0 and command_byte is not None:
                    try:
                        raw_frame = unescape_kiss(frame_data)

                        if command_byte != 0x00:
                            in_frame = False
                            continue

                        if len(raw_frame) < 18:
                            in_frame = False
                            continue

                        dest_field = raw_frame[0:7]
                        src_field = raw_frame[7:14]
                        ctrl_pid = raw_frame[14:16]

                        if ctrl_pid != b'\x03\xf0':
                            in_frame = False
                            continue

                        file_id = ''.join(chr(c >> 1) for c in dest_field[:6]).strip()
                        src_call = ''.join(chr(c >> 1) for c in src_field[:6]).strip()

                        payload = raw_frame[16:]

                        if len(payload) < 2:
                            print(f"   ⚠ Corrupt: payload too short – skipping frame")
                            in_frame = False
                            continue

                        frame_num = int.from_bytes(payload[0:2], 'big')
                        chunk = payload[2:]

                        original_len = len(chunk)

                        if len(chunk) < MAX_INFO:
                            chunk = chunk.ljust(MAX_INFO, b'\x00')
                            print(f"   ⚠ Frame {frame_num:4d}: short ({original_len} → padded to {MAX_INFO} bytes)")
                        elif len(chunk) > MAX_INFO:
                            chunk = chunk[:MAX_INFO]
                            print(f"   ⚠ Frame {frame_num:4d}: oversized ({original_len} → truncated to {MAX_INFO} bytes)")

                        safe_src = src_call if src_call else "UNKNOWN"
                        safe_file_id = file_id if file_id else "XX"
                        filename = f"received_{safe_file_id}_from_{safe_src}.bin"

                        if file_id not in active_transfers:
                            active_transfers[file_id] = {
                                'chunks': {},
                                'highest': -1,
                                'src': src_call,
                                'filename': filename
                            }
                            print(f"\n=== New file transfer ===")
                            print(f"   FILE_ID : {file_id}")
                            print(f"   From    : {src_call}")
                            print(f"   Saving  : {filename}")

                        transfer = active_transfers[file_id]

                        if frame_num not in transfer['chunks']:
                            transfer['chunks'][frame_num] = chunk
                            transfer['highest'] = max(transfer['highest'], frame_num)
                            print(f"   ✓ Frame {frame_num:4d} stored")
                        else:
                            print(f"   Duplicate frame {frame_num} ignored")

                        with open(transfer['filename'], 'wb') as f:
                            for i in range(transfer['highest'] + 1):
                                f.write(transfer['chunks'].get(i, b'\x00' * MAX_INFO))

                        total_frames = transfer['highest'] + 1
                        received = len(transfer['chunks'])
                        size_kb = os.path.getsize(transfer['filename']) / 1024
                        print(f"   → {filename} | {received}/{total_frames} frames ({size_kb:.1f} KB)")

                    except Exception as e:
                        print(f"   ⚠ Malformed frame skipped (error: {e})")

                in_frame = False
            else:
                if command_byte is None:
                    command_byte = b
                else:
                    frame_data.append(b)

except KeyboardInterrupt:
    print("\n\nReceiver stopped by user.")

finally:
    sock.close()
    print("\n=== Final received files ===")
    for t in active_transfers.values():
        filename = t['filename']
        if os.path.exists(filename):
            size_kb = os.path.getsize(filename) / 1024
            print(f"  {filename} ({size_kb:.1f} KB)")
        else:
            print(f"  {filename} (incomplete)")
