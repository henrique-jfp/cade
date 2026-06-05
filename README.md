# Instant Media Search (Real-Debrid)

Buscador universal de arquivos/mídia que retorna apenas torrents **instantaneamente disponíveis** no cache do Real-Debrid.

## 1) Arquitetura do sistema

### Visão geral

- **Frontend (React + Vite)**
  - Barra de busca
  - Filtro por tipo de mídia (tudo, filmes, séries, jogos, música, software e adulto)
  - Cards de resultado com metadata (TMDB)
  - Ações: assistir, baixar, copiar magnet
- **Backend (FastAPI)**
  - Busca em múltiplos indexadores
  - Extração/normalização de infohash
  - Verificação de cache no Real-Debrid (`/torrents/instantAvailability`)
  - Ranking de resultados
  - Geração de link direto via Real-Debrid
- **Persistência local (SQLite)**
  - Cache de hashes já consultados no Real-Debrid

### Cobertura de tipos de arquivo

- Modo universal para vídeo, áudio, jogos, software e adulto.
- Camgirls via OnScreens/Archivebate (pesquisa automática de replays/archives).
- Suporte opcional ao Jackett para ampliar cobertura de indexadores.

### Fluxo

1. Frontend chama `GET /api/search?q=matrix`.
2. Backend consulta indexadores (exemplo: Jackett opcional + APIBay + YTS para filmes/séries).
3. Backend extrai `infohash` e deduplica resultados.
4. Backend consulta cache local (SQLite) e depois Real-Debrid para hashes não cacheados localmente.
5. Backend filtra somente resultados instantâneos.
6. Backend enriquece com TMDB (poster/sinopse/ano).
7. Frontend mostra cards com ações:
   - `Copiar magnet`
   - `Assistir` / `Baixar` via endpoint `POST /api/actions/resolve`.

## 2) Estrutura de pastas

```
testedd/
  backend/
    app/
      api/
        routes_actions.py
        routes_search.py
      clients/
        real_debrid_client.py
        tmdb_client.py
      core/
        config.py
      db/
        cache_repo.py
      models/
        schemas.py
      services/
        cache_checker.py
        hash_extractor.py
        link_service.py
        result_ranker.py
        torrent_searcher.py
      main.py
    .env.example
    requirements.txt
  frontend/
    src/
      api.js
      App.jsx
      main.jsx
      styles.css
    .env.example
    index.html
    package.json
    vite.config.js
```

## 3) Backend code skeleton

Veja a pasta `backend/app`:

- `services/torrent_searcher.py`: integração com indexadores
- `services/hash_extractor.py`: extração de infohash do magnet/URL
- `clients/real_debrid_client.py`: wrapper de API Real-Debrid
- `services/cache_checker.py`: cache local + consulta RD
- `services/result_ranker.py`: ranking por qualidade/seeders/tamanho
- `services/link_service.py`: geração de link direto (exemplo)

## 4) Exemplo de integração Real-Debrid

Principal método em `backend/app/clients/real_debrid_client.py`:

- `get_instant_availability(infohashes)`
- `add_magnet(magnet)`
- `select_files(torrent_id, "all")`
- `get_torrent_info(torrent_id)`
- `unrestrict_link(link)`

## 5) Exemplo de integração com indexadores

Arquivo `backend/app/services/torrent_searcher.py` inclui:

- `search_apibay(query)`
- `search_yts(query)`
- `search_jackett(query, media_type)` (opcional)
- método agregador `search_all(query, media_type)`

> Observação: APIs públicas mudam com frequência. O código já trata falhas e continua com provedores disponíveis.

## 6) Exemplo de página de busca

Frontend em `frontend/src/App.jsx`:

- campo de busca
- listagem de resultados instantâneos
- botões de assistir/baixar/cópia de magnet

## 7) Como rodar localmente

### Pré-requisitos

- Python 3.11+
- Node.js 20+
- Conta Real-Debrid com API key
- (Opcional) TMDB API key para posters/sinopse
- (Opcional) Jackett para busca universal com mais fontes

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# preencha REAL_DEBRID_API_KEY e opcionalmente TMDB_API_KEY / JACKETT_*
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Abra `http://localhost:5173`.

## Indexadores integrados

### Indexadores públicos nativos:
- **APIBay** - Indexador universal (The Pirate Bay mirror)
- **1337x** - Milhões de torrents
- **YTS** - Filmes com rating IMDB
- **EZTV** - Séries e TV
- **Nyaa** - Anime e conteúdo asiático
- **Sukebei** - Conteúdo adulto (Nyaa adult)
- **PornBay** - Conteúdo adulto via TPB

### Como adicionar mais indexadores adultos via Jackett:

1. Abra `http://127.0.0.1:9117`
2. Clique em **"Add indexer"**
3. Procure e adicione indexadores adultos populares:
   - **Empornium** (requer convite/tracker privado)
   - **PornoLab** (russo, muito grande)
   - **SumoTorrent** (categoria adulto)
   - **TorrentSexy**
   - **Adult-Empire**
4. Configure cada indexador com suas credenciais (se necessário)
5. Reinicie o backend - automaticamente terá acesso a todos

**Nota**: Alguns trackers adultos são privados e exigem convite.

## Segurança e performance

- API key do Real-Debrid somente no backend (`.env`)
- Rate-limit simples por endpoint (pode evoluir para Redis)
- Cache SQLite com TTL para reduzir chamadas ao Real-Debrid
- Para categorias sensíveis (adulto), aplique controle de acesso conforme sua política

## Próximos passos recomendados

- Adicionar autenticação de usuário
- Persistir histórico e biblioteca
- Substituir cache local por Redis
- Implementar bot Telegram
