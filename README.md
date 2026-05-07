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