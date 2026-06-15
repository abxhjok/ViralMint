import { useState } from "react"
import {
  Box, Typography, ToggleButton, ToggleButtonGroup, FormControl, InputLabel,
  Select, MenuItem, Alert,
} from "@mui/material"
import SubtitlesOutlinedIcon from "@mui/icons-material/SubtitlesOutlined"
import RecordVoiceOverOutlinedIcon from "@mui/icons-material/RecordVoiceOverOutlined"
import ToolRunner from "../../components/tools/ToolRunner"
import useDocumentTitle from "../../hooks/useDocumentTitle"

const STYLES = [
  { value: "viral", label: "Viral", description: "Yellow highlight, 3 words" },
  { value: "classic", label: "Classic", description: "Full sentence, no highlight" },
  { value: "bold", label: "Bold", description: "Green highlight, 2 words" },
]

export default function ToolCaptions() {
  useDocumentTitle("Add Captions")
  const [style, setStyle] = useState("viral")
  const [emojiStyle, setEmojiStyle] = useState("moderate")

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
    </ToolRunner>
  )
}
