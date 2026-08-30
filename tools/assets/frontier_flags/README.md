# Frontier flag source assets

These files are immutable source inputs for `tools/generate_frontier_polity_flags.py`.

- `goryeo_phoenix_reference.png`: user-supplied reference. The generator extracts only the central phoenix and connected cloud ornament; the hoist teeth and colour bars are excluded.
- `tangut_xia_u17d32_mask.png`: monochrome glyph mask for Tangut `𗴲` (U+17D32, Li Fanwen 2008 no. 0071, “summer / Xia”). It was rendered from Noto Serif Tangut v2.170, distributed under the SIL Open Font License 1.1: <https://github.com/notofonts/tangut/releases/tag/NotoSerifTangut-v2.170>.

The generator embeds neither the font nor any runtime network dependency. Do not hand-edit generated TGA files; change the source asset or generator and regenerate the whole batch.
