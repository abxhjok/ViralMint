import { Typography } from "@mui/material"
import FastRewindOutlinedIcon from "@mui/icons-material/FastRewindOutlined"
import ToolRunner from "../../components/tools/ToolRunner"
import useDocumentTitle from "../../hooks/useDocumentTitle"

export default function ToolRemoveSilence() {
  useDocumentTitle("Silence Remover")
  return (
    <ToolRunner
      title="Silence Remover"
      description="Auto-cut pauses, fillers, and dead air"
      icon={<FastRewindOutlinedIcon fontSize="large" />}
      endpoint="/api/tools/remove-silence"
    >
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Transcribes your video with Whisper, removes silent gaps longer than
        0.4 seconds, and strips common filler words (um, uh, like, you know).
        Works best on talking-head content with clean speech.
        Videos with no detectable silence are returned unchanged.
      </Typography>
    </ToolRunner>
  )
}
