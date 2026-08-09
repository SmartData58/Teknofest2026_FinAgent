<script setup lang="ts">

import Dot from "./Dot.vue"
import { useDotMatrix } from "~/composables/useDotMatrix"

const props = withDefaults(

defineProps<{

size?:number

dotSize?:number

gap?:number

speed?:number

color?:string

}>(),

{

size:3,

dotSize:16,

gap:2,

speed:1,

color:"#ffffff"

})

const { dots } = useDotMatrix(props.size)

</script>

<template>

<div

class="dm-root"

:style="{

'--gap':`${gap}px`,

'--dot-size':`${dotSize}px`,

'--speed':speed,

'--dot-color':color

}"

>

<div

class="dm-grid"

:style="{

gridTemplateColumns:`repeat(${size},${dotSize}px)`

}"

>

<Dot

v-for="dot in dots"

:key="`${dot.row}-${dot.col}`"

:dot="dot"

:dot-size="dotSize"

/>

</div>

</div>

</template>

<style scoped>
.dm-root{
  display:inline-flex;
}

.dm-grid{
  display:grid;
  gap:var(--gap);
}

.dm-dot{
  background:var(--dot-color);
  border-radius:50%;
  opacity:.08;
  transform:scale(.75);

  animation:
    pulse calc(1s / var(--speed))
    ease-in-out
    infinite;

  animation-delay:
    calc(var(--path) * 120ms);

  will-change:
    transform,
    opacity;
}

@keyframes pulse{
  0%,100%{
    opacity:.08;
    transform:scale(.65);
  }

  50%{
    opacity:1;
    transform:scale(1);
  }
}
</style>