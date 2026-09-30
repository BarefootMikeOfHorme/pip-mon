---
source_url: https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/Internal/TextureChunk.cs
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: upstream-verbatim
trust: "Verbatim third-party C# source, unmodified. DX10 per-chunk record field order."
---

using System;

namespace Ba2Tools.Internal
{
    /// <summary>
    /// Represents DDS texture chunk.
    /// </summary>
    internal struct TextureChunk
    {
        /// <summary>
        /// Offset to chunk data from beginning of the archive.
        /// </summary>
        public UInt64 Offset;

        /// <summary>
        /// zlib chunk packed size.
        /// </summary>
        public UInt32 PackedLength;

        /// <summary>
        /// Unpacked size of chunk.
        /// </summary>
        public UInt32 UnpackedLength;

        /// <summary>
        /// Start mipmap of texture.
        /// </summary>
        public UInt16 StartMipmap;

        /// <summary>
        /// End mipmap of texture.
        /// </summary>
        public UInt16 EndMipmap;

        public UInt32 Unknown; // 0xBAADF00D
    }
}
