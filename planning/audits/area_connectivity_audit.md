# Area connectivity audit

- Total areas: 939
- Strict bitmap-disconnected: 72
- Still disconnected after explicit adjacencies: 41
- Areas containing empty province references: 0
- Han-region areas checked: 90

## Han areas requiring reassignment

| Area | Localised | Strict components | Gameplay components | Components |
|---|---|---:|---:|---|
| — | — | 0 | 0 | No issues |

## Han areas separated only by a navigable river or defined crossing

| Area | Localised | Bitmap components | Components before crossing |
|---|---|---:|---|
| `east_zhejiang_area` | 会稽 | 2 | 温州(1824)、明州(2149)、台州(4951)、宁海(5005) ｜ 昌国(5004) |
| `jingyi_area` | 荆郢 | 2 | 荆州(2172)、枝江(5345) ｜ 施州(5013)、公安(5014) |
| `wuhan_enan_area` | 江夏 | 2 | 武昌(682)、兴国(5016) ｜ 汉阳(4981)、汉口(5011) |
| `yingtian_area` | 金陵 | 2 | 江宁(1821)、溧水(5057) ｜ 六合(5056) |

## Han areas containing province IDs with no bitmap pixels

| Area | Localised | Empty references |
|---|---|---|
| — | — | None |

## Full-map gameplay-disconnected areas

These include intentional archipelagos and vanilla layouts; review before changing.

| Area | Localised | Components | Provinces |
|---|---|---:|---|
| `aegean_archipelago_area` | aegean_archipelago_area | 4 | 164(164)、3003(3003) ｜ 320(320) ｜ 2348(2348) ｜ 4700(4700) |
| `alaska_area` | alaska_area | 2 | 978(978)、2611(2611)、2612(2612) ｜ 979(979) |
| `angola_namibia_area` | angola_namibia_area | 3 | 1167(1167)、1171(1171)、1172(1172) ｜ 1098(1098) ｜ 1174(1174) |
| `batak_area` | batak_area | 2 | 619(619)、2682(2682)、4811(4811) ｜ 2684(2684) |
| `cap_verde_area` | cap_verde_area | 2 | 1096(1096) ｜ 1111(1111) |
| `chimor_area` | chimor_area | 2 | 812(812)、2821(2821)、2822(2822)、2826(2826) ｜ 2002(2002) |
| `cukurova_area` | cukurova_area | 2 | 327(327)、2302(2302) ｜ 321(321) |
| `denmark_area` | denmark_area | 2 | 12(12)、14(14)、1983(1983) ｜ 1981(1981) |
| `eastern_polynesia_area` | eastern_polynesia_area | 3 | 1244(1244) ｜ 1987(1987) ｜ 1988(1988) |
| `gotaland_area` | gotaland_area | 2 | 2(2)、3(3)、4166(4166) ｜ 25(25) |
| `greater_antilles_area` | greater_antilles_area | 4 | 481(481) ｜ 487(487) ｜ 491(491) ｜ 492(492) |
| `hecate_strait_area` | hecate_strait_area | 2 | 975(975)、2609(2609) ｜ 2022(2022) |
| `indian_ocean_islands_area` | indian_ocean_islands_area | 5 | 574(574) ｜ 1101(1101) ｜ 1248(1248) ｜ 1998(1998) ｜ 1999(1999) |
| `kingdom_of_the_isles_area` | kingdom_of_the_isles_area | 2 | 253(253)、4364(4364) ｜ 4365(4365) |
| `kyushu_area` | kyushu_area | 2 | 1012(1012)、4180(4180)、4181(4181) ｜ 1015(1015) |
| `leeward_islands_area` | leeward_islands_area | 3 | 494(494)、495(495)、496(496) ｜ 493(493) ｜ 1881(1881) |
| `lesser_sunda_islands_area` | lesser_sunda_islands_area | 2 | 631(631)、632(632)、2693(2693) ｜ 634(634) |
| `lucayan_area` | lucayan_area | 2 | 482(482) ｜ 483(483) |
| `macaronesia_area` | macaronesia_area | 3 | 366(366)、4565(4565) ｜ 367(367) ｜ 368(368) |
| `mahra_area` | mahra_area | 2 | 402(402)、4284(4284) ｜ 1099(1099) |
| `mascarenes_area` | mascarenes_area | 3 | 1100(1100) ｜ 1102(1102) ｜ 1103(1103) |
| `melanesia_area` | melanesia_area | 4 | 1236(1236) ｜ 1238(1238) ｜ 1239(1239) ｜ 1986(1986) |
| `micronesia_area` | micronesia_area | 4 | 1241(1241) ｜ 1991(1991) ｜ 1993(1993) ｜ 1994(1994) |
| `minangkabau_area` | minangkabau_area | 2 | 2680(2680)、2681(2681)、4817(4817)、4818(4818) ｜ 2683(2683) |
| `molluca_area` | molluca_area | 3 | 646(646)、647(647) ｜ 645(645) ｜ 2717(2717) |
| `morea_area` | morea_area | 2 | 145(145)、146(146)、1773(1773)、4701(4701) ｜ 163(163) |
| `mozambique_area` | mozambique_area | 2 | 788(788)、1195(1195)、4049(4049) ｜ 4020(4020) |
| `northern_polynesia_area` | northern_polynesia_area | 2 | 1240(1240)、4934(4934)、4935(4935)、4936(4936) ｜ 1997(1997) |
| `palawan_area` | palawan_area | 2 | 655(655)、4356(4356) ｜ 651(651) |
| `polynesia_area` | polynesia_area | 4 | 1243(1243) ｜ 1989(1989) ｜ 1990(1990) ｜ 1992(1992) |
| `sao_tome_area` | sao_tome_area | 2 | 1097(1097) ｜ 1306(1306) |
| `sicily_area` | sicily_area | 2 | 124(124)、2982(2982) ｜ 126(126) |
| `south_atlantic_islands_area` | south_atlantic_islands_area | 2 | 1095(1095) ｜ 2025(2025) |
| `south_korea_area` | south_korea_area | 2 | 737(737)、1013(1013)、4228(4228)、4229(4229) ｜ 2741(2741) |
| `south_sumatra_area` | south_sumatra_area | 2 | 621(621)、622(622)、623(623)、2678(2678) ｜ 2679(2679) |
| `southern_luzon_area` | southern_luzon_area | 2 | 656(656)、2697(2697)、2699(2699)、4349(4349) ｜ 4350(4350) |
| `subarctic_islands_area` | subarctic_islands_area | 3 | 370(370)、371(371) ｜ 1978(1978) ｜ 1979(1979) |
| `timor_area` | timor_area | 3 | 633(633)、635(635)、2695(2695) ｜ 2696(2696) ｜ 2725(2725) |
| `upper_acadia_area` | upper_acadia_area | 2 | 985(985)、2572(2572) ｜ 983(983) |
| `west_micronesia_area` | west_micronesia_area | 3 | 1235(1235) ｜ 1995(1995) ｜ 1996(1996) |
| `windward_islands_area` | windward_islands_area | 2 | 497(497)、498(498)、499(499)、500(500) ｜ 501(501) |
