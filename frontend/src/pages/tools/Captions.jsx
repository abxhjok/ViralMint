import { useState } from "react"
import {
  Box, Typography, ToggleButton, ToggleButtonGroup, FormControl, InputLabel,
  Select, MenuItem, Alert, Paper, Stack, Chip, CircularProgress,
} from "@mui/material"
import SubtitlesOutlinedIcon from "@mui/icons-material/SubtitlesOutlined"
import RecordVoiceOverOutlinedIcon from "@mui/icons-material/RecordVoiceOverOutlined"
import ToolRunner from "../../components/tools/ToolRunner"
import AnimatedCaptionPreview from "../../components/captions/AnimatedCaptionPreview"
import useDocumentTitle from "../../hooks/useDocumentTitle"

const STYLES = [
  { value: "viral", label: "Viral", description: "Yellow highlight, 3 words" },
  { value: "classic", label: "Classic", description: "Full sentence, no highlight" },
  { value: "bold", label: "Bold", description: "Green highlight, 2 words" },
]

// Short sample caption used by the animated preset preview. Timing is kept
// under the backend preview duration limits so preset cards stay lightweight.
const SAMPLE_WORDS = [
  { text: "Create", start_ms: 0, end_ms: 400 },
  { text: "viral", start_ms: 400, end_ms: 900 },
  { text: "shorts", start_ms: 900, end_ms: 1400 },
  { text: "in", start_ms: 1400, end_ms: 1700 },
  { text: "seconds", start_ms: 1700, end_ms: 2300 },
]

const ANIMATED_PRESETS = [
  { id: "bounce", name: "Bounce", desc: "Spring bounce on the active word" },
  { id: "explosive", name: "Explosive", desc: "Scale + fade entry with overshoot" },
  { id: "glitch", name: "Glitch", desc: "Deterministic jitter while active" },
  { id: "typewriter", name: "Typewriter", desc: "Character-by-character reveal" },
  { id: "karaoke", name: "Karaoke", desc: "Highlight sweep across words" },
]

function PresetCard({ preset, isSelected, onClick }) {
  return (
    <Paper
      elevation={0}
      onClick={onClick}
      sx={{
        p: 1.5,
        cursor: "pointer",
        borderRadius: 2,
        border: 2,
        borderColor: isSelected ? "primary.main" : "divider",
        bgcolor: isSelected ? "action.selected" : "background.paper",
        transition: "all 0.2s",
        width: 140,
        flexShrink: 0,
        textAlign: "center",
        "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" },
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
        <AnimatedCaptionPreview
          words={SAMPLE_WORDS}
          presetId={preset.id}
          fps={24}
          durationMs={1600}
          frameStep={2}
          autoplay
          loop
          width={100}
          height={160}
          baseColor="#ffffff"
          highlightColor="#ffee33"
        />
      </Box>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>{preset.name}</Typography>
      <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 0.5, lineHeight: 1.3 }}>
        {preset.desc}
      </Typography>
    </Paper>
  )
}

export default function ToolCaptions() {
  useDocumentTitle("Add Captions")
  const [style, setStyle] = useState("viral")
  const [emojiStyle, setEmojiStyle] = useState("moderate")
  const [selectedPreset, setSelectedPreset] = useState("bounce")

  return (
    <ToolRunner
      title="Add Captions"
      description="Auto-transcribe your video's speech and burn word-by-word captions in TikTok / Reels style — no typing"
      icon={<SubtitlesOutlinedIcon fontSize="large" />}
      endpoint="/api/tools/captions"
      fieldBuilder={() => ({ style, emoji_style: emojiStyle })}
    >
      {/* Pre-upload heads-up. Whisper drives transcription from spoken
          audio, so music-only / silent clips return "No speech detected"
          from the runner. Surface that up-front instead of waiting for
          the user to upload, run, and only then see the failure toast. */}
      <Alert
        severity="info"
        icon={<RecordVoiceOverOutlinedIcon fontSize="small" />}
        sx={{ mb: 2, py: 0.5, "& .MuiAlert-message": { fontSize: "0.82rem" } }}
      >
        Works on videos with clear spoken audio (talking head, voiceover,
        interview). Music-only or silent clips return no captions.
      </Alert>

      <Typography variant="caption" sx={{ fontWeight: 600, display: "block", mb: 1 }}>
        Caption style
      </Typography>
      <ToggleButtonGroup
        value={style}
        exclusive
        onChange={(_, v) => v && setStyle(v)}
        size="small"
        sx={{ mb: 2, flexWrap: "wrap" }}
      >
        {STYLES.map((s) => (
          <ToggleButton key={s.value} value={s.value} sx={{ textTransform: "none", flexDirection: "column", py: 1, px: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>{s.label}</Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>{s.description}</Typography>
          </ToggleButton>
        ))}
      </ToggleButtonGroup>

      <Box sx={{ mt: 1 }}>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Emoji intensity</InputLabel>
          <Select value={emojiStyle} label="Emoji intensity" onChange={(e) => setEmojiStyle(e.target.value)}>
            <MenuItem value="none">None</MenuItem>
            <MenuItem value="minimal">Minimal</MenuItem>
            <MenuItem value="moderate">Moderate</MenuItem>
            <MenuItem value="heavy">Heavy</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Animated preset preview gallery (Phase 3) */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
          Animated preset preview
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 2 }}>
          All previews are computed by the backend animation engine; the frontend only renders the returned visual state.
        </Typography>

        <Stack direction="row" spacing={1.5} sx={{ overflowX: "auto", pb: 1, mb: 2 }}>
          {ANIMATED_PRESETS.map((preset) => (
            <PresetCard
              key={preset.id}
              preset={preset}
              isSelected={selectedPreset === preset.id}
              onClick={() => setSelectedPreset(preset.id)}
            />
          ))}
        </Stack>

        <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
          <AnimatedCaptionPreview
            words={SAMPLE_WORDS}
            presetId={selectedPreset}
            fps={30}
            durationMs={2400}
            frameStep={1}
            autoplay
            loop
            width={320}
            height={560}
            baseColor="#ffffff"
            highlightColor="#ffee33"
          />
        </Box>
      </Box>
    </ToolRunner>
  )
}
