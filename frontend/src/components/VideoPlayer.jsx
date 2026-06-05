import React from 'react';

export function VideoPlayer({ playerUrl, playerTitle, playerMode, onClose }) {
  if (!playerUrl) return null;

  return (
    <section className="player-section">
      <div className="player-header">
        <h2>Assistindo: {playerTitle}</h2>
        <div className="player-actions">
          <button type="button" onClick={() => window.open(playerUrl, '_blank', 'noopener,noreferrer')}>
            Abrir em nova aba
          </button>
          <button type="button" onClick={onClose}>
            Fechar player
          </button>
        </div>
      </div>

      {playerMode === 'video' ? (
        <video src={playerUrl} controls autoPlay className="video-player" />
      ) : (
        <iframe title={playerTitle} src={playerUrl} className="iframe-player" allow="autoplay; fullscreen" />
      )}
    </section>
  );
}
