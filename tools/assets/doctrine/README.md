# Hundred Schools doctrine emblems

These six transparent source images and their generated EU4 sprites share the
aged bronze, jade, patina, and gold-highlight language of the Ritual Teaching
religion emblem. The motifs are deliberately object-based rather than written
characters so they remain distinct from country flags.

| Key | School | Motif |
| --- | --- | --- |
| `ru` | 儒家 | 玉圭与简册 |
| `fa` | 法家 | 法版与度尺 |
| `mo` | 墨家 | 曲尺与墨斗 |
| `dao` | 道家 | 玉璧与云水纹 |
| `bing` | 兵家 | 青铜虎符 |
| `zongheng` | 纵横家 | 交错使节符与绳结 |

The sources were generated with built-in ImageGen on a flat magenta key and
converted to RGBA with the standard chroma-key helper. Rebuild and verify the
64 px and 32 px RLE-TGA sprites with:

```sh
python3 tools/generate_doctrine_emblems.py
python3 tools/generate_doctrine_emblems.py --check
```

The registered sprite names are `GFX_zhx_doctrine_<key>` and
`GFX_zhx_doctrine_<key>_small`. They are intentionally not bound to a specific
GUI widget yet, so the next UI pass can use the same assets in the debate panel,
country presentation, or a sect-style selector without duplicating textures.
