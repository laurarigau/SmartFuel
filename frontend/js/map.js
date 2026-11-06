/**
 * SmartFuel - Leaflet Map Integration
 * Handles map rendering, marker clustering, station popups, and geolocation.
 */

let mapInstance = null;
let markerClusterGroup = null;
let currentMarkers = new Map();

function initMap(containerId = 'map') {
  if (mapInstance) return mapInstance;

  // Center on Spain
  mapInstance = L.map(containerId, {
    zoomControl: false,
  }).setView([40.4168, -3.7038], 6);

  // Zoom control in top-right
  L.control.zoom({ position: 'topright' }).addTo(mapInstance);

  // CartoDB Positron tiles (clean, light)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(mapInstance);

  // Initialize marker cluster group
  markerClusterGroup = L.markerClusterGroup({
    chunkedLoading: true,
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
  });

  mapInstance.addLayer(markerClusterGroup);

  return mapInstance;
}

function renderStationsOnMap(stations, onStationSelect) {
  if (!markerClusterGroup) return;

  markerClusterGroup.clearLayers();
  currentMarkers.clear();

  stations.forEach(station => {
    if (!station.latitude || !station.longitude) return;

    const lat = parseFloat(station.latitude);
    const lon = parseFloat(station.longitude);
    if (isNaN(lat) || isNaN(lon)) return;

    // Custom marker icon based on price
    const icon = createPriceMarkerIcon(station);

    const marker = L.marker([lat, lon], { icon: icon });

    // Popup content
    const popupContent = buildPopupContent(station);
    marker.bindPopup(popupContent);

    marker.on('click', () => {
      if (typeof onStationSelect === 'function') {
        onStationSelect(station);
      }
    });

    currentMarkers.set(String(station.station_id), marker);
    markerClusterGroup.addLayer(marker);
  });
}

function createPriceMarkerIcon(station) {
  const price = station.gasoline_95_price || station.diesel_price || 0;
  let colorClass = 'marker-mid';

  // Relative coloring
  if (price < 1.60) {
    colorClass = 'marker-cheap';
  } else if (price > 1.75) {
    colorClass = 'marker-expensive';
  }

  return L.divIcon({
    className: 'custom-station-marker',
    html: `<div class="station-pin ${colorClass}">
             <span>${price ? price.toFixed(2) : '—'}€</span>
           </div>`,
    iconSize: [44, 24],
    iconAnchor: [22, 24],
  });
}

function buildPopupContent(station) {
  const gas95 = station.gasoline_95_price ? `${station.gasoline_95_price.toFixed(3)} €/L` : '—';
  const diesel = station.diesel_price ? `${station.diesel_price.toFixed(3)} €/L` : '—';
  const pred = station.prediction || 'STABLE';
  const predClass = pred === 'UP' ? 'badge--danger' : 'badge--success';
  const predIcon = pred === 'UP' ? '↑ Sube' : '↓ Estable/Baja';

  return `
    <div class="station-popup">
      <div class="station-popup__header">
        <h4>${escapeHtml(station.station_name || 'Gasolinera')}</h4>
        <span class="prediction-badge ${predClass}">${predIcon}</span>
      </div>
      <p class="station-popup__address">${escapeHtml(station.address || '')}, ${escapeHtml(station.municipality || '')}</p>
      <div class="station-popup__prices">
        <div class="price-pill">
          <span class="fuel-label">Gasolina 95</span>
          <span class="fuel-price">${gas95}</span>
        </div>
        <div class="price-pill">
          <span class="fuel-label">Diésel</span>
          <span class="fuel-price">${diesel}</span>
        </div>
      </div>
      <button class="btn btn--primary btn--sm btn--block view-details-btn" data-station-id="${station.station_id}">
        Ver Detalles y Previsión
      </button>
    </div>
  `;
}

function focusStationOnMap(station) {
  if (!mapInstance || !station) return;
  const lat = parseFloat(station.latitude);
  const lon = parseFloat(station.longitude);
  if (!isNaN(lat) && !isNaN(lon)) {
    mapInstance.setView([lat, lon], 14);
    const marker = currentMarkers.get(String(station.station_id));
    if (marker) {
      markerClusterGroup.zoomToShowLayer(marker, () => {
        marker.openPopup();
      });
    }
  }
}

function getUserLocation(onSuccess, onError) {
  if (!navigator.geolocation) {
    if (onError) onError(new Error('Geolocation not supported by your browser'));
    return;
  }

  navigator.geolocation.getCurrentPosition(
    position => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      if (mapInstance) {
        mapInstance.setView([lat, lon], 13);
        L.circleMarker([lat, lon], {
          radius: 8,
          fillColor: '#2563EB',
          color: '#ffffff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.9,
        }).addTo(mapInstance).bindPopup('Tu ubicación').openPopup();
      }
      if (onSuccess) onSuccess({ lat, lon });
    },
    error => {
      if (onError) onError(error);
    }
  );
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

window.initMap = initMap;
window.renderStationsOnMap = renderStationsOnMap;
window.focusStationOnMap = focusStationOnMap;
window.getUserLocation = getUserLocation;
