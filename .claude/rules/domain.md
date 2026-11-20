# Aturan Domain

Sumber: `docs/product-requirements.md` §2 (keputusan D1–D8). Perubahan aturan di sini WAJIB diikuti pembaruan PRD.

- **Faceless (D3, D4):** semua karakter humanoid hanya punya sepasang mata, dirender lewat komponen tunggal `FacelessEyes`. Dilarang menambahkan mesh, tekstur, atau blendshape hidung, mulut, telinga, maupun alis di mana pun. Detail mata: iris + pupil + highlight, kedip, arah pandang, tidak lebih.
- **Kendaraan:** motor & mobil mewarisi satu abstraksi `VehicleController`; parameter (`acceleration`, `maxSpeed`, `handling`, suspensi) di ScriptableObject `VehicleConfig`. Dilarang menduplikasi logika kemudi.
- **Perolehan kendaraan (D5):** motor bebek diberikan di awal; mobil terbuka setelah ≥ 50% POI Tier A ditemukan. Aturan dievaluasi **di server** (`vehicle_models.unlock_rule`). Dilarang menambah mekanisme perolehan lain (toko, mata uang) tanpa memperbarui PRD §2.
- **Aktivitas (D6):** penemuan lokasi, interaksi landmark, koleksi, foto mode. Masing-masing sistem terpisah di `Game.Exploration`.
- **Tier bangunan (D2):** A = landmark dimodelkan manual, B = modular kit di jalan utama, C = procedural dari footprint OSM.
- **Koordinat:** 1 unit = 1 m; X = timur, Z = utara, Y = atas; origin = `worlds.origin`; proyeksi UTM 49S (EPSG:32749); chunk 256 m dengan ID `"{x}_{z}"`. Data geografis di DB dalam SRID 4326.
- **Cakupan (D1):** jangan menambah wilayah di luar batas yang ditetapkan tanpa pembaruan PRD. Floating origin wajib sebelum wilayah melebihi ±8 km dari origin.
- **Privasi (NFR-07):** jangan tampilkan nama pemilik atau data pribadi warga; bangunan pribadi memakai label generik.
- **Lisensi data (NFR-06):** atribusi OSM (ODbL) wajib di kredit; citra satelit berlisensi terbatas hanya untuk referensi modeling, bukan tekstur.
- **Akun (D8):** game tetap bisa dimainkan offline dengan save lokal; akun hanya untuk cloud save. Multiplayer belum direncanakan; bila ditambahkan, aturan auth di `server.md` WAJIB ditulis ulang lebih dulu.
