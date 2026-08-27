import { useI18n } from 'vue-i18n'

export const useTaxonomy = () => {
  const { t, te } = useI18n()

  const normalizeKey = (key: string | null | undefined): string => {
    if (!key) return ''
    return String(key)
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '_')
  }

  const formatTur = (tur: string | null | undefined): string => {
    if (!tur || tur === '-' || tur === 'Bilinmiyor') return '-'
    const norm = normalizeKey(tur)
    
    // i18n sözlüğünde varsa
    if (te(`taxonomy.turler.${norm}`)) {
      return t(`taxonomy.turler.${norm}`)
    }

    // Yedek formatlama
    let clean = norm.replace(/_kampanyasi|_kampanyalari|_urunu/g, '').replace(/_/g, ' ')
    if (te(`taxonomy.turler.${clean.replace(/\s+/g, '_')}`)) {
      return t(`taxonomy.turler.${clean.replace(/\s+/g, '_')}`)
    }
    return clean.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  const formatHedefKitleItem = (item: string): string => {
    const norm = normalizeKey(item)
    if (!norm || norm === 'segment' || norm === 'segment_esnaf') {
      return ''
    }
    if (te(`taxonomy.hedef_kitleler.${norm}`)) {
      return t(`taxonomy.hedef_kitleler.${norm}`)
    }
    return norm.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  const formatHedefKitle = (kitle: string | string[] | null | undefined): string => {
    if (!kitle || kitle === '-' || (Array.isArray(kitle) && kitle.length === 0)) return '-'
    
    let items: string[] = []
    if (Array.isArray(kitle)) {
      items = kitle.map(k => formatHedefKitleItem(k)).filter(Boolean)
    } else {
      const str = String(kitle).trim()
      items = str
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
        .map(formatHedefKitleItem)
        .filter(Boolean)
    }

    return items.length > 0 ? items.join(', ') : '-'
  }

  const formatKategori = (kat: string | null | undefined): string => {
    if (!kat || kat === '-') return '-'
    const norm = normalizeKey(kat).replace(/_kampanyalari|_kampanyasi|-fon/g, '')
    if (te(`taxonomy.kategoriler.${norm}`)) {
      return t(`taxonomy.kategoriler.${norm}`)
    }
    return norm.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  return {
    formatTur,
    formatHedefKitle,
    formatKategori
  }
}
