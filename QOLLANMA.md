# Beatframe — foydalanish qo'llanmasi

## 0. Har safar boshlashda

```bash
cd ~/Desktop/"YouTube content"/beatframe
source .venv/bin/activate
```
Qator boshida `(.venv)` paydo bo'lsa, tayyor. `beatframe: command not found` chiqsa, ikkinchi qatorni unutgansiz.

## 1. Yangi video yaratish

```bash
beatframe new neanderthal --title "There's a Neanderthal Inside You"
```
`projects/neanderthal/neanderthal.yaml` fayli tayyor namuna bilan yaratiladi. Uni VS Code'da oching:
```bash
code projects/neanderthal/neanderthal.yaml
```

## 2. Script yozish (yaml fayl)

Har bir **beat** — narrator aytadigan bitta gap va uning ostidagi sahna:

```yaml
beats:
  - text: "Narrator aytadigan gap (inglizcha)."
    scene: statement                # qaysi shablon
    chapter: "Bob nomi"             # ixtiyoriy: YouTube bobi shu yerdan boshlanadi
    params: {text: "Ekranda chiqadigan matn.", highlight: "matn"}
```

Qoidalar:
- `text` — ovozga aylanadigan matn. Sahna uzunligi shu ovozga qarab avtomatik belgilanadi.
- Bitta beat'da 1–3 ta gap bo'lsin. Uzun paragrafni bir nechta beat'ga bo'ling: tasvir tez-tez almashib turadi, tomoshabin zerikmaydi.
- `scene` va `params` ro'yxatini ko'rish uchun:
  ```bash
  beatframe templates
  ```
- Bo'sh joylar (probel) muhim: `- text`, `scene`, `params` bir xil chiziqda turishi kerak.

## 3. Tekshirish

```bash
beatframe check projects/neanderthal/neanderthal.yaml
```
Xato bo'lsa, qaysi beat'da va nima noto'g'ri ekanini yozadi. Masalan, shablon nomida xato bo'lsa, `unknown scene` chiqadi.

## 4. Tezkor ko'rish (480p)

```bash
beatframe preview projects/neanderthal/neanderthal.yaml            # hammasi
beatframe preview projects/neanderthal/neanderthal.yaml --beats 3  # faqat 3-beat
beatframe preview projects/neanderthal/neanderthal.yaml --beats 2-5
```
Natija: `projects/neanderthal/output/preview.mp4`. Ochish uchun:
```bash
xdg-open projects/neanderthal/output/preview.mp4
```

## 5. Tuzatish

yaml faylni o'zgartirib, preview'ni qayta ishga tushiring. **Faqat o'zgargan beat'lar qayta render bo'ladi**, qolganlari keshdan olinadi (`(cached)` deb yoziladi).

## 6. Yakuniy video (1080p)

```bash
beatframe make projects/neanderthal/neanderthal.yaml
```
`output/` papkasida chiqadigan fayllar:

| Fayl | Nima qilinadi |
|---|---|
| `final.mp4` | YouTube'ga yuklanadi |
| `subtitles.srt` | Studio → Subtitles → Upload file |
| `chapters.txt` | description'ga nusxa ko'chiriladi |
| `thumbs/` | muqova uchun 5 ta kadr |

## Ovoz sozlamalari

```yaml
voice:
  provider: edge
  name: en-US-AndrewNeural   # boshqa ovozlar: en-US-BrianNeural, en-GB-RyanNeural
  rate: "-5%"                # sekinroq: "-10%", tezroq: "+5%"
```
Barcha inglizcha ovozlar ro'yxati:
```bash
edge-tts --list-voices | grep en-
```
O'z ovozingiz yoki boshqa TTS'dan olingan fayllar bilan ishlash:
```yaml
voice:
  provider: files
  files_dir: projects/neanderthal/voice   # ichida 001.mp3, 002.mp3, ... har beat uchun bittadan
```

## Muammolar

| Belgi | Yechim |
|---|---|
| `command not found` | `source .venv/bin/activate` |
| `unknown scene` | `beatframe templates` bilan nomni tekshiring |
| yaml xatosi (`mapping values...`) | bo'sh joylar va qo'shtirnoqlarni tekshiring. Matnda `:` bo'lsa, butun matnni `"..."` ichiga oling |
| ovoz yaratilmayapti | internetni tekshiring |
| hammasini noldan render qilish kerak | `beatframe clean projects/.../xxx.yaml` |

## Qachon menga murojaat qilish kerak

- **Yangi sahna turi kerak** (masalan, miya, ko'z, xarita yoki grafik). Uni shablon sifatida yozib beraman, keyin o'zingiz ishlatasiz.
- Script yoki sarlavha bo'yicha yordam kerak bo'lsa.
- Tushunarsiz xato chiqsa — terminal natijasini yuboring.
