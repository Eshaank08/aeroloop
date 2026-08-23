import { useReducedMotion } from "motion/react"
import { useCallback, useState } from "react"

export function useMotionPreferences() {
  const prefersReducedMotion = Boolean(useReducedMotion())
  const [isMotionPaused, setIsMotionPaused] = useState(false)
  const toggleMotion = useCallback(() => setIsMotionPaused((paused) => !paused), [])

  return { prefersReducedMotion, isMotionPaused, toggleMotion }
}
