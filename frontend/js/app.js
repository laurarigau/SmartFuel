/**
 * SmartFuel - Main Application Controller
 * Orchestrates the map, UI events, search/filters, station detail view, and alerts.
 */

// Sample mock data for demo mode (Madrid, Barcelona, Valencia, Sevilla, Bilbao)
const DEMO_STATIONS = [
  {
    station_id: "4375",
    station_name: "REPSOL",
    address: "PASEO DE LA CASTELLANA, 278",
    municipality: "Madrid",
    province: "MADRID",
    latitude: 40.4820,
    longitude: -3.6872,
    gasoline_95_price: 1.689,
    diesel_price: 1.819,
    prediction: "DOWN_OR_STABLE",
    probability: 0.78,
  },
  {
    station_id: "5122",
    station_name: "CEPSA",
    address: "CALLE DE ALCALA, 546",
    municipality: "Madrid",
    province: "MADRID",
    latitude: 40.4431,
    longitude: -3.6267,
    gasoline_95_price: 1.719,
    diesel_price: 1.849,
    prediction: "UP",
    probability: 0.82,
  },
  {
    station_id: "12054",
    station_name: "BP",
    address: "AVENIDA DE AMERICA, 32",
    municipality: "Madrid",
    province: "MADRID",
    latitude: 40.4385,
    longitude: -3.6685,
    gasoline_95_price: 1.699,
    diesel_price: 1.829,
    prediction: "DOWN_OR_STABLE",
    probability: 0.65,
  },
  {
    station_id: "13933",
    station_name: "PLENOIL",
    address: "AVENIDA DE ANDALUCIA, 12",
    municipality: "Madrid",
    province: "MADRID",
    latitude: 40.3752,
    longitude: -3.6923,
    gasoline_95_price: 1.549,
    diesel_price: 1.699,
    prediction: "DOWN_OR_STABLE",
    probability: 0.89,
  },
  {
    station_id: "15000",
    station_name: "BALLENOIL",
    address: "CALLE VILLA DE MADRID, 45",
    municipality: "Getafe",
    province: "MADRID",
    latitude: 40.3082,
    longitude: -3.7327,
    gasoline_95_price: 1.539,
    diesel_price: 1.689,
    prediction: "DOWN_OR_STABLE",
    probability: 0.91,
  },
  {
    station_id: "6001",
    station_name: "REPSOL",
    address: "AVINGUDA DIAGONAL, 696",
    municipality: "Barcelona",
    province: "BARCELONA",
    latitude: 41.3833,
    longitude: 2.1130,
    gasoline_95_price: 1.729,
    diesel_price: 1.859,
    prediction: "UP",
    probability: 0.74,
  },
  {
    station_id: "6002",
    station_name: "CEPSA",
    address: "GRAN VIA DE LES CORTS CATALANES, 302",
    municipality: "Barcelona",
    province: "BARCELONA",
    latitude: 41.3705,
    longitude: 2.1444,
    gasoline_95_price: 1.709,
    diesel_price: 1.839,
    prediction: "DOWN_OR_STABLE",
    probability: 0.63,
  },
  {
    station_id: "6003",
    station_name: "BONAREA",
    address: "CARRER DE SANTANDER, 55",
    municipality: "Barcelona",
    province: "BARCELONA",
    latitude: 41.4285,
    longitude: 2.2045,
    gasoline_95_price: 1.529,
    diesel_price: 1.679,
    prediction: "DOWN_OR_STABLE",
    probability: 0.94,
  },
  {
    station_id: "7001",
    station_name: "GALP",
    address: "AVENIDA DE CATALUÑA, 15",
    municipality: "Valencia",
    province: "VALENCIA",
    latitude: 39.4833,
    longitude: -0.3542,
    gasoline_95_price: 1.679,
    diesel_price: 1.799,
    prediction: "DOWN_OR_STABLE",
    probability: 0.70,
  },
  {
    station_id: "8001",
    station_name: "SHELL",
    address: "AVENIDA DE LA CONSTITUCION, 88",
    municipality: "Sevilla",
    province: "SEVILLA",
    latitude: 37.3850,
    longitude: -5.9930,
    gasoline_95_price: 1.695,
    diesel_price: 1.815,
    prediction: "UP",
    probability: 0.81,
  },
  {
    station_id: "9001",
    station_name: "PETRONOR",
    address: "GRAN VIA DON DIEGO LOPEZ DE HARO, 70",
    municipality: "Bilbao",
    province: "VIZCAYA",
    latitude: 43.2630,
    longitude: -2.9350,
    gasoline_95_price: 1.715,
    diesel_price: 1.835,
    prediction: "DOWN_OR_STABLE",
    probability: 0.68,
  }
];

class SmartFuelApp {
  constructor() {
    this.stations = [];
    this.filteredStations = [];
    this.selectedStation = null;
    this.apiBaseUrl = window.location.origin.includes('localhost')
      ? 'http://localhost:8000'
      : '/api'; // In production, routed through API Gateway
    this.useMockData = true;
  }

  async init() {
    window.initMap('map');
    this.setupEventListeners();
    await this.loadData();
    this.updateStationCount();
  }

  async loadData() {
    try {
      if (!this.useMockData) {
        const resp = await fetch(`${this.apiBaseUrl}/stations?limit=500`);
        if (!resp.ok) throw new Error('API unavailable');
        this.stations = await resp.json();
      } else {
        this.stations = DEMO_STATIONS;
      }
    } catch {
      console.warn('Falling back to demo mock stations');
      this.stations = DEMO_STATIONS;
      this.useMockData = true;
    }

    this.filteredStations = [...this.stations];
    this.renderStations();
    this.renderStationList();
  }

