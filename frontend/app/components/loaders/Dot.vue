<script setup lang="ts">
import type { DotData } from "~/utils/geometry"

const props = defineProps<{
  dot: DotData
  dotSize: number
}>()

const style = computed(() => ({
  width: `${props.dotSize}px`,
  height: `${props.dotSize}px`,

  "--path": props.dot.path,

  "--distance": props.dot.distance,

  "--row": props.dot.row,

  "--col": props.dot.col,

  "--angle": props.dot.angle
}))
</script>

<template>

<span
  class="dm-dot"
  :style="style"
/>

</template>