# Academic Images — Built In, No Setup Required

Claw-ED automatically finds relevant academic images for your slides and handouts. **No API keys needed.** It searches these sources in order:

| Source | Best for | Cost | Key needed? |
|--------|----------|------|-------------|
| **Library of Congress** | History, Social Studies, Civics | Free | No |
| **Wikimedia Commons** | Science, Art, Music, all subjects | Free | No |
| **Web Search** (fallback) | Modern photos, generic visuals | Free | Optional (Brave key) |

## How it works

When you generate a lesson with `--format pptx` or `--format docx`, Claw-ED searches for images that match your topic and subject. A lesson on "The American Revolution" gets historical paintings and primary source documents from the Library of Congress. A lesson on "Photosynthesis" gets scientific diagrams from Wikimedia Commons.

## What you get

- **Title slide:** Full-bleed academic image with dark overlay for readability
- **Content slides:** Sidebar images (right 35%) matched to key concepts
- **Student handouts (DOCX):** Embedded images alongside relevant sections
- **No images?** Slides still look professional — subject-themed colors, clean typography, proper layouts

## Image caching

Every image is cached locally at `~/.clawed/cache/images/` so the same topic never re-downloads. Searches have a 5-second timeout — if a source is slow, it's skipped gracefully.

## Want even more images?

Add a Brave Search key for broader image results:

```bash
clawed config set-search-key YOUR_KEY   # from api.search.brave.com (free, 1000/month)
```

---

Back to the [README](../README.md).
