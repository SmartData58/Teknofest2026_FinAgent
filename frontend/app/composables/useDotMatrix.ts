import { computed } from "vue"
import { generateGrid } from "~/utils/geometry"

export function useDotMatrix(size: number) {

  const dots = computed(() => generateGrid(size))

  return {
    dots
  }
}