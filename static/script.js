/* ═══════════════════════════════════════
   VOYAGER AI — script.js v3
   Features: weather, packing list, PDF,
   skeleton loaders, toast, budget slider,
   scroll progress, resume last trip,
   similar destinations, travel tips,
   save trip modal, email modal
   ═══════════════════════════════════════ */

// ─── State ─────────────────────────────
let currentPlanData   = [];
let currentDestination = '';
let currentDays        = 0;
let currentBudget      = 0;
let currentTripType    = 'Solo';

// ─── Scroll progress bar ───────────────
window.addEventListener('scroll', () => {
  const el = document.getElementById('scrollProgress');
  if (!el) return;
  const scrolled = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
  el.style.width = scrolled + '%';
});

// ─── Toast ─────────────────────────────
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(() => { t.className = 'toast'; }, 3400);
}

// ─── Dark mode ─────────────────────────
function toggleDarkMode() {
  document.body.classList.toggle('dark');
  const icon = document.querySelector('.toggle-icon');
  if (icon) icon.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
  localStorage.setItem('voyager_dark', document.body.classList.contains('dark'));
}

if (localStorage.getItem('voyager_dark') === 'true') {
  document.body.classList.add('dark');
  const icon = document.querySelector('.toggle-icon');
  if (icon) icon.textContent = '☀️';
}

