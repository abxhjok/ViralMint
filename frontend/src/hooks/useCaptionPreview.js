import { useEffect, useState, useMemo } from "react"
import http from "../api/http"

/**
 * Lightweight, deterministic caption preview state from the backend.
 *
 * The backend Phase 2 animation engine evaluates every requested frame and
 * returns a normalized visual-state payload. The frontend only renders it;
 * no spring/bounce/glitch/typewriter/karaoke formulas are duplicated.
 */
export default function useCaptionPreview({ words, presetId, fps = 30, durationMs = 2400, frameStep = 1, enabled = true }) {
  const [frames, setFrames] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const endFrame = useMemo(() => {
    return Math.ceil((durationMs * fps) / 1000)
  }, [durationMs, fps])

  const cacheKey = useMemo(() => {
    return JSON.stringify({ words, presetId, fps, endFrame, frameStep })
  }, [words, presetId, fps, endFrame, frameStep])

  useEffect(() => {
    if (!enabled || !words?.length || !presetId) {
      setFrames(null)
      setError(null)
      return
    }

    let cancelled = false
    const fetchPreview = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await http.post("/api/captions/preview", {
          words,
          preset_id: presetId,
          fps,
          start_frame: 0,
          end_frame: endFrame,
          frame_step: frameStep,
        })
        if (!cancelled) setFrames(res.data?.frames || null)
      } catch (e) {
        if (!cancelled) setError(e.response?.data?.detail || e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchPreview()
    return () => { cancelled = true }
  }, [cacheKey, enabled])

  return { frames, loading, error, endFrame }
}
