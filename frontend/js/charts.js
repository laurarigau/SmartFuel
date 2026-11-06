/**
 * SmartFuel - Price History Chart Module
 * Renders line charts of 30-day price trends using Chart.js.
 */

let priceChartInstance = null;

function renderPriceChart(canvasId, priceHistory) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  // Destroy previous chart if it exists
  if (priceChartInstance) {
    priceChartInstance.destroy();
    priceChartInstance = null;
  }

  // Fallback / mock history if none provided
  if (!priceHistory || priceHistory.length === 0) {
    priceHistory = generateMockPriceHistory();
  }

  const labels = priceHistory.map(item => item.date);
  const gas95Prices = priceHistory.map(item => item.gasoline_95);
  const dieselPrices = priceHistory.map(item => item.diesel);

  const ctx = canvas.getContext('2d');
  priceChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Gasolina 95 (€/L)',
          data: gas95Prices,
          borderColor: '#2563EB',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          borderWidth: 2,
          tension: 0.3,
          fill: true,
          pointRadius: 3,
        },
        {
          label: 'Diésel (€/L)',
          data: dieselPrices,
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderWidth: 2,
          tension: 0.3,
          fill: true,
          pointRadius: 3,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y.toFixed(3)} €/L`;
            }
          }
        }
      },
      scales: {
        y: {
          ticks: {
            callback: value => value.toFixed(2) + ' €'
          }
        }
      }
    }
  });
}

function generateMockPriceHistory(basePrice = 1.65, days = 14) {
  const history = [];
  const today = new Date();

  for (let i = days; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];

    // Subtle drift
    const variation = (Math.sin(i / 2) * 0.03) + (Math.random() * 0.01 - 0.005);
    history.push({
      date: dateStr,
      gasoline_95: Number((basePrice + variation).toFixed(3)),
      diesel: Number((basePrice + 0.12 + variation * 0.8).toFixed(3)),
    });
  }
  return history;
}

window.renderPriceChart = renderPriceChart;
window.generateMockPriceHistory = generateMockPriceHistory;
