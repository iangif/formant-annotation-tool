uv run fastapi dev main.py
uv run fastapi run main.py

technologies:
uv
FastAPI
Pydantic
jinja 2 templates
vanilla JS
bootstrap for CSS
SQL alchemy / SQLite

async: aiosqlite
routers

GET / (renders annotation page)
GET /api/tokens/next?annotator_id=name
- returns next unannotated token for this annotator (TokenRead)
GET /api/tokens/{token_id}
POST /api/annotations
- sends annotation to backend (AnnotationCreate)
GET /api/progress?annotator_id=name

---

Space
  Save immediately as auto_accept.
  Ignore whatever is currently written in F1–F4.
  Backend/frontend should use auto_winner_panel for all four fields.

B
  Save immediately as bad_token.

X
  Save immediately as needs_correction.

Hover over spectrogram image
  Treat the image as a 20-panel grid.
  Panels are numbered 0–19, left-to-right, top-to-bottom.
  The hovered panel gets a subtle visual overlay/highlight.

Click hovered panel
  Copy that panel number into F1, F2, F3, and F4.
  Do not save yet.
  User can then manually edit individual F1–F4 fields.

Enter
  Save using the current written F1–F4 values.
  If all four fields equal auto_winner_panel:
    decision = auto_accept
  Else if all four fields are the same non-winner panel:
    decision = select_panel
  Else:
    decision = complex

Shift + click hovered panel
  Copy that panel number into all four fields and save immediately.
  If selected panel equals auto_winner_panel:
    decision = auto_accept
  Else:
    decision = select_panel