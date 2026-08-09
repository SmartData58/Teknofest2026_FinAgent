import re
from typing import Optional

# Promptlar
RAG_CEVAP_PROMPTU = """Sen Türkiye'deki katılım bankalarının kampanyalarını bilen bir asistansın.
KURALLAR:
- SADECE aşağıdaki kampanya bilgilerine dayanarak cevap ver.
- Bilgi kampanya metinlerinde yoksa açıkça "elimdeki kampanya verilerinde bu bilgi yok" de. ASLA tahmin etme, sayı uydurma.
- Hangi bankanın hangi kampanyasından bahsettiğini belirt.
- Kısa ve doğal Türkçe ile cevapla (2-5 cümle).
- Sorular yatırım tavsiyesi isterse: kampanya bilgisi verdiğini, tavsiye veremeyeceğini söyle.

KAMPANYA BİLGİLERİ:
{baglam}

{gecmis}SORU: {soru}

CEVAP:"""

STATIK_CEVAP: dict[str, str] = {
    "selamlama": "Merhaba! Katılım bankacılığı kampanyaları ve finansman ürünleri hakkında nasıl yardımcı olabilirim?",
    "hal_hatir": "Teşekkür ederim, size yardımcı olmak için buradayım. Hangi kampanya veya banka hakkında bilgi almak istersiniz?",
    "tesekkur": "Rica ederim. Başka bir konuda da yardımcı olabilirim.",
    "vedalasma": "İyi günler dilerim. Yeniden görüşmek üzere.",
    "yetenekler": "Kampanyaları bankaya göre listeleyebilir, en düşük kar payı veya en yüksek ödül gibi karşılaştırmalar yapabilir, kampanya sorularını veritabanı ve doküman bilgileriyle yanıtlayabilirim.",
}

_PATTERNS: tuple[tuple[str, str], ...] = (
    ("selamlama", r"^(merhaba|merhabalar|meraba|mrhb|selam|selamlar|slm|sa|s\.a|selamun\s+aleykum|selamün\s+aleyküm|günaydın|gunaydin|hayırlı\s+sabahlar|iyi\s+(günler|gunler|akşamlar|aksamlar|geceler))\b"),
    ("hal_hatir", r"^(nasılsın|nasilsin|nasilsiniz|naber|n'aber|ne\s+haber|iyi\s+misin|iyi\s+misiniz|nasıl\s+gidiyor|napıyorsun|napyosun|ne\s+yapıyorsun)\b"),
    ("tesekkur", r"^(teşekkür|tesekkur|teşekkürler|tesekkurler|teşekkür\s+ederim|tesekkur\s+ederim|sağol|sagol|saol|eyvallah|eyv|harikasın|supersin|süpersin)\b"),
    ("vedalasma", r"^(görüşürüz|gorusuruz|baybay|bye|hoşça\s+kal|hoscakal|iyi\s+çalışmalar|iyi\s+calismalar|kolay\s+gelsin|tamamdır|tamamdir|anladım|anladim)\b"),
    ("yetenekler", r"^(kimsin|sen\s+kimsin|ne\s+işe\s+yarıyorsun|ne\s+ise\s+yariyorsun|ne\s+yapabilirsin|yardım\s+et|yardim|nereden\s+başlamalıyım)\b"),
)

def sabitle_yanitla(user_message: str) -> Optional[str]:
    """Kullanıcı mesajı basit bir niyet kalıbıyla eşleşirse statik cevabı döner."""
    msg = user_message.strip().lower()
    for intent, pattern in _PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            return STATIK_CEVAP.get(intent)
    return None