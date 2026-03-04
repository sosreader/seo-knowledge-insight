/**
 * Minimal .npy file parser for float32 2D arrays.
 *
 * NumPy .npy format v1.0:
 *   - 6 bytes magic: \x93NUMPY
 *   - 1 byte major version
 *   - 1 byte minor version
 *   - 2 bytes (v1) or 4 bytes (v2) header length (little-endian)
 *   - ASCII header: Python dict literal with 'descr', 'fortran_order', 'shape'
 *   - Raw data
 */

export interface NpyArray {
  readonly shape: readonly [number, number];
  readonly data: Float32Array;
}

export function parseNpy(buffer: Buffer): NpyArray {
  const magic = buffer.subarray(0, 6).toString("latin1");
  if (magic !== "\x93NUMPY") {
    throw new Error("Not a valid .npy file (bad magic)");
  }

  const majorVersion = buffer[6]!;
  let headerLen: number;
  let headerStart: number;

  if (majorVersion === 1) {
    headerLen = buffer.readUInt16LE(8);
    headerStart = 10;
  } else if (majorVersion === 2) {
    headerLen = buffer.readUInt32LE(8);
    headerStart = 12;
  } else {
    throw new Error(`Unsupported npy version: ${majorVersion}`);
  }

  const headerStr = buffer.subarray(headerStart, headerStart + headerLen).toString("latin1");

  // Parse dtype
  const descrMatch = headerStr.match(/'descr'\s*:\s*'([^']+)'/);
  if (!descrMatch) {
    throw new Error("Cannot parse dtype from npy header");
  }
  const descr = descrMatch[1]!;
  // Support little-endian float32 and float64
  const isFloat32 = descr === "<f4" || descr === "float32";
  const isFloat64 = descr === "<f8" || descr === "float64";
  if (!isFloat32 && !isFloat64) {
    throw new Error(`Unsupported dtype: ${descr}. Only float32/float64 are supported.`);
  }

  // Parse fortran order
  const fortranMatch = headerStr.match(/'fortran_order'\s*:\s*(True|False)/);
  if (fortranMatch?.[1] === "True") {
    throw new Error("Fortran-order arrays are not supported");
  }

  // Parse shape
  const shapeMatch = headerStr.match(/'shape'\s*:\s*\((\d+),\s*(\d+)\)/);
  if (!shapeMatch) {
    throw new Error("Cannot parse 2D shape from npy header");
  }
  const rows = parseInt(shapeMatch[1]!, 10);
  const cols = parseInt(shapeMatch[2]!, 10);

  const dataStart = headerStart + headerLen;

  if (isFloat64) {
    // Convert float64 to float32
    const bytesPerElement = 8;
    const expectedBytes = rows * cols * bytesPerElement;
    if (buffer.length < dataStart + expectedBytes) {
      throw new Error(
        `File too short: expected ${dataStart + expectedBytes} bytes, got ${buffer.length}`,
      );
    }
    const float64 = new Float64Array(
      buffer.buffer,
      buffer.byteOffset + dataStart,
      rows * cols,
    );
    const data = new Float32Array(float64);
    return { shape: [rows, cols] as const, data };
  }

  // float32
  const bytesPerElement = 4;
  const expectedBytes = rows * cols * bytesPerElement;
  if (buffer.length < dataStart + expectedBytes) {
    throw new Error(
      `File too short: expected ${dataStart + expectedBytes} bytes, got ${buffer.length}`,
    );
  }

  const data = new Float32Array(buffer.buffer, buffer.byteOffset + dataStart, rows * cols);
  return { shape: [rows, cols] as const, data };
}