  renderStations() {
    window.renderStationsOnMap(this.filteredStations, station => {
      this.selectStation(station);
    });
  }

  renderStationList() {
    const container = document.getElementById('stationList');
    if (!container) return;

    if (this.filteredStations.length === 0) {
      container.innerHTML = '<div class="station-list-empty">No se encontraron gasolineras con esos filtros.</div>';
      return;
    }

    container.innerHTML = this.filteredStations.map(s => {
      const isUp = s.prediction === 'UP';
      return `
        <div class="station-card" data-id="${s.station_id}">
          <div class="station-card__header">
            <h4>${s.station_name}</h4>
            <span class="prediction-badge ${isUp ? 'badge--danger' : 'badge--success'}">
              ${isUp ? '↑ Sube' : '↓ Estable/Baja'}
            </span>
          </div>
          <p class="station-card__sub">${s.municipality || ''} (${s.province || ''})</p>
          <div class="station-card__prices">
            <span><strong>G95:</strong> ${s.gasoline_95_price ? s.gasoline_95_price.toFixed(3) + '€' : '—'}</span>
            <span><strong>Diésel:</strong> ${s.diesel_price ? s.diesel_price.toFixed(3) + '€' : '—'}</span>
          </div>
        </div>
      `;
    }).join('');

    // Attach click listeners to cards
    container.querySelectorAll('.station-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.dataset.id;
        const station = this.stations.find(s => String(s.station_id) === String(id));
        if (station) {
          this.selectStation(station);
          window.focusStationOnMap(station);
        }
      });
    });
  }

  selectStation(station) {
    this.selectedStation = station;
    const panel = document.getElementById('stationDetail');
    if (!panel) return;

    // Populate panel details
    document.getElementById('detailStationName').textContent = station.station_name;
    document.getElementById('detailStationAddress').textContent = `${station.address}, ${station.municipality}`;
    document.getElementById('detailPriceG95').textContent = station.gasoline_95_price ? `${station.gasoline_95_price.toFixed(3)} €/L` : '—';
    document.getElementById('detailPriceDiesel').textContent = station.diesel_price ? `${station.diesel_price.toFixed(3)} €/L` : '—';

    // Prediction badge
    const predEl = document.getElementById('detailPrediction');
    const isUp = station.prediction === 'UP';
    predEl.className = `prediction-badge ${isUp ? 'badge--danger' : 'badge--success'}`;
    predEl.textContent = isUp
      ? `↑ Subirá los próximos días (${Math.round((station.probability || 0.8) * 100)}% conf.)`
      : `↓ Estable o bajará (${Math.round((station.probability || 0.8) * 100)}% conf.)`;

    // Render price chart
    window.renderPriceChart('priceChart', null);

    // Open detail panel
    panel.classList.add('station-detail--open');
  }

  setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
      searchInput.addEventListener('input', e => {
        const q = e.target.value.toLowerCase().trim();
        this.filteredStations = this.stations.filter(s =>
          (s.station_name && s.station_name.toLowerCase().includes(q)) ||
          (s.municipality && s.municipality.toLowerCase().includes(q)) ||
          (s.province && s.province.toLowerCase().includes(q))
        );
        this.renderStations();
        this.renderStationList();
        this.updateStationCount();
      });
    }

    // Geolocation button
    const locateBtn = document.getElementById('locateBtn');
    if (locateBtn) {
      locateBtn.addEventListener('click', () => {
        window.getUserLocation(
          () => this.showToast('📍 Centrado en tu ubicación'),
          err => this.showToast(`Error de ubicación: ${err.message}`, 'error')
        );
      });
    }

    // Close detail panel
    const closeDetail = document.getElementById('closeDetail');
    if (closeDetail) {
      closeDetail.addEventListener('click', () => {
        document.getElementById('stationDetail')?.classList.remove('station-detail--open');
      });
    }

    // Alert subscription form
    const alertForm = document.getElementById('alertForm');
    if (alertForm) {
      alertForm.addEventListener('submit', async e => {
        e.preventDefault();
        const targetPrice = document.getElementById('alertTargetPrice').value;
        const email = document.getElementById('alertEmail').value;
        const fuelType = document.getElementById('alertFuelType').value;

        try {
          // If we had API Gateway deployed, we would POST to /subscriptions:
          // await fetch(`${this.apiBaseUrl}/subscriptions`, { method: 'POST', body: ... })
          document.getElementById('alertSuccess')?.classList.remove('hidden');
          setTimeout(() => {
            document.getElementById('alertSuccess')?.classList.add('hidden');
            alertForm.reset();
          }, 3000);
        } catch {
          document.getElementById('alertError')?.classList.remove('hidden');
        }
      });
    }

    // Auth modal triggers
    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');
    const authModal = document.getElementById('authModal');
    const closeAuthModal = document.getElementById('closeAuthModal');

    if (loginBtn && authModal) {
      loginBtn.addEventListener('click', () => authModal.classList.add('modal--open'));
    }
    if (signupBtn && authModal) {
      signupBtn.addEventListener('click', () => authModal.classList.add('modal--open'));
    }
    if (closeAuthModal && authModal) {
      closeAuthModal.addEventListener('click', () => authModal.classList.remove('modal--open'));
    }

    // Listen to popup click delegation
    document.addEventListener('click', e => {
      if (e.target && e.target.classList.contains('view-details-btn')) {
        const id = e.target.dataset.stationId;
        const station = this.stations.find(s => String(s.station_id) === String(id));
        if (station) this.selectStation(station);
      }
    });
  }

  updateStationCount() {
    const el = document.getElementById('stationCount');
    if (el) {
      el.textContent = `${this.filteredStations.length} gasolineras`;
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3000);
  }
}

// Boot app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new SmartFuelApp();
  window.app.init();
});
