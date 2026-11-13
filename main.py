"""ai-happy-01 entry: write the judged image to $MAKEFUN_OUTPUT_DIR/entry.png.

The image this entry submits lives in the repository as entry.png (next to
this file). This program copies it byte for byte to the output directory
after validating that it is a whole, in-limits PNG, so the two runs the
grader performs always produce identical bytes.

Standard library only. No network, no randomness, no clock reads.
"""

import hashlib
import os
import struct
import sys
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576
MAX_DIMENSION = 1024


def _fail(message):
    print("error: " + message, file=sys.stderr)
    raise SystemExit(1)


def _read_png_chunks(data):
    """Yield (type, payload) for every chunk; verify lengths and CRCs."""
    if data[:8] != PNG_SIGNATURE:
        _fail("source is not a PNG (bad signature)")
    pos = 8
    chunks = []
    while pos < len(data):
        if pos + 8 > len(data):
            _fail("truncated PNG chunk header")
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        end = pos + 8 + length + 4
        if end > len(data):
            _fail("truncated PNG chunk: " + chunk_type.decode("latin-1"))
        payload = data[pos + 8:pos + 8 + length]
        stored_crc = struct.unpack(">I", data[pos + 8 + length:end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            _fail("PNG chunk CRC mismatch: " + chunk_type.decode("latin-1"))
        chunks.append((chunk_type, payload))
        pos = end
        if chunk_type == b"IEND":
            break
    if not chunks or chunks[-1][0] != b"IEND":
        _fail("PNG has no IEND chunk")
    if pos != len(data):
        _fail("trailing bytes after PNG IEND chunk")
    return chunks


def _validate(data):
    """Check the image against the competition limits; return (width, height)."""
    if len(data) > MAX_BYTES:
        _fail("image is %d bytes, over the 1 MiB limit" % len(data))
    chunks = _read_png_chunks(data)
    if chunks[0][0] != b"IHDR" or len(chunks[0][1]) != 13:
        _fail("PNG has no valid IHDR chunk")
    width, height = struct.unpack(">II", chunks[0][1][:8])
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        _fail("image is %dx%d, over the 1024x1024 limit" % (width, height))
    if width == 0 or height == 0:
        _fail("image has a zero dimension")
    if not any(chunk_type == b"IDAT" for chunk_type, _ in chunks):
        _fail("PNG has no IDAT chunk")
    return width, height


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    dest = os.path.join(out_dir, "entry.png")

    try:
        with open(source, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        _fail("cannot read %s: %s" % (source, exc))

    width, height = _validate(data)

    os.makedirs(out_dir, exist_ok=True)
    with open(dest, "wb") as handle:
        handle.write(data)

    # Verify the write: re-read the output and confirm it is byte-identical
    # to the validated source, so a partial or corrupted write can never
    # pass silently as a valid entry.
    with open(dest, "rb") as handle:
        written = handle.read()
    if written != data:
        _fail("output verification failed: written bytes differ from source")
    digest = hashlib.sha256(written).hexdigest()

    print("wrote %s (%dx%d, %d bytes, sha256 %s)"
          % (dest, width, height, len(data), digest))


if __name__ == "__main__":
    main()
