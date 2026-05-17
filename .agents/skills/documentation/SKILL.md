---
name: generate-docs
version: 1.0.0
description: Generate concise, high-impact documentation. Use this skill when the user asks to create guides, documentation, or explain project structure.
---

# Goal
Create project documentation that is clear, concise, and strictly follows the user's defined structure (Index, Back-links, Numbered Sections, Relative Links).

# Philosophy: Less is More
*   **Conciseness**: Rules over volume.
*   **Clarity**: Simple, direct language (Imperative mood).
*   **Visuals**: Use images to make the documentation as clear as possible.
*   **Connectivity**: Every file mention MUST be a relative link.

# Structure Standard
Every documentation file must follow this exact template:

```markdown
# [Title]

## Index

1. [Section 1 Name](#1-section-1-name)
2. [Section 2 Name](#2-section-2-name)
3. [Next steps](#3-next-steps)

---

## 1 Section 1 Name

- ***Instruction***: Direct command.
- ***Visuals***:
    ![Example](./img/example_image_name.png)
- ***File References***:
    - Edit [config.yaml](../config.yaml)
    - Open [terraform/](../terraform/)

[←Index](#index)

## 2 Section 2 Name

Description or steps...

[←Index](#index)

## 3 Next steps

- [Next File Name](./next_file.md)
```

# Examples (Few-Shot)

### Bad Example ❌
"In this section we are going to configure the database. First you need to open the file located at..."

### Good Example ✅
"## 1 Configure Database
- Edit [database.yml](../config/database.yml).
- Set `max_connections: 100`."

# Instructions
1.  **Analyze**: Determine the scope. Split large topics into numbered files.
2.  **Drafting**:
    *   **Mandatory Linking**: Every time you mention a file or directory, YOU MUST create a relative link (e.g., `[README.md](../README.md)`).
    *   **Visuals**: Proactively identify where an image would clarify the step and request/place it (e.g., `![Login Screen](./img/login.png)`).
    *   **Structure**: 
        *   **Always** start with the `## Index`.
        *   **Always** include `[←Index](#index)` at the end of every section.
        *   **NO Verification Section**: Do not add a finalized "Verification" section.
3.  **Refining**:
    *   **Cut the fluff**: No "In this section we will...". Just "Run:".
    *   **Check links**: Ensure anchors work and file paths are correct relative to the doc file.
