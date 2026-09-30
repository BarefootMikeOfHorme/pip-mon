---
source_url: https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/README.md
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: upstream-verbatim
trust: "Verbatim third-party file, unmodified. Describes tiny hand-built BA2 fixtures, which independently confirm the 24-byte header and version 1 as valid."
---

# Test BA2 archives

**Don't forget to update tests when updating test archives** 

* GeneralHeaderOnly.ba2 — contains only header, 0 files, no name table.
* GeneralHeaderOnlyInvalidVersion.ba2 — same as previous, but contains version 153 instead of valid version 1.
* GeneralOneFile.ba2 — contains header, 1 text file (test.txt), 1 name table entry (test.txt).
* InvalidArchive.txt — plain text file, not archive at all.
