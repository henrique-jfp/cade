import React from 'react';

export function SearchForm({ query, setQuery, mediaType, setMediaType, loading, onSearch, onlyInstant, setOnlyInstant }) {
  return (
    <form onSubmit={onSearch} className="search-form">
      <div className="search-row">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar filme, série, game..."
        />
        <select value={mediaType} onChange={(e) => setMediaType(e.target.value)}>
          <option value="all">Tudo</option>
          <option value="movie">Filmes</option>
          <option value="series">Séries</option>
          <option value="anime">Anime</option>
          <option value="game">Jogos</option>
          <option value="music">Música</option>
          <option value="software">Software</option>
          <option value="sports">Esportes</option>
          <option value="adult">Cam/Adulto</option>
        </select>
        <button type="submit" disabled={loading}>
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </div>
      
      <div className="search-options">
        <label className="toggle-label">
          <input 
            type="checkbox" 
            checked={onlyInstant} 
            onChange={(e) => setOnlyInstant(e.target.checked)} 
          />
          <span>Mostrar apenas instantâneos (⚡ RD)</span>
        </label>
      </div>
    </form>
  );
}
