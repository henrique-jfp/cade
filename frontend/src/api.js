const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function throwWithApiDetail(response, fallbackMessage) {
  let detail = ''
  try {
    const data = await response.json()
    detail = data?.detail || ''
  } catch {
    detail = ''
  }
  throw new Error(detail || fallbackMessage)
}

export async function searchInstant(query, mediaType = 'all') {
  const url = new URL(`${API_BASE_URL}/api/search`)
  url.searchParams.set('q', query)
  url.searchParams.set('media_type', mediaType)

  const response = await fetch(url)
  if (!response.ok) {
    await throwWithApiDetail(response, 'Falha ao buscar resultados')
  }
  return response.json()
}

export async function resolveMagnet(magnet) {
  const response = await fetch(`${API_BASE_URL}/api/actions/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ magnet }),
  })

  if (!response.ok) {
    await throwWithApiDetail(response, 'Falha ao resolver link no Real-Debrid')
  }
  return response.json()
}
