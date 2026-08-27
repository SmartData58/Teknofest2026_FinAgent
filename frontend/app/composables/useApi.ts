/**
 * Backend API adresinin TEK KAYNAĞI + istemci tarafı GET önbelleği.
 *
 * ── Adres ──────────────────────────────────────────────────────────────────
 * Sayfalarda 17 ayrı `fetch('http://localhost:8003/...')` çağrısı vardı.
 * Tünel açmak (VS Code dev tunnel / cloudflared), başka bir porttan sunmak ya
 * da dağıtıma çıkmak için hepsini tek tek düzenlemek gerekiyordu — ve biri
 * unutulduğunda sayfanın yalnızca o bölümü sessizce çalışmıyordu. Artık adres
 * `runtimeConfig.public.apiUrl` üzerinden geliyor ve `.env` ile ayarlanıyor.
 *
 * ── Önbellek ───────────────────────────────────────────────────────────────
 * Backend uçlarına ETag/Cache-Control eklendi, ama ÖLÇTÜK: VS Code dev tunnel
 * yanıtlara `no-cache, no-store` enjekte ediyor ve tarayıcı HTTP önbelleğini
 * tamamen devre dışı bırakıyor. Tünel üzerinden çalışırken sayfalar arası her
 * geçiş 1 MB'lık `/campaigns?limit=1000` yanıtını yeniden indiriyordu.
 *
 * Bu yüzden önbellek uygulama katmanında: `apiGet()` sonuçları bellekte TTL
 * ile tutar ve AYNI ANDA giden istekleri tekilleştirir (dashboard üç uca
 * birden gidiyor; aynı uç iki bileşenden istenirse tek istek atılır).
 * HTTP başlıklarına bağlı olmadığı için tünelde de çalışır.
 */

/** Sondaki eğik çizgi olmadan API kök adresi. */
export const apiTabani = (): string => {
  let taban = ''
  try {
    // useRuntimeConfig yalnızca Nuxt bağlamında çalışır. Bu yardımcı olay
    // işleyicilerinin içinden de çağrıldığı için hata durumunda çökmek
    // yerine yedeğe düşüyoruz.
    const config = useRuntimeConfig()
    taban = String(config?.public?.apiUrl ?? '')
  } catch {
    taban = ''
  }

  if (!taban) {
    // Yapılandırma okunamadıysa geliştirme varsayılanı.
    taban = 'http://localhost:8003'
  }

  return taban.replace(/\/+$/, '')
}

/**
 * Verilen yolu API köküyle birleştirir.
 * `apiUrl` göreli bir değerse (ör. "/api" — ters vekil kurulumu) sonuç da
 * göreli kalır; tarayıcı onu bulunduğu kaynağa göre çözer.
 */
export const apiUrl = (yol: string): string => {
  const temizYol = yol.startsWith('/') ? yol : `/${yol}`
  return `${apiTabani()}${temizYol}`
}

// ---------------------------------------------------------------------------
// GET ÖNBELLEĞİ
// ---------------------------------------------------------------------------
type Kayit = { veri: Response; zaman: number }

const _onbellek = new Map<string, Kayit>()
const _ucanIstekler = new Map<string, Promise<any>>()

/** Varsayılan tazelik süresi (ms). Kampanya verisi günde birkaç kez değişir. */
const VARSAYILAN_TTL = 5 * 60 * 1000

/**
 * Önbellekli GET — `fetch` ile AYNI arayüz, `Response` döndürür.
 *
 * Bilerek `Response` döndürüyor: sayfalardaki çağrılar iki farklı biçimde
 * yazılmış (`if (res.ok) { await res.json() }` ve `.then(r => r.json())`).
 * Doğrudan veri döndüren bir yardımcı, on yedi çağrı yerinin de yeniden
 * yazılmasını gerektirirdi; `Response` döndürünce değişiklik tek kelimeye
 * iniyor: `fetch(apiUrl(x))` -> `apiFetch(x)`.
 *
 * Gövde bir kez okunabildiği için önbellekte KLON tutuluyor.
 *
 * @param yol   API yolu ("/banks", "/campaigns?limit=1000")
 * @param ttl   ms cinsinden tazelik süresi; 0 verilirse önbellek atlanır
 */
export const apiFetch = async (yol: string, ttl: number = VARSAYILAN_TTL): Promise<Response> => {
  if (ttl > 0) {
    const kayit = _onbellek.get(yol)
    if (kayit && Date.now() - kayit.zaman < ttl) {
      return kayit.veri.clone()
    }
  }

  // Aynı uca eşzamanlı ikinci istek gelirse ilkinin sonucunu paylaş.
  // (Dashboard aynı anda /banks + /campaigns + /top-advantageous istiyor;
  //  iki bileşen aynı ucu isterse tek istek atılsın.)
  const ucan = _ucanIstekler.get(yol)
  if (ucan) return (await ucan).clone()

  const istek = (async () => {
    try {
      const res = await fetch(apiUrl(yol))
      // Yalnızca başarılı yanıt önbelleğe alınır; hata tekrar denenebilmeli.
      if (res.ok && ttl > 0) {
        _onbellek.set(yol, { veri: res.clone(), zaman: Date.now() })
      }
      return res
    } finally {
      _ucanIstekler.delete(yol)
    }
  })()

  _ucanIstekler.set(yol, istek)
  return (await istek).clone()
}

/** Doğrudan JSON isteyenler için ince sarmalayıcı. */
export const apiGet = async (yol: string, ttl: number = VARSAYILAN_TTL): Promise<any> => {
  const res = await apiFetch(yol, ttl)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

/**
 * Önbelleği boşaltır. Yol verilirse yalnızca onunla başlayan girdileri siler.
 * (Veri tazelendiğinde ya da kullanıcı "yenile" dediğinde çağırın.)
 */
export const apiOnbellegiTemizle = (onek?: string): void => {
  if (!onek) {
    _onbellek.clear()
    return
  }
  for (const k of _onbellek.keys()) {
    if (k.startsWith(onek)) _onbellek.delete(k)
  }
}
