---
paths:
  - "client/**"
---

# Aturan Unity / C#

## Arsitektur
- Namespace mengikuti assembly: `Game.Core`, `Game.World`, `Game.Player`, `Game.Vehicles`, `Game.Exploration`, `Game.Save`, `Game.Net`, `Game.UI`. Satu folder di `Assets/_Project/Scripts/` = satu `.asmdef`.
- Arah dependensi: `UI → gameplay → Core`; `Save → Net → Core`. Modul gameplay **dilarang** mereferensikan `Game.UI`. UI hanya membaca state lewat event bus / ViewModel, tidak memutasi state gameplay langsung.
- Semua HTTP lewat `Game.Net.ApiClient`; dilarang `UnityWebRequest` langsung di modul lain.
- Semua baca/tulis save lewat `Game.Save`; dilarang `File.*`/`PlayerPrefs` untuk progres di modul lain.
- Refresh token disimpan di penyimpanan aman OS (DPAPI/Credential Manager), bukan `PlayerPrefs` atau file teks.
- HUD & menu memakai UI Toolkit (UXML + USS).

## Konvensi kode
- Penamaan: class/method/property `PascalCase`; field private `_camelCase`; parameter/lokal `camelCase`; konstanta `PascalCase`. Nama file = nama class.
- Gunakan `[SerializeField] private` alih-alih field `public` untuk inspector.
- Konstanta tuning di ScriptableObject config, bukan di kode.
- Async: `Awaitable` / `async` dengan `CancellationToken` (`destroyCancellationToken`); hindari coroutine untuk kode baru.
- Aktifkan nullable reference types di setiap `.asmdef` baru bila memungkinkan.

## Performa
- Semua gerak memakai `Time.deltaTime`; fisika di `FixedUpdate`.
- Nol alokasi GC di jalur `Update` gameplay: tanpa LINQ, `new` koleksi, boxing, string concat, atau `GetComponent` per frame. Cache referensi di `Awake`.
- Konten dunia dimuat lewat Addressables per chunk. Dilarang `Resources.Load` dan dilarang memuat seluruh dunia sekaligus. Setiap handle yang dimuat WAJIB dilepas (`Release`).
- Bangunan Tier A/B wajib punya LOD Group; Tier C memakai atlas tekstur.
- HUD yang mahal (speedometer, minimap) diperbarui maksimal 10×/detik.
- Client tidak mengirim posisi per frame; sinkron hanya lewat batch `POST /v1/me/sync` (interval 60 detik + event penting).

## Aset
- Nama aset `kebab-case`: `motor-bebek.fbx`, `masjid-al-ikhlas-lod0.fbx`, `rumah-warga-tier-c-atlas.png`.
- 1 unit = 1 meter, pivot di dasar objek, sumbu Y ke atas, skala 1 saat impor.
- Jangan mengedit `.unity`/`.prefab` secara teks kecuali perubahan kecil yang pasti aman; selalu commit file `.meta`.

## Testing
- Logika murni (aturan unlock, merge save, konversi koordinat, tuning kendaraan) di-test EditMode; alur scene di-test PlayMode.
- Test EditMode harus lulus (CI GameCI) sebelum task dinyatakan selesai.
