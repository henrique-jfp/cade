import React from 'react';

export function ResultCard({ item, onWatch, onDownload, onCopyMagnet, isResolving }) {
  const isBook = (item.category || '').toLowerCase() === 'books' || item.title.toLowerCase().includes('epub');

  return (
    <article className="card">
      <div className="card-top">
        {item.metadata?.poster_url ? (
          <img src={item.metadata.poster_url} alt={item.title} className="poster" />
        ) : (
          <div className={`poster placeholder placeholder-${(item.category || 'other').toLowerCase()}`}>
            {item.category || 'N/A'}
          </div>
        )}

        <div className="meta">
          <h3>{item.title}</h3>

          <div className="badges">
            {item.instant_available ? (
              <span className="badge instant">⚡ Instant RD</span>
            ) : (
              <span className="badge unverified">⚠ Não verificado</span>
            )}
            {item.category && item.category !== 'Cam' && <span className="badge category">{item.category}</span>}
            {item.category === 'Cam' && <span className="badge cam-replay">📷 Cam Replay</span>}
          </div>

          <p className="info-line">
            {item.resolution || 'N/A'} • {item.size_label || 'N/A'}
          </p>

          <p className="info-line">
            ⬆ {item.seeders} seeders • ⬇ {item.leechers || 0} leechers
            {item.uploaded_at && ` • 📅 ${item.uploaded_at}`}
          </p>

          {item.metadata?.rating && (
            <p className="info-line">⭐ {item.metadata.rating.toFixed(1)}/10</p>
          )}

          {item.metadata?.genres && item.metadata.genres.length > 0 && (
            <p className="genres">{item.metadata.genres.join(', ')}</p>
          )}

          {item.metadata?.synopsis && <p className="synopsis">{item.metadata.synopsis}</p>}
        </div>
      </div>

      <div className="actions">
        {!isBook && (
          <button onClick={() => onWatch(item)} disabled={isResolving}>
            {item.instant_available ? '▶ Assistir' : '📥 Reproduzir'}
          </button>
        )}
        <button 
          onClick={() => onDownload(item)} 
          disabled={isResolving} 
          className="btn-primary-download"
          title="Baixa o arquivo direto no navegador/celular via HTTPS"
        >
          {isResolving ? '⏳ Resolvendo HTTP...' : '📲 Baixar no Navegador (HTTP)'}
        </button>
        <button 
          onClick={() => onCopyMagnet(item.magnet)} 
          disabled={isResolving}
          className="btn-icon" 
          title="Copiar Link Magnet"
        >
          📋 Magnet
        </button>
      </div>
    </article>
  );
}
