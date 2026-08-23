import {
  useAnimationFrame,
  useMotionValue,
  useScroll,
  useTransform,
  type MotionValue,
} from "motion/react"
import type { RefObject } from "react"

interface FlightMotionOptions {
  isMotionPaused: boolean
  prefersReducedMotion: boolean
}

interface FlightMotionResult {
  craftTransform: MotionValue<string>
  craftOpacity: MotionValue<number>
}

export function useFlightMotion(
  heroRef: RefObject<HTMLElement | null>,
  { isMotionPaused, prefersReducedMotion }: FlightMotionOptions,
): FlightMotionResult {
  const flightProgress = useMotionValue(0)
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  })

  useAnimationFrame((_time, delta) => {
    if (isMotionPaused || prefersReducedMotion) return
    const normalizedDelta = Math.min(delta, 80) / 11000
    flightProgress.set((flightProgress.get() + normalizedDelta) % 1)
  })

  const progress = useTransform(() => {
    const timeValue = prefersReducedMotion ? 0 : flightProgress.get()
    return (timeValue + scrollYProgress.get() * 0.18) % 1
  })

  const craftTransform = useTransform(() => {
    const value = progress.get()
    const x = -22 + value * 184 + Math.sin(value * Math.PI * 2) * 8
    const y = 6 - value * 42 + Math.sin(value * Math.PI * 4) * 4
    const rotation = -12 + value * 72 + Math.cos(value * Math.PI * 2) * 4
    const scale = 0.76 + value * 0.48
    return `translate3d(${x}%, ${y}%, 0) rotateZ(${rotation}deg) scale(${scale})`
  })

  const craftOpacity = useTransform(() => 0.82 + progress.get() * 0.18)

  return { craftTransform, craftOpacity }
}
