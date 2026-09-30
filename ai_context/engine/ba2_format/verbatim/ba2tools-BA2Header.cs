---
source_url: https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/BA2Header.cs
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: upstream-verbatim
trust: "Verbatim third-party C# source, unmodified. Independent corroboration of the 24-byte BA2 header field order."
---

using System;

namespace Ba2Tools
{
    public struct BA2Header
    {
        /// <summary>
        /// Archive signature.
        /// </summary>
        public byte[] Signature;

        /// <summary>
        /// Archive version.
        /// </summary>
        public UInt32 Version;

        /// <summary>
        /// Archive type.
        /// </summary>
        public byte[] ArchiveType;

        /// <summary>
        /// Total files in archive.
        /// </summary>
        public UInt32 TotalFiles;

        /// <summary>
        /// Offset to name table.
        /// </summary>
        public UInt64 NameTableOffset;
    }
}
