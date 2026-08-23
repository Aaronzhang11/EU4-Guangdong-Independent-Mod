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
64 px, 52 px native-school, and 32 px RLE-TGA sprites with:

```sh
python3 tools/generate_doctrine_emblems.py
python3 tools/generate_doctrine_emblems.py --check
```

The generator requires Pillow; it is already listed in
`tools/map_pipeline/requirements.txt`. The doctrine contract validator also
checks the committed 52 px TGA headers and sprite bindings without importing
Pillow, so missing or malformed runtime textures cannot pass silently.

The registered sprite names are `GFX_zhx_doctrine_<key>`,
`GFX_zhx_doctrine_<key>_school`, and `GFX_zhx_doctrine_<key>_small`. The 52 px
variant is used by the native `religious_school` mirror, so the same emblem
appears in the religion screen, foreign diplomacy header, and at the country's
capital in religion map mode.
The 64 px and 32 px variants remain available for the debate panel and compact
country presentation without duplicating source artwork.

The generator also writes a fully transparent 52 px
`zhx_no_doctrine_school.tga`. EU4 1.37 has no scripted clear-school effect, so
the religion-change lifecycle uses this sentinel to retire an obsolete eastern
display mirror without showing a false doctrine emblem.
