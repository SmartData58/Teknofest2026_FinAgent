# FinAgent — 200 Promptluk Flaw Testi

**Hedef:** `http://localhost:8003/api/chat`  
**Senaryo:** 499

| Kategori | Toplam | Geçti | Kaldı | İnceleme | Hata | Ort. sn |
|---|---:|---:|---:|---:|---:|---:|
| banka_filtre | 30 | 30 | 0 | 0 | 0 | 21.5 |
| belge | 11 | 11 | 0 | 0 | 0 | 35.2 |
| belirsiz | 20 | 20 | 0 | 0 | 0 | 26.3 |
| cok_turlu | 25 | 25 | 0 | 0 | 0 | 26.7 |
| enjeksiyon | 30 | 30 | 0 | 0 | 0 | 32.4 |
| gorsel_ret | 15 | 15 | 0 | 0 | 0 | 27.7 |
| gorsel_yok | 40 | 40 | 0 | 0 | 0 | 32.6 |
| grafik | 25 | 23 | 0 | 2 | 0 | 28.3 |
| halusinasyon | 40 | 40 | 0 | 0 | 0 | 30.8 |
| ingilizce | 40 | 40 | 0 | 0 | 0 | 27.2 |
| kapsam_disi | 20 | 20 | 0 | 0 | 0 | 25.3 |
| kiyas | 30 | 30 | 0 | 0 | 0 | 26.4 |
| liste | 40 | 40 | 0 | 0 | 0 | 30.1 |
| metrik | 25 | 25 | 0 | 0 | 0 | 21.2 |
| persona | 8 | 8 | 0 | 0 | 0 | 23.2 |
| sayisal | 25 | 25 | 0 | 0 | 0 | 26.7 |
| sinir | 15 | 15 | 0 | 0 | 0 | 29.5 |
| toplam | 22 | 22 | 0 | 0 | 0 | 29.1 |
| tutarlilik | 8 | 8 | 0 | 0 | 0 | 24.8 |
| yazim | 30 | 30 | 0 | 0 | 0 | 29.0 |

## Sıkı kontrollerde kalanlar

_Yok._
## İnsan gözüyle incelenmeli

- **[grafik] grafik — 'grafikle'** — satır sayısı 1 < beklenen en az 2
- **[grafik] grafik — oran grafiği** — satır sayısı 1 < beklenen en az 2