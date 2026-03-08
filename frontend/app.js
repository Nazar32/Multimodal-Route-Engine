// Якщо сторінка відкрита через file:// — використовуємо localhost
const API_URL = (window.location.protocol === 'file:' || window.location.origin === 'null')
  ? 'http://localhost:8080'
  : window.location.origin;

const FALLBACK_PLACES = [
  'Київ', 'Львів', 'Одеса', 'Харків', 'Дніпро', 'Запоріжжя', 'Вінниця', 'Чернігів'
];

const departureSelect = document.getElementById('departure');
const arrivalSelect = document.getElementById('arrival');
const searchBtn = document.getElementById('search');
const swapBtn = document.getElementById('swap');
const resultsSection = document.getElementById('results');
const routesList = document.getElementById('routes-list');
const routeSummary = document.getElementById('route-summary');
const emptyState = document.getElementById('empty-state');
const loadingSection = document.getElementById('loading');
const errorSection = document.getElementById('error');
const errorMessage = document.getElementById('error-message');

async function loadPlaces() {
  try {
    const res = await fetch(`${API_URL}/places`);
    if (!res.ok) throw new Error('Не вдалося завантажити населені пункти');
    const places = await res.json();
    if (places && places.length > 0) {
      renderPlaces(places);
    } else {
      renderPlaces(FALLBACK_PLACES.map(name => ({ name })));
    }
  } catch (err) {
    console.error(err);
    renderPlaces(FALLBACK_PLACES.map(name => ({ name })));
    errorSection.hidden = true;
  }
}

function renderPlaces(places) {
  if (!places || places.length === 0) return;
  const options = places.map(p => {
    const name = typeof p === 'string' ? p : (p.name || '');
    return name ? `<option value="${name}">${name}</option>` : '';
  }).filter(Boolean).join('');
  const placeholder = '<option value="">Оберіть місто...</option>';
  departureSelect.innerHTML = placeholder + options;
  arrivalSelect.innerHTML = placeholder + options;
}

async function searchRoutes() {
  const departure = departureSelect.value;
  const arrival = arrivalSelect.value;
  if (!departure || !arrival) {
    errorSection.hidden = false;
    errorMessage.textContent = 'Оберіть місце відправлення та прибуття';
    return;
  }
  if (departure === arrival) {
    errorSection.hidden = false;
    errorMessage.textContent = 'Місце відправлення та прибуття мають відрізнятися';
    return;
  }

  emptyState.hidden = true;
  resultsSection.hidden = true;
  errorSection.hidden = true;
  loadingSection.hidden = false;
  searchBtn.disabled = true;

  try {
    const res = await fetch(`${API_URL}/routes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ departure, arrival }),
    });
    if (!res.ok) throw new Error('Помилка пошуку маршрутів');
    const data = await res.json();
    renderRoutes(data);
  } catch (err) {
    console.error(err);
    errorSection.hidden = false;
    errorMessage.textContent = err.message || 'Не вдалося знайти маршрути';
  } finally {
    loadingSection.hidden = true;
    searchBtn.disabled = false;
  }
}

function renderRoutes(data) {
  routeSummary.textContent = `${data.departure} → ${data.arrival}`;
  routesList.innerHTML = '';

  if (!data.routes || data.routes.length === 0) {
    routesList.innerHTML = '<p class="empty-msg">Маршрути не знайдено</p>';
  } else {
    data.routes.forEach((route, i) => {
      const card = document.createElement('div');
      card.className = 'route-card';
      const isMultimodal = route.transport_types?.includes('railway') && route.transport_types?.includes('road');
      const transport = isMultimodal ? 'multimodal' : (route.transport_types?.includes('railway') ? 'railway' : 'road');
      const transportLabel = isMultimodal ? 'Авто + Залізниця' : (transport === 'railway' ? 'Залізниця' : 'Авто');
      const segmentsHtml = route.segments.map(s => {
        const details = s.details ? Object.entries(s.details).map(([k, v]) => `${k}: ${v}`).join(', ') : '';
        const transportIcon = s.transport === 'railway' ? '🚂' : '🚗';
        return `<div class="segment">
          <span class="segment-path">${transportIcon} ${s.from_place} → ${s.to_place}</span>
          ${details ? `<br><small>${details}</small>` : ''}
        </div>`;
      }).join('');
      const stats = [];
      if (route.total_distance_km) stats.push(`<span>📏 ${route.total_distance_km} км</span>`);
      if (route.total_duration_min) stats.push(`<span>⏱ ${Math.floor(route.total_duration_min / 60)} год ${route.total_duration_min % 60} хв</span>`);
      card.innerHTML = `
        <span class="transport-badge ${transport}">${transportLabel}</span>
        ${segmentsHtml}
        <div class="stats">${stats.join('')}</div>
      `;
      routesList.appendChild(card);
    });
  }

  resultsSection.hidden = false;
}

swapBtn.addEventListener('click', () => {
  const d = departureSelect.value;
  const a = arrivalSelect.value;
  departureSelect.value = a;
  arrivalSelect.value = d;
});

searchBtn.addEventListener('click', searchRoutes);

loadPlaces();
