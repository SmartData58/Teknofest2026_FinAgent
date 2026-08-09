export interface DotData {
  row: number
  col: number

  x: number
  y: number

  distance: number
  radius: number
  angle: number
  manhattan: number

  path: number
}

export function generateGrid(size: number): DotData[] {

  const center = (size - 1) / 2

  const dots: DotData[] = []

  for (let row = 0; row < size; row++) {

    for (let col = 0; col < size; col++) {

      const x = col - center
      const y = row - center

      const distance = Math.sqrt(x * x + y * y)

      dots.push({
        row,
        col,

        x,
        y,

        distance,

        radius: distance,

        angle: Math.atan2(y, x),

        manhattan: Math.abs(x) + Math.abs(y),

        path:
          (row + col) /
          ((size - 1) * 2)
      })
    }
  }

  return dots
}