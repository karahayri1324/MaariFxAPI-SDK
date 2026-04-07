# MaarifX API Dokumantasyonu

MaarifX, yapay zeka destekli bir soru cozme platformudur. Ogrenciler fizik, matematik ve fen sorularinin fotograflarini yukler; yapay zeka soruyu adim adim cozer ve istege bagli olarak cozumu dogrudan gorsel uzerine cizer.

Bu dokumantasyon, MaarifX API'sini kendi uygulamaniza entegre etmek icin ihtiyaciniz olan her seyi icerir.

**Base URL:** `https://api2.ogretimsayfam.com`

---

## Icindekiler

1. [Genel Bakis](#genel-bakis)
2. [Hizli Baslangic](#hizli-baslangic)
3. [API Tipleri](#api-tipleri)
4. [Endpoint Referansi](#endpoint-referansi)
5. [SSE Event Tipleri](#sse-event-tipleri)
6. [Python SDK Kullanimi](#python-sdk-kullanimi)
7. [Hata Kodlari](#hata-kodlari)
8. [Ornek Entegrasyon Akislari](#ornek-entegrasyon-akislari)

---

## Genel Bakis

MaarifX API iki farkli kullanim modeli sunar:

| Ozellik | Istek Bazli API | Auth Bazli API |
|---------|----------------|----------------|
| Key formati | `mfx_req_...` | `mfx_auth_...` |
| Hedef kitle | Tekil uygulama | Distributor / platform |
| Kullanici yonetimi | Yok | Alt kullanici sistemi |
| Ucretlendirme | Token bazli | Token bazli |
| Rate limit | Gunluk + aylik | Gunluk + aylik + kullanici basi |

### Ne Yapar?

1. Soru iceren bir gorsel gonderirsiniz
2. MaarifX yapay zekasi soruyu analiz eder ve adim adim cozer
3. Sonuc iki sekilde donebilir:
   - **Metin olarak** (`draw_on_image=false`): Cozum metni token token stream edilir
   - **Gorsel uzerine cizim** (`draw_on_image=true`): Cozum gorsel uzerine cizilir, bir `view_url` doner

---

## Hizli Baslangic

### 1. API Key Alin

Admin dashboard uzerinden API key olusturun. Iki tip key vardir:
- **Istek Bazli** (`mfx_req_...`): Dogrudan istek gonderme
- **Auth Bazli** (`mfx_auth_...`): Kullanici yonetimli distributor modeli

### 2. Python SDK Kurulumu

```bash
pip install maarifx
```

### 3. Ilk Isteginiz

#### Metin Cozum (draw_on_image=false)

```python
from maarifx import MaarifX

client = MaarifX(api_key="mfx_req_...")

# Senkron cozum
result = client.solve("soru.png", draw_on_image=False)
print(result.text)
print(f"Kullanim: {result.usage.input_tokens} input, {result.usage.output_tokens} output")
```

#### Gorsel Uzerine Cizim (draw_on_image=true)

```python
result = client.solve("soru.png", draw_on_image=True)
print(result.view_url)  # Tarayicida acilabilir URL
```

#### Streaming (Token Token)

```python
for event in client.solve_stream("soru.png"):
    if event.type == "token":
        print(event.token, end="", flush=True)
    elif event.type == "thinking":
        pass  # Dusunme tokenleri (isteage bagli)
    elif event.type == "complete":
        print(f"\n\nTamamlandi! Kullanim: {event.usage}")
```

---

## API Tipleri

### Istek Bazli API (`mfx_req_...`)

En basit kullanim modeli. Tek bir API key ile dogrudan istek gonderirsiniz.

- **Ucretlendirme:** $1 / 1M input token, $7 / 1M output token (varsayilan, admin tarafindan ayarlanabilir)
- **Rate limit:** Gunluk ve aylik istek limiti (admin tarafindan ayarlanir)
- **Kullanim alani:** Kendi uygulamanizda dogrudan kullanim

```
POST /v1/solve
Headers:
  X-API-Key: mfx_req_abc123...
```

### Auth Bazli API (`mfx_auth_...`)

Distributor modeli. Kendi kullanicilarinizi MaarifX sistemine kaydedersiniz; her kullanicinin kendi limitleri ve tokeni olur.

- **Alt kullanici kayit sistemi:** `/v1/users/register` ile kullanici olusturma
- **Kullanici basi gunluk limit:** Her alt kullanicinin ayri istek limiti
- **Fraud onleme:** Kullanici bazinda izleme ve limit
- **Kullanim alani:** Egitim platformlari, dershane uygulamalari, okul sistemleri

```
POST /v1/solve
Headers:
  X-API-Key: mfx_auth_abc123...
  X-Sub-User-Token: usr_xyz789...
```

#### Distributor Akisi

```
1. Distributor: POST /v1/users/register  -->  { token: "usr_..." }
2. Distributor tokeni kendi veritabaninda saklar
3. Kullanici soru cozunce:
   Distributor: POST /v1/solve + X-Sub-User-Token: usr_...
4. Her kullanicinin gunluk limiti ayri takip edilir
```

---

## Endpoint Referansi

### POST /v1/solve

Soru cozme endpoint'i. Gorsel gonderin, cozum alin.

**Content-Type:** `multipart/form-data`

#### Headers

| Header | Zorunlu | Aciklama |
|--------|---------|----------|
| `X-API-Key` | Evet | API anahtari (`mfx_req_...` veya `mfx_auth_...`) |
| `X-Sub-User-Token` | Auth tipinde evet | Alt kullanici tokeni (`usr_...`) |

#### Form Parametreleri

| Parametre | Tip | Zorunlu | Varsayilan | Aciklama |
|-----------|-----|---------|------------|----------|
| `image` | File | Evet | - | Soru gorseli (PNG, JPG, WebP) |
| `text` | String | Hayir | `""` | Ek soru metni veya yonerge |
| `draw_on_image` | Boolean | Hayir | `false` | `true` ise cozum gorsel uzerine cizilir |
| `stream` | Boolean | Hayir | `true` | `false` ise senkron JSON cevap doner |
| `detailLevel` | Integer | Hayir | `3` | Cozum detay seviyesi (1-5) |
| `classLevel` | String | Hayir | `null` | Sinif seviyesi (orn: "9", "10", "TYT") |

#### Cevap: Senkron Mod (stream=false)

**draw_on_image=false:**
```json
{
  "requestId": "abc-123",
  "status": "completed",
  "text": "Cozum metni...",
  "usage": {
    "input_tokens": 1500,
    "output_tokens": 3200
  }
}
```

**draw_on_image=true:**
```json
{
  "requestId": "abc-123",
  "status": "completed",
  "view_url": "https://api2.ogretimsayfam.com/public/canvas.html?mode=replay&requestId=abc-123&token=eyJ...",
  "usage": {
    "input_tokens": 1500,
    "output_tokens": 3200
  }
}
```

#### Cevap: Streaming Mod (stream=true, varsayilan)

SSE (Server-Sent Events) formati. Detaylar icin [SSE Event Tipleri](#sse-event-tipleri) bolumune bakin.

#### Response Headers (Streaming Mod)

| Header | Aciklama |
|--------|----------|
| `X-Request-Id` | Istek ID'si |
| `X-RateLimit-Daily-Used` | Bugunki kullanim sayisi |
| `X-RateLimit-Daily-Limit` | Gunluk limit |

---

### POST /v1/users/register

Alt kullanici olusturur. **Sadece auth-bazli API key'ler** icin gecerlidir.

#### Headers

| Header | Zorunlu | Aciklama |
|--------|---------|----------|
| `X-API-Key` | Evet | Auth-bazli API key (`mfx_auth_...`) |

#### Body (JSON)

| Parametre | Tip | Zorunlu | Aciklama |
|-----------|-----|---------|----------|
| `external_id` | String | Evet | Sizin sisteminizde kullanicinin benzersiz ID'si |
| `display_name` | String | Hayir | Kullanici gorunen adi |
| `email` | String | Hayir | Kullanici email adresi |

#### Basarili Cevap (201)

```json
{
  "sub_user_id": "uuid-...",
  "external_id": "ogrenci_42",
  "token": "usr_abc123...",
  "daily_limit": 30,
  "message": "Token sadece bir kez gosterilir, guvenli bir yerde saklayin!"
}
```

> **Onemli:** `token` degeri sadece bir kez doner. Guvenli bir sekilde saklayin!

#### Hata Cevaplari

- `400`: Auth-bazli olmayan key ile cagirildi
- `400`: `external_id` eksik
- `403`: Maksimum kullanici limitine ulasildi
- `409`: Bu `external_id` zaten kayitli

---

### POST /v1/users/verify

Alt kullanici tokenini dogrular.

#### Headers

| Header | Zorunlu | Aciklama |
|--------|---------|----------|
| `X-API-Key` | Evet | Auth-bazli API key (`mfx_auth_...`) |

#### Body (JSON)

| Parametre | Tip | Zorunlu | Aciklama |
|-----------|-----|---------|----------|
| `token` | String | Evet | Dogrulanacak sub-user tokeni |

#### Basarili Cevap (200)

```json
{
  "valid": true,
  "sub_user_id": "uuid-...",
  "external_id": "ogrenci_42",
  "display_name": "Ahmet Yilmaz"
}
```

#### Hata Cevaplari

- `404`: Gecersiz token (`{ "valid": false }`)
- `403`: Kullanici devre disi

---

### GET /v1/users

Tum alt kullanicilari listeler. **Sadece auth-bazli API key'ler** icin gecerlidir.

#### Headers

| Header | Zorunlu | Aciklama |
|--------|---------|----------|
| `X-API-Key` | Evet | Auth-bazli API key (`mfx_auth_...`) |

#### Basarili Cevap (200)

```json
{
  "sub_users": [
    {
      "id": "uuid-...",
      "external_id": "ogrenci_42",
      "display_name": "Ahmet Yilmaz",
      "email": "ahmet@ornek.com",
      "token_prefix": "usr_abc12345",
      "daily_limit": 30,
      "is_active": 1,
      "created_at": "2025-01-15T10:30:00.000Z",
      "last_active_at": "2025-01-16T08:15:00.000Z"
    }
  ],
  "total": 1,
  "active": 1,
  "limit": 10
}
```

---

### DELETE /v1/users/:externalId

Alt kullaniciyi devre disi birakir (silinmez, sadece is_active=0 yapilir).

#### Headers

| Header | Zorunlu | Aciklama |
|--------|---------|----------|
| `X-API-Key` | Evet | Auth-bazli API key (`mfx_auth_...`) |

#### URL Parametreleri

| Parametre | Aciklama |
|-----------|----------|
| `externalId` | Kullanicinin `external_id` degeri |

#### Basarili Cevap (200)

```json
{
  "success": true,
  "message": "Kullanici devre disi birakildi"
}
```

#### Hata Cevaplari

- `404`: Kullanici bulunamadi

---

### GET /v1/usage

API key'in kullanim istatistiklerini dondurur.

#### Headers

| Header | Zorunlu | Aciklama |
|--------|---------|----------|
| `X-API-Key` | Evet | Herhangi bir API key |

#### Basarili Cevap (200)

```json
{
  "today": {
    "requests": 15,
    "input_tokens": 22500,
    "output_tokens": 48000,
    "cost_usd": 0.3585
  },
  "this_month": {
    "requests": 340,
    "input_tokens": 510000,
    "output_tokens": 1088000,
    "cost_usd": 8.126
  },
  "limits": {
    "daily": 100,
    "monthly": 3000
  }
}
```

---

### GET /v1/view/:requestId

Tamamlanmis bir istek icin goruntuleme URL'si olusturur. `draw_on_image=true` ile gonderilen isteklerin sonucunu goruntulemek icin kullanilir.

#### Headers

| Header | Zorunlu | Aciklama |
|--------|---------|----------|
| `X-API-Key` | Evet | Herhangi bir API key |

#### URL Parametreleri

| Parametre | Aciklama |
|-----------|----------|
| `requestId` | Istek ID'si |

#### Basarili Cevap (200)

```json
{
  "view_url": "https://api2.ogretimsayfam.com/public/canvas.html?mode=replay&requestId=abc-123&token=eyJ...",
  "expires_in": 3600,
  "expires_at": "2025-01-16T11:30:00.000Z"
}
```

> **Not:** URL 1 saat gecerlidir. Suresi dolunca bu endpoint'i tekrar cagirarak yeni URL alin.

---

## SSE Event Tipleri

Streaming modda (`stream=true`, varsayilan) sunucu SSE (Server-Sent Events) formati ile yanit doner. Her event'in formati:

```
event: <event_tipi>
data: <json_verisi>
```

### Event Referansi

#### `accepted`

Istek kabul edildi, isleme alindi.

```
event: accepted
data: {"requestId": "abc-123"}
```

#### `status`

Durum guncellenmesi. Siniflandirma veya render bilgisi.

```
event: status
data: {"message": "classifying", "subject": "Fizik - Kuvvet ve Hareket"}
```

```
event: status
data: {"message": "rendering", "step": 3}
```

#### `token`

Cozum metninden bir token (kelime parcasi). **Sadece `draw_on_image=false` modunda gonderilir.**

```
event: token
data: {"token": "Bu soruda "}
```

#### `thinking`

Yapay zekanin dusunme sureci tokenleri. **Sadece `draw_on_image=false` modunda gonderilir.**

```
event: thinking
data: {"token": "Soruda verilen kuvveti analiz edersek..."}
```

#### `thinking_done`

Dusunme sureci tamamlandi, cozum metni basliyor.

```
event: thinking_done
data: {}
```

#### `complete`

Islem tamamlandi. Son event'tir.

**draw_on_image=false:**
```
event: complete
data: {
  "requestId": "abc-123",
  "text": "Tam cozum metni...",
  "usage": {"input_tokens": 1500, "output_tokens": 3200}
}
```

**draw_on_image=true:**
```
event: complete
data: {
  "requestId": "abc-123",
  "view_url": "https://api2.ogretimsayfam.com/public/canvas.html?...",
  "usage": {"input_tokens": 1500, "output_tokens": 3200}
}
```

#### `error`

Bir hata olustu.

```
event: error
data: {"message": "Processor bagli degil veya yanit alamadi"}
```

### Heartbeat

Sunucu baglanti kopmasin diye 15 saniyede bir heartbeat gonderir:

```
: heartbeat
```

Bu satir SSE standartina gore yorum satirdir ve istemci tarafindan goz ardi edilmelidir.

---

## Python SDK Kullanimi

### Kurulum

```bash
pip install maarifx
```

### Senkron Kullanim

```python
from maarifx import MaarifX

client = MaarifX(api_key="mfx_req_...")

# Basit cozum
result = client.solve("fizik_sorusu.png")
print(result.text)

# Gorsel uzerine cizim
result = client.solve("fizik_sorusu.png", draw_on_image=True)
print(result.view_url)

# Ek parametrelerle
result = client.solve(
    "fizik_sorusu.png",
    text="Bu soruyu detayli coz",
    detail_level=5,
    class_level="TYT",
    draw_on_image=False
)
```

### Async Kullanim

```python
import asyncio
from maarifx import AsyncMaarifX

async def main():
    client = AsyncMaarifX(api_key="mfx_req_...")

    result = await client.solve("fizik_sorusu.png")
    print(result.text)

asyncio.run(main())
```

### Streaming

```python
from maarifx import MaarifX

client = MaarifX(api_key="mfx_req_...")

for event in client.solve_stream("fizik_sorusu.png"):
    match event.type:
        case "accepted":
            print(f"Istek kabul edildi: {event.request_id}")
        case "status":
            print(f"Durum: {event.message}")
        case "token":
            print(event.token, end="", flush=True)
        case "thinking":
            pass  # Dusunme tokenleri - isteage bagli gosterebilirsiniz
        case "thinking_done":
            print("\n--- Cozum ---")
        case "complete":
            print(f"\n\nTamamlandi!")
            print(f"Kullanim: {event.usage.input_tokens} input, {event.usage.output_tokens} output")
            if event.view_url:
                print(f"Gorsel: {event.view_url}")
        case "error":
            print(f"Hata: {event.message}")
```

### Auth-Bazli Kullanim (Distributor)

```python
from maarifx import MaarifX

client = MaarifX(api_key="mfx_auth_...")

# 1. Alt kullanici olustur
sub_user = client.register_user(
    external_id="ogrenci_42",
    display_name="Ahmet Yilmaz",
    email="ahmet@ornek.com"
)
print(f"Token: {sub_user.token}")  # Bunu veritabaniniza kaydedin!

# 2. Alt kullanici ile soru coz
result = client.solve(
    "fizik_sorusu.png",
    sub_user_token=sub_user.token
)
print(result.text)

# 3. Kullanicilari listele
users = client.list_users()
for user in users:
    print(f"{user.external_id}: {user.display_name}")

# 4. Kullanim istatistikleri
usage = client.get_usage()
print(f"Bugun: {usage.today.requests} istek, ${usage.today.cost_usd}")

# 5. Kullaniciyi devre disi birak
client.delete_user("ogrenci_42")
```

---

## Hata Kodlari

| Kod | Aciklama | Ornek Senaryo |
|-----|----------|---------------|
| `400` | Gecersiz istek parametreleri | Gorsel eksik, `external_id` eksik |
| `401` | Kimlik dogrulama hatasi | Gecersiz API key, eksik `X-Sub-User-Token` |
| `403` | Yetki hatasi | Devre disi API key, devre disi kullanici, max kullanici limiti |
| `409` | Cakisma | `external_id` zaten kayitli |
| `429` | Rate limit asimi | Gunluk veya aylik istek limiti dolmus |
| `500` | Sunucu hatasi | Beklenmeyen iç hata |
| `502` | Processor hatasi | Processor bagli degil veya yanit vermiyor |

### Hata Cevap Formati

```json
{
  "error": "Hata aciklamasi"
}
```

Rate limit hatalarinda ek bilgi:

```json
{
  "error": "Gunluk istek limitine ulasildi",
  "rateLimit": {
    "used": 100,
    "limit": 100,
    "reset": "gece 00:00"
  }
}
```

---

## Ornek Entegrasyon Akislari

### Akis 1: Basit Soru Cozme (Istek Bazli)

Bir mobil uygulama veya web sitesi icin en basit entegrasyon:

```
Kullanici --> Sizin Backend --> MaarifX API --> Sizin Backend --> Kullanici

1. Kullanici soru fotografini yukluer
2. Backend POST /v1/solve cagrisini yapar (X-API-Key ile)
3. SSE stream'i dinler, tokenleri kullaniciya iletir
4. complete event'i gelince cozum tamamlanir
```

**Ornek Python Backend:**

```python
from flask import Flask, request, Response
from maarifx import MaarifX

app = Flask(__name__)
client = MaarifX(api_key="mfx_req_...")

@app.route("/coz", methods=["POST"])
def coz():
    image = request.files["image"]
    image.save("/tmp/soru.png")

    def generate():
        for event in client.solve_stream("/tmp/soru.png"):
            if event.type == "token":
                yield f"data: {event.token}\n\n"
            elif event.type == "complete":
                yield f"event: done\ndata: ok\n\n"

    return Response(generate(), mimetype="text/event-stream")
```

### Akis 2: Distributor Entegrasyonu (Auth Bazli)

Bir egitim platformu veya dershane icin tam entegrasyon:

```
Ogrenci --> Distributor Backend --> MaarifX API --> Distributor Backend --> Ogrenci

Kayit Akisi:
1. Ogrenci distributor platformuna kayit olur
2. Distributor backend MaarifX'e POST /v1/users/register cagrisi yapar
3. Donen tokeni kendi DB'sine kaydeder

Soru Cozme Akisi:
1. Ogrenci soru fotografini yukler
2. Distributor backend ogrencinin MaarifX tokenini DB'den ceker
3. POST /v1/solve + X-Sub-User-Token ile cagirir
4. Sonucu ogrenciye iletir

Yonetim:
- GET /v1/users ile tum ogrencileri listele
- GET /v1/usage ile kullanim istatistiklerini gor
- DELETE /v1/users/:id ile mezun/ayrilan ogrencileri devre disi birak
```

---

## Ornekler

Tam calisan ornek uygulamalar icin `examples/` klasorune bakin:

| Ornek | Aciklama |
|-------|----------|
| [`examples/backend-python/`](examples/backend-python/) | Flask ile distributor backend ornegi |
| [`examples/backend-node/`](examples/backend-node/) | Express.js ile distributor backend ornegi |
| [`examples/frontend-html/`](examples/frontend-html/) | Tek dosya HTML demo (SSE streaming) |

---

## Destek

Sorulariniz icin: admin dashboard uzerinden iletisime gecin.