// ─── Slide navigation ──────────────────
function goToOutput() {
  document.getElementById('inputSlide').classList.remove('active');
  document.getElementById('outputSlide').classList.add('active');
  const printBtn = document.getElementById('printBtn');
  const pdfBtn   = document.getElementById('pdfBtn');
  if (printBtn) printBtn.style.display = 'flex';
  if (pdfBtn)   pdfBtn.style.display   = 'flex';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goBack() {
  document.getElementById('outputSlide').classList.remove('active');
  document.getElementById('inputSlide').classList.add('active');
  const printBtn = document.getElementById('printBtn');
  const pdfBtn   = document.getElementById('pdfBtn');
  if (printBtn) printBtn.style.display = 'none';
  if (pdfBtn)   pdfBtn.style.display   = 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ─── City tab switching ─────────────────
function switchCity(index) {
  document.querySelectorAll('.city-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const sec = document.getElementById('city-' + index);
  const tab = document.getElementById('tab-' + index);
  if (sec) sec.classList.add('active');
  if (tab) tab.classList.add('active');
}

// ─── Quick destination fill ─────────────
function fillDestination(dest) {
  const el = document.getElementById('destination');
  if (el) { el.value = dest; el.focus(); }
}

// ─── Budget slider ──────────────────────
function updateBudgetDisplay(val) {
  const num = parseInt(val);
  const disp = document.getElementById('budgetDisplay');
  if (disp) disp.textContent = '₹' + num.toLocaleString('en-IN');
  const hidden = document.getElementById('budget');
  if (hidden) hidden.value = num;

  const slider = document.getElementById('budgetRange');
  if (slider) {
    const pct = ((num - 1000) / (200000 - 1000)) * 100;
    slider.style.background = `linear-gradient(to right, var(--amber) 0%, var(--amber) ${pct}%, var(--border) ${pct}%, var(--border) 100%)`;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  updateBudgetDisplay(25000);
  loadResumeCard();
});

// ─── Resume last trip ───────────────────
function saveLastTrip(destination, days, budget, trip_type) {
  localStorage.setItem('voyager_last_trip', JSON.stringify({ destination, days, budget, trip_type, ts: Date.now() }));
}

function loadResumeCard() {
  try {
    const saved = localStorage.getItem('voyager_last_trip');
    if (!saved) return;
    const trip = JSON.parse(saved);
    const card = document.getElementById('resumeCard');
    const meta = document.getElementById('resumeMeta');
    if (card && meta) {
      meta.textContent = `${trip.destination} · ${trip.days} days · ₹${Number(trip.budget).toLocaleString('en-IN')} · ${trip.trip_type}`;
      card.style.display = 'flex';
    }
  } catch (e) {}
}

function resumeLastTrip() {
  try {
    const trip = JSON.parse(localStorage.getItem('voyager_last_trip'));
    document.getElementById('destination').value = trip.destination;
    document.getElementById('days').value = trip.days;
    updateBudgetDisplay(trip.budget);
    document.getElementById('budgetRange').value = trip.budget;
    const radioEl = document.querySelector(`input[name="trip_type"][value="${trip.trip_type}"]`);
    if (radioEl) radioEl.checked = true;
    showToast('🕐 Last trip restored!', 'success');
  } catch (e) {}
}

// ─── Budget helpers ─────────────────────
function getBudgetSplit(budget, trip_type) {
  const splits = {
    Honeymoon: { Hotels: 0.50, Food: 0.20, Transport: 0.15, Activities: 0.15 },
    Friends:   { Hotels: 0.35, Food: 0.25, Transport: 0.15, Activities: 0.25 },
    Family:    { Hotels: 0.40, Food: 0.20, Transport: 0.25, Activities: 0.15 },
    Solo:      { Hotels: 0.40, Food: 0.20, Transport: 0.20, Activities: 0.20 }
  };
  const ratios = splits[trip_type] || splits['Solo'];
  return {
    Hotels:     Math.round(budget * ratios.Hotels),
    Food:       Math.round(budget * ratios.Food),
    Transport:  Math.round(budget * ratios.Transport),
    Activities: Math.round(budget * ratios.Activities)
  };
}

function getPrice(type) {
  if (type === 'budget') return '₹500–₹1,500/night';
  if (type === 'mid')    return '₹2,000–₹5,000/night';
  return '₹8,000+/night';
}

function getRating(type) {
  if (type === 'budget') return '⭐ 4.0';
  if (type === 'mid')    return '⭐ 4.3';
  return '⭐ 4.7';
}

function getHotelBadge(type) {
  const badges = {
    budget: ['#E8F5E9','#1B5E20','Budget'],
    mid:    ['#E3F2FD','#0D47A1','Mid-range'],
    luxury: ['#FFF8E1','#E65100','Luxury']
  };
  const [bg, color, label] = badges[type] || badges['mid'];
  return `<span style="background:${bg};color:${color};font-size:11px;padding:3px 8px;border-radius:10px;font-weight:500;">${label}</span>`;
}

function getSuggestion(budget, trip_type) {
  const msgs = {
    Honeymoon: '💑 For a romantic getaway, splurge on a private villa or resort — the memories are worth it. Book couple spa packages in advance!',
    Friends:   '🎉 Travelling with friends? Split costs on a group Airbnb — it\'s cheaper than multiple hotel rooms and way more fun.',
    Family:    '👨‍👩‍👧 Family trips work best with a comfortable mid-range hotel near attractions. Always check for family combo ticket discounts!',
    Solo:      budget < 5000
      ? '💡 You\'re on a tight budget — prioritize hostels, local dhabas, and city buses to stretch every rupee.'
      : '💡 Great solo budget! Mix comfortable stays with street food adventures. Weekday bookings save 15–20%.'
  };
  return msgs[trip_type] || msgs['Solo'];
}

// ─── Weather ───────────────────────────
async function fetchWeather(city) {
  try {
    const res = await fetch(`https://wttr.in/${encodeURIComponent(city)}?format=j1`);
    const data = await res.json();
    const cur  = data.current_condition[0];
    return {
      tempC:    cur.temp_C,
      desc:     cur.weatherDesc[0].value,
      humidity: cur.humidity,
      feelsLike: cur.FeelsLikeC,
      windKmph: cur.windspeedKmph,
      icon:     getWeatherIcon(cur.weatherDesc[0].value)
    };
  } catch { return null; }
}

function getWeatherIcon(desc) {
  const d = desc.toLowerCase();
  if (d.includes('sun') || d.includes('clear'))          return '☀️';
  if (d.includes('cloud') || d.includes('overcast'))     return '⛅';
  if (d.includes('rain') || d.includes('drizzle'))       return '🌧️';
  if (d.includes('thunder') || d.includes('storm'))      return '⛈️';
  if (d.includes('snow'))                                return '❄️';
  if (d.includes('fog') || d.includes('mist'))           return '🌫️';
  if (d.includes('wind'))                                return '💨';
  return '🌤️';
}

// ─── Packing list ───────────────────────
function getPackingList(trip_type, days, destination) {
  const dest = destination.toLowerCase();
  const isBeach    = ['goa','maldives','kerala','andaman','puri','pondicherry'].some(d => dest.includes(d));
  const isMountain = ['manali','shimla','leh','ladakh','kashmir','ooty','munnar'].some(d => dest.includes(d));

  const base = {
    '👗 Clothing':  ['T-shirts','Comfortable trousers','Undergarments','Socks','Sleepwear'],
    '🪥 Toiletries':['Toothbrush & toothpaste','Shampoo & conditioner','Sunscreen SPF 50+','Deodorant','Hand sanitizer'],
    '📱 Tech & Docs':['Phone + charger','Power bank','Travel adapter','ID / Passport','Travel insurance'],
    '💊 Health':    ['Personal medication','Pain relievers','Band-aids','Antacids','Mosquito repellent']
  };

  if (isBeach)    base['🏖️ Beach Essentials'] = ['Swimwear','Beach towel','Flip flops','Sunglasses','Waterproof bag'];
  if (isMountain) base['🏔️ Mountain Gear']    = ['Warm jacket','Thermal innerwear','Trekking shoes','Woollen cap & gloves','Rain poncho'];
  if (trip_type === 'Honeymoon') base['💑 Honeymoon'] = ['Formal outfit','Perfume / cologne','Camera','Couple accessories','Candles or gifts'];
  if (trip_type === 'Family')    base['👶 Family']    = ['Kids snacks','Baby wipes','First aid kit','Entertainment for kids','Emergency contact list'];
  if (days >= 7) base['👗 Clothing'].push('Extra outfits','Laundry bag');

  return base;
}

function renderPackingList(trip_type, days, destination) {
  const list = getPackingList(trip_type, days, destination);
  let html = '<div class="packing-categories">';
  for (const [category, items] of Object.entries(list)) {
    html += `<div>
      <div class="packing-category-title">${category}</div>
      <div class="packing-items">
        ${items.map(item => `
          <div class="packing-item" onclick="togglePackItem(this)">
            <span class="packing-check">○</span>
            <span>${item}</span>
          </div>
        `).join('')}
      </div>
    </div>`;
  }
  return html + '</div>';
}

function togglePackItem(el) {
  el.classList.toggle('checked');
  const check = el.querySelector('.packing-check');
  if (check) check.textContent = el.classList.contains('checked') ? '✓' : '○';
}

// ─── Similar destinations ───────────────
function getSimilarDestinations(destination) {
  const map = {
    'Goa':      ['Pondicherry 🌊','Varkala 🏖️','Tarkarli 🤿'],
    'Manali':   ['Spiti Valley 🏔️','Leh-Ladakh ❄️','Kasol 🌿'],
    'Jaipur':   ['Jodhpur 🏰','Udaipur 🌅','Pushkar 🐪'],
    'Kerala':   ['Coorg 🌿','Alleppey 🛶','Munnar ☕'],
    'Varanasi': ['Rishikesh 🕉️','Haridwar 🙏','Prayagraj 🌊'],
    'Mumbai':   ['Pune 🏙️','Nashik 🍇','Alibaug 🌊'],
  };
  for (const [key, vals] of Object.entries(map)) {
    if (destination.toLowerCase().includes(key.toLowerCase())) return vals;
  }
  return ['Goa 🏖️', 'Jaipur 🏰', 'Manali 🏔️', 'Kerala 🌴'];
}

// ─── Travel tips ───────────────────────
function getTravelTips(destination, trip_type) {
  const tips = [
    { icon: '📱', text: 'Download offline maps (Google Maps / Maps.me) before you leave.' },
    { icon: '💳', text: 'Carry some cash — smaller towns may not accept cards everywhere.' },
    { icon: '🌐', text: 'Buy a local SIM or activate roaming before your trip.' },
    { icon: '🔒', text: 'Keep a digital copy of all ID documents in your email.' },
    { icon: '🧴', text: 'Always carry sunscreen, even on cloudy days in India.' },
  ];
  if (trip_type === 'Solo')   tips.push({ icon: '📍', text: 'Share your live location with a trusted contact back home.' });
  if (trip_type === 'Family') tips.push({ icon: '🏥', text: 'Note the nearest hospital or clinic to your accommodation.' });
  if (destination.toLowerCase().includes('goa') || destination.toLowerCase().includes('beach'))
    tips.push({ icon: '🌊', text: 'Swim only at patrolled beaches and watch for red flag warnings.' });
  return tips.slice(0, 5);
}

// ─── Skeleton loaders ───────────────────
function buildSkeletonHTML() {
  return `
    <div class="city-stats">
      ${Array(4).fill('<div class="stat-card"><div class="skeleton sk-title" style="margin:0 auto 8px;width:50%"></div><div class="skeleton sk-line sk-short" style="margin:0 auto;width:60%"></div></div>').join('')}
    </div>
    <div class="results-grid">
      ${Array(6).fill(`
        <div class="skeleton-card">
          <div class="skeleton sk-title"></div>
          <div class="skeleton sk-line"></div>
          <div class="skeleton sk-line sk-med"></div>
          <div class="skeleton sk-line sk-short"></div>
        </div>
      `).join('')}
    </div>
  `;
}

// ─── Loading messages ───────────────────
const LOADING_MSGS = [
  'Crafting your perfect itinerary…',
  'Finding the best hotels for you…',
  'Scouting local restaurants…',
  'Mapping transport routes…',
  'Packing your virtual bags…',
  'Almost there — final touches…'
];
let loadingInterval = null;

function startLoadingMessages() {
  let i = 0;
  const el = document.getElementById('loading-text');
  if (!el) return;
  el.textContent = LOADING_MSGS[0];
  loadingInterval = setInterval(() => {
    i = (i + 1) % LOADING_MSGS.length;
    el.textContent = LOADING_MSGS[i];
  }, 1800);
}

function stopLoadingMessages() {
  if (loadingInterval) clearInterval(loadingInterval);
}

// ─── Chart colors ────────────────────────
const CHART_COLORS = ['#C9853A','#1D9E75','#2563EB','#E23744'];

// ─── PDF download ───────────────────────
function downloadPDF() {
  const el = document.getElementById('result');
  if (!el) return;
  showToast('📄 Preparing PDF…', '');
  const opt = {
    margin: [10,10,10,10],
    filename: 'voyager-itinerary.pdf',
    image: { type: 'jpeg', quality: 0.95 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['avoid-all','css','legacy'] }
  };
  html2pdf().set(opt).from(el).save().then(() => {
    showToast('✅ Itinerary downloaded!', 'success');
  });
}

function printItinerary() { window.print(); }

// ─── Modals ─────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function openSaveModal() {
  if (!currentPlanData.length) { showToast('⚠️ Generate a plan first.', 'error'); return; }
  const res = document.getElementById('saveResult');
  if (res) res.style.display = 'none';
  openModal('saveModal');
}

function openEmailModal() {
  if (!currentPlanData.length) { showToast('⚠️ Generate a plan first.', 'error'); return; }
  const res = document.getElementById('emailResult');
  if (res) res.style.display = 'none';
  openModal('emailModal');
}

// ─── Save trip ──────────────────────────
async function saveTrip() {
  try {
    const res = await fetch('/save-trip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        destination: currentDestination,
        days:        currentDays,
        budget:      currentBudget,
        trip_type:   currentTripType,
        plan:        currentPlanData
      })
    });
    const data = await res.json();
    const el = document.getElementById('saveResult');
    if (el) {
      el.style.display = 'block';
      el.innerHTML = `
        ✅ Trip saved!<br>
        <strong>Share link:</strong><br>
        <a href="${data.share_url}" target="_blank" style="color:var(--amber);word-break:break-all">${data.share_url}</a>
        <br><br>
        <button onclick="navigator.clipboard.writeText('${data.share_url}').then(()=>showToast('📋 Link copied!','success'))"
          style="background:var(--amber);color:#fff;border:none;border-radius:8px;padding:7px 14px;cursor:pointer;font-size:13px;">
          📋 Copy Link
        </button>
      `;
    }
  } catch (e) {
    showToast('❌ Could not save. Please try again.', 'error');
  }
}

