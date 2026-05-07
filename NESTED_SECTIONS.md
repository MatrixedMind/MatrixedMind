# Nested Subsections Feature

This document describes the nested subsections feature in MatrixedMind.

## Overview

MatrixedMind now supports arbitrary nesting of subsections within the note storage hierarchy. This allows for better organization of notes in complex projects.

### Before (Simple Sections)
```
notes/<project>/<section>/<title>.md
```

### After (Nested Sections)
```
notes/<project>/<section>/<subsection1>/<subsection2>/.../<title>.md
```

## Usage

### API Format

When creating or retrieving notes, use forward slashes (`/`) in the `section` parameter to indicate nesting:

```json
{
  "project": "MyProject",
  "section": "Ideas/Subidea/DeepIdea",
  "title": "My Note",
  "body": "Note content here",
  "mode": "append"
}
```

### Examples

#### Simple Section (Backwards Compatible)
```json
{
  "project": "Personal Wiki",
  "section": "Ideas",
  "title": "Simple Note",
  "body": "Content"
}
```
**Result**: `notes/Personal_Wiki/Ideas/Simple_Note.md`

#### Two-Level Nesting
```json
{
  "project": "Personal Wiki",
  "section": "Work/Q1 Planning",
  "title": "Budget",
  "body": "Q1 budget details"
}
```
**Result**: `notes/Personal_Wiki/Work/Q1_Planning/Budget.md`

#### Deep Nesting
```json
{
  "project": "Research",
  "section": "Projects/2025/AI/Machine Learning/Papers",
  "title": "Transformers",
  "body": "Attention is all you need"
}
```
**Result**: `notes/Research/Projects/2025/AI/Machine_Learning/Papers/Transformers.md`

## Storage Structure

For a note with `section: "Ideas/Subidea/DeepIdea"`, the following files are created:

### Note File
```
notes/MyProject/Ideas/Subidea/DeepIdea/MyNote.md
```

### Index Files (Created Automatically)
```
notes/MyProject/_index.md
notes/MyProject/Ideas/_index.md
notes/MyProject/Ideas/Subidea/_index.md
notes/MyProject/Ideas/Subidea/DeepIdea/_index.md
```

Each index file:
- Links to its child subsections
- Lists notes in that section
- Is maintained automatically by the API

## Validation Rules

The `section` parameter has the following validation rules:

### ✅ Valid
- Simple sections: `"Ideas"`
- Nested sections: `"Ideas/Subidea"`
- Deep nesting: `"A/B/C/D/E"`
- Spaces (auto-sanitized): `"Work Items/Q1 Planning"`

### ❌ Invalid
- Leading slash: `"/Ideas"` → **Error**
- Trailing slash: `"Ideas/"` → **Error**
- Both: `"/Ideas/"` → **Error**

The API will return a `422 Validation Error` for invalid section paths.

## Sanitization

Each section component is sanitized independently using the following rules:

1. **Whitespace** → Replaced with underscores
2. **Path separators** (`/`, `\`) → Replaced with underscores
3. **Special characters** (`:`, `*`, `?`, `"`, `<`, `>`, `|`, `.`) → Replaced with underscores
4. **Control characters** → Removed

### Example
```
Input:  "Work Items/Q1: Planning"
Output: "Work_Items/Q1__Planning"
Path:   notes/MyProject/Work_Items/Q1__Planning/Note.md
```

## API Endpoints

### POST /api/v1/notes

Create or update a note with nested sections.

**Request:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Notes-Key: ${API_KEY}" \
  --data '{
    "project": "Personal Wiki",
    "section": "Ideas/Tech/AI",
    "title": "GPT Applications",
    "body": "Exploring potential applications of GPT models...",
    "mode": "append"
  }' \
  "${CLOUD_RUN_URL}/api/v1/notes"
```

**Response:**
```json
{
  "status": "ok",
  "path": "notes/Personal_Wiki/Ideas/Tech/AI/GPT_Applications.md",
  "content": "# GPT Applications\n\n## 2025-10-30 12:34:56 UTC\nExploring potential applications of GPT models...\n"
}
```

### GET /api/v1/notes

Retrieve a note with nested sections.

**Request:**
```bash
curl -H "X-Notes-Key: ${API_KEY}" \
  "${CLOUD_RUN_URL}/api/v1/notes?project=Personal%20Wiki&section=Ideas%2FTech%2FAI&title=GPT%20Applications"
```

**Response:**
```json
{
  "status": "ok",
  "path": "notes/Personal_Wiki/Ideas/Tech/AI/GPT_Applications.md",
  "content": "# GPT Applications\n\n## 2025-10-30 12:34:56 UTC\nExploring potential applications of GPT models...\n"
}
```

### GET /api/v1/index

List all notes (returns nested section paths).

**Request:**
```bash
curl -H "X-Notes-Key: ${API_KEY}" \
  "${CLOUD_RUN_URL}/api/v1/index"
```

**Response:**
```json
{
  "status": "ok",
  "projects": [
    {
      "name": "Personal Wiki",
      "sections": [
        {
          "name": "Ideas",
          "notes": ["Simple Note"]
        },
        {
          "name": "Ideas/Tech",
          "notes": ["Tech Note"]
        },
        {
          "name": "Ideas/Tech/AI",
          "notes": ["GPT Applications", "ML Models"]
        }
      ]
    }
  ]
}
```

## Backwards Compatibility

This feature is **fully backwards compatible**:

- ✅ Existing notes with simple sections continue to work
- ✅ API accepts both simple (`"Ideas"`) and nested (`"Ideas/Subidea"`) sections
- ✅ No migration needed for existing data
- ✅ No changes required to existing clients using simple sections

## Use Cases

### Project Organization
```
Projects/
  2025/
    AI/
      Research/
        Papers/
          - Transformers.md
          - BERT.md
      Implementation/
        - Code.md
```

### Knowledge Base
```
Knowledge/
  Programming/
    Python/
      Libraries/
        - NumPy.md
        - Pandas.md
    JavaScript/
      Frameworks/
        - React.md
        - Vue.md
```

### Work Management
```
Work/
  Q1 2025/
    Projects/
      Project A/
        - Requirements.md
        - Design.md
      Project B/
        - Kickoff.md
    Reviews/
      - Performance Review.md
```

## Implementation Details

### Index File Management

When you create a note at `section: "A/B/C"`, the system:

1. Creates/updates `notes/Project/_index.md` with link to "A"
2. Creates `notes/Project/A/_index.md` with link to "B"
3. Creates `notes/Project/A/B/_index.md` with link to "C"
4. Creates `notes/Project/A/B/C/_index.md` with the note link

All index operations are atomic to prevent race conditions in concurrent access.

### Path Generation

The `note_path()` function:
1. Splits the section by `/`
2. Filters out empty parts
3. Sanitizes each part independently
4. Joins them back with `/`
5. Constructs the full path

This ensures that each level of the hierarchy is properly sanitized while maintaining the structure.

## Security

- **Path Traversal Protection**: The forward slashes in section names are treated as logical separators, not filesystem path separators. Each component is sanitized to remove actual path separators.
- **Sanitization**: All existing sanitization rules apply to each section component independently.
- **Validation**: Section paths are validated to prevent malformed inputs.

## Migration from Simple Sections

No migration is needed! You can start using nested sections immediately:

1. Existing notes with simple sections (e.g., `"Ideas"`) continue to work
2. New notes can use nested sections (e.g., `"Ideas/Subidea"`)
3. The index listing API returns both formats

The system handles both formats transparently.
