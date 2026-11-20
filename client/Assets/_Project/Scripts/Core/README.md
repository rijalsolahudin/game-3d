# Game.Core

Fondasi bersama semua modul (ARC §2.3). Dua infrastruktur utama: **event bus** dan **config ScriptableObject**.

## Event bus (`Game.Core.Events`)

Sistem saling berkomunikasi lewat event bertipe tanpa saling mereferensikan. UI hanya *mendengarkan* event dari gameplay; gameplay tidak pernah tahu UI ada.

```csharp
// 1. Definisikan event sebagai struct (wajib struct: publish tanpa boxing/alokasi).
public readonly struct LocationDiscovered
{
    public readonly int PoiId;
    public LocationDiscovered(int poiId) => PoiId = poiId;
}

// 2. Publish dari mana saja, aman di Update (nol GC alloc).
EventBus.Publish(new LocationDiscovered(poiId));

// 3a. MonoBehaviour yang hanya perlu event selama aktif (pola yang direkomendasikan).
//     Dispose di OnDisable melepas langganan dan registrasinya pada destroyCancellationToken,
//     jadi siklus enable/disable berulang tidak menumpuk apa pun. Bila OnDisable terlewat
//     (mis. exception), langganan tetap dilepas saat objek di-destroy.
private EventSubscription<LocationDiscovered> _subscription;
private void OnEnable() => _subscription = this.SubscribeUntilDestroyed<LocationDiscovered>(OnLocationDiscovered);
private void OnDisable() => _subscription.Dispose();
private void OnLocationDiscovered(in LocationDiscovered evt) { /* ... */ }

// 3b. MonoBehaviour yang mendengarkan sepanjang hidupnya: subscribe sekali, tanpa unsubscribe manual.
private void Awake() => this.SubscribeUntilDestroyed<LocationDiscovered>(OnLocationDiscovered);

// 3c. Kelas non-MonoBehaviour: simpan token dari EventBus.Subscribe dan Dispose saat selesai.
_subscription = EventBus.Subscribe<LocationDiscovered>(OnLocationDiscovered);
_subscription.Dispose();
```

`SubscribeUntilDestroyed` melempar `ArgumentNullException` bila owner `null`, dan `ObjectDisposedException` bila owner sudah di-destroy.

Aturan & perilaku:

- **Hanya main thread.** Jangan publish dari thread lain/`Task.Run`.
- **Handler berupa method** (method group), bukan lambda yang menangkap variabel: lambda beralokasi saat dibuat dan tidak bisa dideteksi pemiliknya.
- Unsubscribe/subscribe di dalam handler aman. Handler yang dilepas tidak dipanggil lagi pada publish yang sedang berjalan; handler baru mulai menerima pada publish berikutnya.
- Exception di satu handler di-log (`Debug.LogException`) dan tidak menghentikan handler lain.
- Jaring pengaman: handler milik `UnityEngine.Object` yang sudah di-destroy dilepas otomatis saat publish berikutnya, disertai warning. Ini bukan pengganti `Dispose`/`SubscribeUntilDestroyed`.
- State statis di-reset di awal setiap sesi Play (`RuntimeInitializeLoadType.SubsystemRegistration`), aman bila domain reload dimatikan.
- Event membawa data minimal (id, nilai), bukan referensi ke objek gameplay yang bisa dimutasi UI.

## Config ScriptableObject (`Game.Core.Config`)

Semua konstanta tuning (kecepatan, radius, interval, batas) tinggal di aset config, bukan di kode.

1. Turunkan `GameConfig` di modul pemilik, `sealed`, dengan `[CreateAssetMenu(menuName = "Game/Config/...")]`.
2. Field `[SerializeField] private` + `[Tooltip]` + `[Min]`/`[Range]`, expose lewat property read-only.
3. Override `Validate()` untuk aturan antar-field (dipanggil otomatis lewat `OnValidate`).
4. Simpan aset di `Assets/_Project/Settings/` dengan nama `kebab-case` (mis. `player-movement-config.asset`).
5. Sistem menerima config lewat `[SerializeField]` atau konstruktor, dan membaca nilainya saat runtime (jangan disalin ke konstanta).

Contoh acuan: `Game.Player.PlayerMovementConfig` + `Game.Player.PlayerMovementCalculator`.

## State machine game (`Game.Core.Flow`)

Scene di Build Settings: `Boot` (index 0) → `Menu` → `World`. Jalankan game dari `Boot`.

- `GameStateMachine` (murni): Boot → Menu → Loading → Playing ⇄ Paused, Paused → Loading → Menu.
  Transisi lain ditolak dan dicatat sebagai warning. Tiap transisi sah mem-publish `GameStateChanged`.
- `GameFlowController` (scene Boot, `DontDestroyOnLoad`): memuat scene async (`SceneLoader`, `Awaitable`),
  `Time.timeScale = 0` saat Paused, dan mengaktifkan action map `Player` **hanya** saat Playing.
  Tombol pause = action `System/Pause` (Escape / Start gamepad).
- UI tidak memutasi state: kirim `EventBus.Publish(new GameFlowRequested(GameFlowCommand.StartGame))`.
- Controller gameplay (mis. karakter) membaca input dari project-wide actions (`InputSystem.actions`) supaya
  ikut ter-gate, dan/atau mendengarkan `GameStateChanged` lalu cek `evt.AllowsGameplayInput`.
- Tuning (nama scene, durasi minimum loading, prioritas loading) di `Settings/game-flow-config.asset`.