// ─── Email itinerary ─────────────────────
async function emailItinerary() {
  const email = document.getElementById('emailInput').value.trim();
  if (!email) { showToast('⚠️ Enter a valid email.', 'error'); return; }

  const el = document.getElementById('emailResult');
  if (el) { el.style.display = 'block'; el.innerHTML = '⏳ Sending…'; }

  try {
    const res = await fetch('/email-itinerary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email:       email,
        destination: currentDestination,
        plan:        currentPlanData
      })
    });
    const data = await res.json();
    if (el) {
      if (data.status === 'sent') {
        el.innerHTML = '✅ Itinerary sent to ' + email;
        showToast('📧 Email sent!', 'success');
      } else {
        el.innerHTML = '❌ ' + (data.error || 'Failed to send.');
      }
    }
  } catch (e) {
    if (el) el.innerHTML = '❌ Something went wrong.';
  }
}

// ─── Main generate ──────────────────────
async function generatePlan() {
  const destination = document.getElementById('destination').value.trim();
  const days        = document.getElementById('days').value.trim();
  const budget      = parseInt(document.getElementById('budget').value);
  const tripTypeEl  = document.querySelector('input[name="trip_type"]:checked');
  const trip_type   = tripTypeEl ? tripTypeEl.value : 'Solo';

  if (!destination || !days || !budget) {
    showToast('⚠️ Please fill in destination, days, and budget.', 'error');
    return;
  }

  // Cache state for save/email
  currentDestination = destination;
  currentDays        = parseInt(days);
  currentBudget      = budget;
  currentTripType    = trip_type;

  document.querySelector('.generate-btn').style.display = 'none';
  document.getElementById('loading-state').classList.remove('hidden');
  startLoadingMessages();
  saveLastTrip(destination, days, budget, trip_type);

  document.getElementById('output-dest-label').textContent = '📍 ' + destination;
  document.getElementById('output-meta').textContent = `${days} days · ₹${Number(budget).toLocaleString('en-IN')} · ${trip_type}`;
  document.getElementById('tabs').innerHTML   = '';
  document.getElementById('result').innerHTML = buildSkeletonHTML();
  goToOutput();

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ destination, days, budget, trip_type })
    });
    const data = await res.json();
    currentPlanData = data;

    let tabsHTML = '', contentHTML = '';

    for (let index = 0; index < data.length; index++) {
      const city     = data[index];
      const daysList = city.plan.split('\n').filter(l => l.trim());
      const similar  = getSimilarDestinations(city.city);
      const tips     = getTravelTips(city.city, trip_type);
      const weatherId = `weather-widget-${index}`;

      tabsHTML += `<button id="tab-${index}" class="tab-btn ${index===0?'active':''}" onclick="switchCity(${index})">📍 ${city.city}</button>`;

      contentHTML += `
      <div id="city-${index}" class="city-section ${index===0?'active':''}">

        <div class="city-stats">
          <div class="stat-card">
            <div class="stat-card-val">${daysList.length}</div>
            <div class="stat-card-label">Days planned</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-val">${city.places ? city.places.length : 0}</div>
            <div class="stat-card-label">Places to visit</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-val">${city.hotels ? city.hotels.length : 0}</div>
            <div class="stat-card-label">Hotel options</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-val">₹${Number(budget).toLocaleString('en-IN')}</div>
            <div class="stat-card-label">Total budget</div>
          </div>
        </div>

        <div class="results-grid">

          <!-- ITINERARY -->
          <div class="card card-full">
            <div class="card-header"><div class="card-icon">📅</div><div class="card-title">Day-by-day itinerary</div></div>
            ${daysList.map((line, di) => {
              const clean = line.replace(/^Day \d+:\s*/, '').replace(/^🗓\s*/, '');
              return `<div class="day-block"><span class="day-num">Day ${di+1}</span><span>${clean}</span></div>`;
            }).join('')}
          </div>

          <!-- WEATHER -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🌤️</div><div class="card-title">Current weather in ${city.city}</div></div>
            <div id="${weatherId}" class="weather-widget"><span class="weather-loading">Loading weather…</span></div>
          </div>

          <!-- PLACES -->
          <div class="card">
            <div class="card-header"><div class="card-icon">📌</div><div class="card-title">Places to visit</div></div>
            ${city.places && city.places.length > 0 ? city.places.map(p => `
              <div class="list-item">
                <div class="item-info"><div class="item-name">${p.name}</div></div>
                <a href="https://www.google.com/maps/search/${encodeURIComponent(p.name+' '+city.city)}" target="_blank">
                  <button class="btn btn-map">View map</button>
                </a>
              </div>
            `).join('') : '<p style="color:var(--muted);font-size:14px;">No specific places listed.</p>'}
          </div>

          <!-- HOTELS -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🏨</div><div class="card-title">Where to stay</div></div>
            ${city.hotels && city.hotels.length > 0 ? city.hotels.map(h => `
              <div class="list-item">
                <div class="item-info">
                  <div class="item-name">${h.name}</div>
                  <div class="item-sub">${getPrice(h.type)} &nbsp;·&nbsp; ${getRating(h.type)}</div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
                  ${getHotelBadge(h.type)}
                  <a href="${h.link}" target="_blank"><button class="btn btn-book">Book →</button></a>
                </div>
              </div>
            `).join('') : '<p style="color:var(--muted);font-size:14px;">No hotel data available.</p>'}
          </div>

          <!-- FOOD -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🍜</div><div class="card-title">What to eat</div></div>
            ${city.food && city.food.street_food && city.food.street_food.length > 0 ? `
              <p style="font-size:12px;font-weight:500;letter-spacing:0.07em;text-transform:uppercase;color:var(--muted);margin-bottom:12px;">Street food</p>
              <div class="food-tags">${city.food.street_food.map(f => `<span class="food-tag">🍴 ${f}</span>`).join('')}</div>
            ` : ''}
            ${city.food && city.food.restaurants && city.food.restaurants.length > 0 ? `
              <p style="font-size:12px;font-weight:500;letter-spacing:0.07em;text-transform:uppercase;color:var(--muted);margin:16px 0 10px;">Restaurants</p>
              ${city.food.restaurants.map(r => `
                <div class="list-item">
                  <div class="item-info"><div class="item-name">${r.name}</div></div>
                  <a href="${r.link}" target="_blank"><button class="btn btn-reserve">Reserve</button></a>
                </div>
              `).join('')}
            ` : ''}
          </div>

          <!-- TRANSPORT -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🚕</div><div class="card-title">Getting around</div></div>
            <div class="transport-row">
              ${city.transport && city.transport.cabs ? city.transport.cabs.map(c => `
                <a href="${c.link}" target="_blank"><button class="btn btn-cab">🚕 ${c.name}</button></a>
              `).join('') : '<p style="color:var(--muted);font-size:14px;">No transport data.</p>'}
            </div>
          </div>

          <!-- BUDGET CHART -->
          <div class="card">
            <div class="card-header"><div class="card-icon">📊</div><div class="card-title">Budget breakdown</div></div>
            <div class="chart-container"><canvas id="chart-${index}"></canvas></div>
            <div class="budget-breakdown" id="budget-breakdown-${index}"></div>
          </div>

          <!-- PACKING LIST -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🧳</div><div class="card-title">Packing list</div></div>
            ${renderPackingList(trip_type, parseInt(days), city.city)}
          </div>

          <!-- TRAVEL TIPS -->
          <div class="card">
            <div class="card-header"><div class="card-icon">💡</div><div class="card-title">Travel tips</div></div>
            <div class="tips-list">
              ${tips.map(tip => `<div class="tip-item"><span class="tip-icon">${tip.icon}</span><span>${tip.text}</span></div>`).join('')}
            </div>
          </div>

          <!-- AI TIPS (from AI response) -->
          ${city.tips && city.tips.length > 0 ? `
          <div class="card">
            <div class="card-header"><div class="card-icon">🤖</div><div class="card-title">AI insights for ${city.city}</div></div>
            <div class="tips-list">
              ${city.tips.map(tip => `<div class="tip-item"><span class="tip-icon">✦</span><span>${tip}</span></div>`).join('')}
            </div>
          </div>` : ''}

          <!-- SMART SUGGESTION -->
          <div class="card card-full">
            <div class="card-header"><div class="card-icon">💡</div><div class="card-title">Smart suggestions</div></div>
            <div class="suggestion-card">${getSuggestion(budget, trip_type)}</div>
          </div>

          <!-- SIMILAR DESTINATIONS -->
          <div class="card card-full">
            <div class="card-header"><div class="card-icon">🗺️</div><div class="card-title">You might also like</div></div>
            <div class="similar-dests">
              ${similar.map(dest => {
                const parts = dest.split(' ');
                const emoji = parts[parts.length - 1];
                const name  = parts.slice(0, -1).join(' ');
                return `<button class="similar-dest-btn" onclick="goBack();setTimeout(()=>fillDestination('${name}'),200)">${emoji} ${name}</button>`;
              }).join('')}
            </div>
          </div>

        </div>
      </div>`;
    }

    document.getElementById('tabs').innerHTML   = tabsHTML;
    document.getElementById('result').innerHTML = contentHTML;

    // Render charts + weather
    data.forEach((city, index) => {
      const split = getBudgetSplit(budget, trip_type);
      const keys  = Object.keys(split);
      const vals  = Object.values(split);
      const total = vals.reduce((a, b) => a + b, 0);

      const canvas = document.getElementById(`chart-${index}`);
      if (canvas) {
        new Chart(canvas, {
          type: 'doughnut',
          data: {
            labels: keys,
            datasets: [{ data: vals, backgroundColor: CHART_COLORS, borderWidth: 0, hoverOffset: 6 }]
          },
          options: {
            cutout: '65%',
            plugins: {
              legend: { display: false },
              tooltip: { callbacks: { label: (ctx) => ` ₹${ctx.raw.toLocaleString('en-IN')}` } }
            }
          }
        });
      }

      const breakdownEl = document.getElementById(`budget-breakdown-${index}`);
      if (breakdownEl) {
        breakdownEl.innerHTML = keys.map((k, i) => {
          const pct = Math.round((vals[i] / total) * 100);
          return `<div class="budget-item">
            <span class="budget-dot" style="background:${CHART_COLORS[i]}"></span>
            <span class="budget-label">${k}</span>
            <span class="budget-pct">${pct}%</span>
          </div>`;
        }).join('');
      }

      fetchWeather(city.city).then(weather => {
        const el = document.getElementById(`weather-widget-${index}`);
        if (!el) return;
        if (!weather) { el.innerHTML = '<span class="weather-loading">Weather unavailable.</span>'; return; }
        el.innerHTML = `
          <div class="weather-main">
            <span class="weather-icon">${weather.icon}</span>
            <div>
              <div class="weather-temp">${weather.tempC}°C</div>
              <div class="weather-desc">${weather.desc}</div>
            </div>
          </div>
          <div class="weather-details">
            <div class="weather-detail">
              <span>💧</span><span>${weather.humidity}%</span>
              <span style="font-size:10px;color:var(--muted-2)">Humidity</span>
            </div>
            <div class="weather-detail">
              <span>🌡️</span><span>${weather.feelsLike}°C</span>
              <span style="font-size:10px;color:var(--muted-2)">Feels like</span>
            </div>
            <div class="weather-detail">
              <span>💨</span><span>${weather.windKmph} km/h</span>
              <span style="font-size:10px;color:var(--muted-2)">Wind</span>
            </div>
          </div>
        `;
      });
    });

    showToast('✅ Your ' + destination + ' itinerary is ready!', 'success');

  } catch (err) {
    console.error('Error generating plan:', err);
    showToast('❌ Something went wrong. Please try again.', 'error');
    document.getElementById('result').innerHTML = '';
    goBack();
  } finally {
    document.querySelector('.generate-btn').style.display = 'flex';
    document.getElementById('loading-state').classList.add('hidden');
    stopLoadingMessages();
  }
}