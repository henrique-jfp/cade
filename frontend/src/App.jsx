import { useMemo, useState } from 'react'
import { resolveMagnet, searchInstant } from './api'
import { Header } from './components/Header'
import { SearchForm } from './components/SearchForm'
import { ResultCard } from './components/ResultCard'
import { VideoPlayer } from './components/VideoPlayer'

function App() {
  const [query, setQuery] = useState('matrix')
  const [mediaType, setMediaType] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [warning, setWarning] = useState('')
  const [results, setResults] = useState([])
  const [sortBy, setSortBy] = useState('relevance')
  const [onlyInstant, setOnlyInstant] = useState(false)
  
  const [playerUrl, setPlayerUrl] = useState('')
  const [playerTitle, setPlayerTitle] = useState('')
  const [playerMode, setPlayerMode] = useState('video')

  function canUseVideoTag(url) {
    if (!url) return false
    const cleanUrl = url.split('?')[0].toLowerCase()
    return cleanUrl.endsWith('.mp4') || cleanUrl.endsWith('.webm') || cleanUrl.endsWith('.m3u8')
  }

  function getUploadedTimestamp(value) {
    if (!value) return 0
    const timestamp = Date.parse(value)
    return Number.isNaN(timestamp) ? 0 : timestamp
  }

  const filteredResults = useMemo(() => {
    if (!onlyInstant) return results
    return results.filter(item => item.instant_available)
  }, [results, onlyInstant])

  const sortedResults = useMemo(() => {
    const copy = [...filteredResults]

    switch (sortBy) {
      case 'upload_desc':
        return copy.sort((a, b) => getUploadedTimestamp(b.uploaded_at) - getUploadedTimestamp(a.uploaded_at))
      case 'upload_asc':
        return copy.sort((a, b) => getUploadedTimestamp(a.uploaded_at) - getUploadedTimestamp(b.uploaded_at))
      case 'title_asc':
        return copy.sort((a, b) => (a.title || '').localeCompare(b.title || '', 'pt-BR', { sensitivity: 'base' }))
      case 'title_desc':
        return copy.sort((a, b) => (b.title || '').localeCompare(a.title || '', 'pt-BR', { sensitivity: 'base' }))
      case 'seeders_desc':
        return copy.sort((a, b) => (b.seeders || 0) - (a.seeders || 0))
      case 'seeders_asc':
        return copy.sort((a, b) => (a.seeders || 0) - (b.seeders || 0))
      case 'size_desc':
        return copy.sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0))
      case 'size_asc':
        return copy.sort((a, b) => (a.size_bytes || 0) - (b.size_bytes || 0))
      default:
        return copy
    }
  }, [filteredResults, sortBy])

  function applyQuickMode(mode) {
    if (mode === 'general') {
      setMediaType('all')
      setQuery('')
      return
    }

    if (mode === 'rom') {
      setMediaType('game')
      setQuery('switch homebrew')
    }
  }

  async function onSearch(event) {
    if (event) event.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError('')
    setWarning('')
    try {
      const data = await searchInstant(query, mediaType)
      setResults(data.items || [])
      setWarning(data.warning || '')
    } catch (err) {
      setError(err.message || 'Erro inesperado na busca')
    } finally {
      setLoading(false)
    }
  }

  async function onWatch(item) {
    const magnet = item?.magnet
    const instantAvailable = item?.instant_available

    if (!magnet) return

    if (!instantAvailable) {
      alert('Esse item nao esta como instant no RD. Abrindo magnet direto...')
      window.location.href = magnet
      return
    }

    try {
      const data = await resolveMagnet(magnet)
      if (!data.success || !data.stream_url) {
        alert(data.message || 'Nao foi possivel gerar stream. Abrindo magnet...')
        window.location.href = magnet
        return
      }

      setPlayerTitle(item?.title || data.filename || 'Player')
      setPlayerUrl(data.stream_url)
      setPlayerMode(canUseVideoTag(data.stream_url) ? 'video' : 'iframe')
    } catch (err) {
      alert('Erro ao gerar link RD. Abrindo magnet direto...')
      window.location.href = magnet
    }
  }

  async function onDownload(item) {
    const magnet = item?.magnet
    const instantAvailable = item?.instant_available

    if (!magnet) return

    if (!instantAvailable) {
      window.location.href = magnet
      return
    }

    try {
      const data = await resolveMagnet(magnet)
      const downloadTarget = data.download_url || data.stream_url
      if (!data.success || !downloadTarget) {
        alert(data.message || 'Nao foi possivel gerar link de download. Abrindo magnet...')
        window.location.href = magnet
        return
      }
      window.open(downloadTarget, '_blank', 'noopener,noreferrer')
    } catch (err) {
      alert('Erro ao gerar download RD. Abrindo magnet direto...')
      window.location.href = magnet
    }
  }

  async function onCopyMagnet(magnet) {
    if (!magnet) return
    await navigator.clipboard.writeText(magnet)
    alert('Magnet copiado')
  }

  return (
    <main className="container">
      <Header />

      <section className="quick-modes">
        <h2>Busca Rápida</h2>
        <p className="quick-modes-note">Escolha um modo para começar mais rápido.</p>
        <div className="quick-modes-grid">
          <button type="button" className="quick-mode-card" onClick={() => applyQuickMode('general')}>
            <span className="quick-mode-title">Geral</span>
            <span className="quick-mode-desc">Busca ampla em todas as categorias</span>
          </button>
          <button type="button" className="quick-mode-card" onClick={() => applyQuickMode('rom')}>
            <span className="quick-mode-title">ROM / Homebrew</span>
            <span className="quick-mode-desc">Foco em jogos. Use somente conteúdo legal.</span>
          </button>
        </div>
      </section>

      <SearchForm 
        query={query} 
        setQuery={setQuery} 
        mediaType={mediaType} 
        setMediaType={setMediaType} 
        loading={loading} 
        onSearch={onSearch}
        onlyInstant={onlyInstant}
        setOnlyInstant={setOnlyInstant}
      />

      {error && <p className="error">{error}</p>}
      {warning && <p className="warning">{warning}</p>}

      {results.length > 0 && (
        <section className="sort-controls" aria-label="Controles de ordenacao">
          <label htmlFor="sort-by">Ordenar por:</label>
          <select id="sort-by" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="relevance">Relevancia (padrao)</option>
            <option value="upload_desc">Data de upload (mais recente)</option>
            <option value="upload_asc">Data de upload (mais antiga)</option>
            <option value="title_asc">Ordem alfabetica (A-Z)</option>
            <option value="title_desc">Ordem alfabetica (Z-A)</option>
            <option value="seeders_desc">Seeders (maior para menor)</option>
            <option value="seeders_asc">Seeders (menor para maior)</option>
            <option value="size_desc">Tamanho (maior para menor)</option>
            <option value="size_asc">Tamanho (menor para maior)</option>
          </select>
          <span style={{ marginLeft: 'auto', fontSize: '12px', color: '#9ca3af' }}>
            Exibindo {sortedResults.length} resultados {onlyInstant && '(apenas instantâneos)'}
          </span>
        </section>
      )}

      <VideoPlayer 
        playerUrl={playerUrl} 
        playerTitle={playerTitle} 
        playerMode={playerMode} 
        onClose={() => { setPlayerUrl(''); setPlayerTitle(''); }} 
      />

      <section className="results">
        {sortedResults.map((item) => (
          <ResultCard 
            key={item.infohash} 
            item={item} 
            onWatch={onWatch} 
            onDownload={onDownload} 
            onCopyMagnet={onCopyMagnet} 
          />
        ))}
        {results.length > 0 && sortedResults.length === 0 && (
          <p style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
            Nenhum resultado instantâneo encontrado para esta busca. 
            Desative o filtro "Apenas instantâneos" para ver outros resultados.
          </p>
        )}
      </section>
    </main>
  )
}

export default App
