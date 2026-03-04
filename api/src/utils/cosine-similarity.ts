/**
 * Float32Array-based vector operations for cosine similarity.
 *
 * All vectors are expected to be L2-normalized before use,
 * so dot product === cosine similarity.
 */

export function dotProduct(a: Float32Array, b: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) {
    sum += a[i]! * b[i]!;
  }
  return sum;
}

export function normalizeL2(vec: Float32Array): Float32Array {
  let norm = 0;
  for (let i = 0; i < vec.length; i++) {
    norm += vec[i]! * vec[i]!;
  }
  norm = Math.sqrt(norm);

  if (norm === 0) return vec;

  const result = new Float32Array(vec.length);
  for (let i = 0; i < vec.length; i++) {
    result[i] = vec[i]! / norm;
  }
  return result;
}

/**
 * Normalize each row of a 2D matrix in-place-style (returns new array).
 * @param data  Flat Float32Array of shape [rows, cols]
 * @param rows  Number of rows
 * @param cols  Number of columns
 */
export function normalizeRows(
  data: Float32Array,
  rows: number,
  cols: number,
): Float32Array {
  const result = new Float32Array(data.length);
  for (let r = 0; r < rows; r++) {
    const offset = r * cols;
    let norm = 0;
    for (let c = 0; c < cols; c++) {
      const v = data[offset + c]!;
      norm += v * v;
    }
    norm = Math.sqrt(norm);
    if (norm === 0) norm = 1;
    for (let c = 0; c < cols; c++) {
      result[offset + c] = data[offset + c]! / norm;
    }
  }
  return result;
}

/**
 * Compute dot product of each row in a matrix with a query vector.
 * @param matrix  Flat Float32Array [rows x cols]
 * @param query   Float32Array [cols]
 * @param rows    Number of rows
 * @param cols    Number of columns
 * @returns Float32Array of shape [rows] with dot product scores
 */
export function matrixDotVector(
  matrix: Float32Array,
  query: Float32Array,
  rows: number,
  cols: number,
): Float32Array {
  const scores = new Float32Array(rows);
  for (let r = 0; r < rows; r++) {
    let sum = 0;
    const offset = r * cols;
    for (let c = 0; c < cols; c++) {
      sum += matrix[offset + c]! * query[c]!;
    }
    scores[r] = sum;
  }
  return scores;
}
