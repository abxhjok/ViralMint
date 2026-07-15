import { useEffect, useMemo, useRef, useState } from "react"
import { Box, Paper, Typography, Stack, Chip, CircularProgress, Alert } from "@mui/material"
import useCaptionPreview from "../../hooks/useCaptionPreview"

/**
 * Unicode-safe grapheme cluster extraction.
 *
 * Uses Intl.Segmenter when available; falls back to code-point iteration
 * so we never slice raw UTF-8 bytes.
 */
function getGraphemeClusters(text) {
  if (typeof Intl !== "undefined" && Intl.Segmenter) {
    return Array.from(new Intl.Segmenter("en", { granularity: "grapheme" }).segment(text || "")).map(s => s.segment)
  }
  return Array.from(text || "")
}

export function visibleText(text, revealProgress) {
  const clusters = getGraphemeClusters(text)
  const count = Math.max(0, Math.min(clusters.length, Math.round(clusters.length * revealProgress)))
  return clusters.slice(0, count).join("")
}

function KaraokeWord({ text, highlightProgress, baseColor, highlightColor }) {
  const width = `${Math.max(0, Math.min(1, highlightProgress)) * 100}%`
  return (
    <Box component="span" sx={{ position: "relative", display: "inline-block" }}>
      <Box component="span" sx={{ color: baseColor, opacity: 0.85 }}>{text}</Box>
      <Box
        component="span"
        sx={{
          position: "absolute",
          left: 0,
          top: 0,
          width,
          overflow: "hidden",
          whiteSpace: "nowrap",
          color: highlightColor,
        }}
      >
        {text}
      </Box>
    </Box>
  )
}

function TypewriterWord({ text, revealProgress }) {
  return <>{visibleText(text, revealProgress)}</>
}

function CaptionWord({ word, baseColor, highlightColor }) {
  const style = useMemo(() => ({
    display: "inline-block",
    opacity: word.opacity,
    transform: `translate(${word.translate_x}px, ${word.translate_y}px) scale(${word.scale}) rotate(${word.rotation}deg)`,
    filter: `blur(${word.blur}px)`,
    textShadow: `0 0 ${word.glow}px currentColor`,
    letterSpacing: `${word.letter_spacing}px`,
    willChange: "transform, opacity",
  }), [word])

  let content
  if (word.reveal_progress > 0 && word.reveal_progress < 1) {
    content = <TypewriterWord text={word.text} revealProgress={word.reveal_progress} />
  } else if (word.highlight_progress > 0) {
    content = <KaraokeWord text={word.text} highlightProgress={word.highlight_progress} baseColor={baseColor} highlightColor={highlightColor} />
  } else {
    content = word.text
  }

  return (
    <Box component="span" sx={{ ...style, mx: 0.6 }}>
      {content}
    </Box>
  )
}

/**
 * AnimatedCaptionPreview
 *
 * Renders a caption segment using deterministic visual states produced by the
 * backend Phase 2 animation engine. It does not contain animation formulas.
 *
 * Props:
 *  - words: array of { text, start_ms, end_ms }
 *  - presetId: one of bounce, explosive, glitch, typewriter, karaoke
 *  - fps: playback frame rate
 *  - durationMs: how long to evaluate (kept short for preset cards)
 *  - frameStep: step between frames (increase to reduce backend payload)
 *  - autoplay: start playback immediately
 *  - loop: restart at end
 *  - width / height: player dimensions
 */
export default function AnimatedCaptionPreview({
  words,
  presetId,
  fps = 30,
  durationMs = 2400,
  frameStep = 1,
  autoplay = true,
  loop = true,
  width = 320,
  height = 560,
  baseColor = "#ffffff",
  highlightColor = "#ffee33",
  onError,
}) {
  const { frames, loading, error, endFrame } = useCaptionPreview({ words, presetId, fps, durationMs, frameStep })
  const [frameIndex, setFrameIndex] = useState(0)
  const [playing, setPlaying] = useState(autoplay)
  const frameCount = frames?.length || 0

  // Playback loop. We drive it from the precomputed frames so it stays in sync
  // with the deterministic backend state.
  useEffect(() => {
    if (!playing || frameCount === 0) return
    const interval = setInterval(() => {
      setFrameIndex(i => {
        const next = i + 1
        if (next >= frameCount) {
          return loop ? 0 : i
        }
        return next
      })
    }, 1000 / fps)
    return () => clearInterval(interval)
  }, [playing, frameCount, fps, loop])

  // Reset when the payload changes.
  useEffect(() => { setFrameIndex(0) }, [frames])

  // Surface errors to parent.
  useEffect(() => { if (error && onError) onError(error) }, [error, onError])

  const currentFrame = frames?.[frameIndex]
  const activeWords = currentFrame?.words || []

  return (
    <Paper
      elevation={0}
      sx={{
        width,
        height,
        bgcolor: "#000",
        borderRadius: 3,
        overflow: "hidden",
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        border: 1,
        borderColor: "divider",
      }}
      onMouseEnter={() => setPlaying(true)}
      onMouseLeave={() => setPlaying(autoplay)}
    >
      {loading && (
        <Box sx={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <CircularProgress size={28} sx={{ color: "rgba(255,255,255,0.5)" }} />
        </Box>
      )}

      {error && !loading && (
        <Alert severity="warning" sx={{ m: 2, fontSize: "0.75rem" }}>
          {error}
        </Alert>
      )}

      {!error && (
        <Box sx={{ p: 2, textAlign: "center" }}>
          <Typography
            variant="h5"
            sx={{
              color: baseColor,
              fontWeight: 800,
              lineHeight: 1.35,
              textShadow: "0 2px 8px rgba(0,0,0,0.6)",
            }}
          >
            {activeWords.length > 0 ? (
              activeWords.map((word, i) => (
                <CaptionWord key={`${word.word_index}-${i}`} word={word} baseColor={baseColor} highlightColor={highlightColor} />
              ))
            ) : (
              <Box component="span" sx={{ opacity: 0.4 }}>—</Box>
            )}
          </Typography>
        </Box>
      )}

      {/* Debug / preset badge */}
      <Chip
        label={presetId}
        size="small"
        sx={{
          position: "absolute",
          top: 8,
          right: 8,
          height: 20,
          fontSize: "0.65rem",
          fontWeight: 700,
          bgcolor: "rgba(255,255,255,0.15)",
          color: "#fff",
          border: "1px solid rgba(255,255,255,0.2)",
        }}
      />

      {/* Optional scrub / frame readout */}
      <Stack
        direction="row"
        spacing={0.5}
        sx={{
          position: "absolute",
          bottom: 8,
          left: 8,
          fontSize: "0.65rem",
          color: "rgba(255,255,255,0.5)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        <Box component="span">{frameIndex}</Box>
        <Box component="span">/</Box>
        <Box component="span">{frameCount || endFrame}</Box>
      </Stack>
    </Paper>
  )
}
