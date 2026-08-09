# backend/static_handler.py
import re

STATIC_RESPONSES: dict[str, str] = {
    "selamlama": (
        "Merhaba! Katılım bankacılığı kampanyaları ve finansman ürünleri "
        "hakkında nasıl yardımcı olabilirim?"
    ),
    "hal_hatir": (
        "Teşekkür ederim, size yardımcı olmak için buradayım. "
        "Hangi kampanya veya banka hakkında bilgi almak istersiniz?"
    ),
    "tesekkur": "Rica ederim. Başka bir konuda da yardımcı olabilirim.",
    "vedalasma": "İyi günler dilerim. Yeniden görüşmek üzere.",
    "yetenekler": (
        "Kampanyaları bankaya göre listeleyebilir, en düşük kar payı veya en yüksek "
        "ödül gibi karşılaştırmalar yapabilir, kampanya sorularını veritabanı ve "
        "doküman bilgileriyle yanıtlayabilirim."
    ),
}

_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "selamlama",
        r"^(merhaba|merhabalar|meraba|mrhb|selam|selamlar|slm|sa|s\.a|"
        r"selamun\s+aleykum|selamün\s+aleyküm|günaydın|gunaydin|"
        r"hayırlı\s+sabahlar|iyi\s+(günler|gunler|akşamlar|aksamlar|geceler))\b",
    ),
    (
        "hal_hatir",
        r"^(nasılsın|nasilsin|nasilsiniz|nasilsiniz|naber|n'aber|ne\s+haber|"
        r"iyi\s+misin|iyi\s+misiniz|nasıl\s+gidiyor|nasil\s+gidiyor|"
        r"napıyorsun|napyosun|ne\s+yapıyorsun)\b",
    ),
    (
        "tesekkur",
        r"^(teşekkür|tesekkur|teşekkürler|tesekkurler|teşekkür\s+ederim|"
        r"tesekkur\s+ederim|sağol|sagol|saol|eyvallah|eyv|harikasın|supersin|süpersin)\b",
    ),
    (
        "vedalasma",
        r"^(görüşürüz|gorusuruz|baybay|bye|hoşça\s+kal|hoscakal|"
        r"iyi\s+çalışmalar|iyi\s+calismalar|kolay\s+gelsin|tamamdır|tamamdir|"
        r"anladım|anladim)\b",
    ),
    (
        "yetenekler",
        r"^(kimsin|sen\s+kimsin|ne\s+işe\s+yarıyorsun|ne\s+ise\s+yariyorsun|"
        r"ne\s+yapabilirsin|yardım\s+et|yardim|nereden\s+başlamalıyım|"
        r"nereden\s+baslamaliyim)\b",
    ),
)


def sabitle_yanitla(soru: str) -> str | None:
    """LLM gerektirmeyen kısa konuşma mesajlarını yanıtlar."""
    text = (soru or "").strip()
    if not text or len(text.split()) > 6:
        return None

    lowered = text.casefold()
    for response_key, pattern in _PATTERNS:
        if re.search(pattern, lowered):
            return STATIC_RESPONSES[response_key]

    return None