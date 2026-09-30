---
source_url: https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/BA2Type.cs
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: upstream-verbatim
trust: "Verbatim third-party C# source, unmodified. Enumerates the two archive kinds."
---

namespace Ba2Tools
{
    /// <summary>
    /// Represents all known BA2 archive types.
    /// </summary>
    /// <seealso cref="BA2Archive" />
    /// <seealso cref="BA2GeneralArchive" />
    /// <seealso cref="BA2TextureArchive" />
    public enum BA2Type
    {
        Unknown,
        General,
        Texture
    }
}
