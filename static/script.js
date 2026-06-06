/* ═══════════════════════════════════════
   VOYAGER AI — script.js v4 (FIXED)
   Fixes:
   • Weather uses /api/weather proxy (no CORS)
   • Destination autocomplete via /api/cities
   • Generate button properly re-enables on error
   • All edge cases handled
   ═══════════════════════════════════════ */

// ─── State ─────────────────────────────
let currentPlanData    = [];
let currentDestination = '';
let currentDays        = 0;
let currentBudget      = 0;
let currentTripType    = 'Solo';

// ─── Scroll progress ───────────────────
window.addEventListener('scroll', () => {
  const el = document.getElementById('scrollProgress');
  if (!el) return;
  const pct = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
  el.style.width = Math.min(pct, 100) + '%';
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
  const isDark = document.body.classList.contains('dark');
  if (icon) icon.setAttribute('data-lucide', isDark ? 'sun' : 'moon');
  localStorage.setItem('voyager_dark', isDark);
  if (window.lucide) lucide.createIcons();
}

if (localStorage.getItem('voyager_dark') === 'true') {
  document.body.classList.add('dark');
  const icon = document.querySelector('.toggle-icon');
  if (icon) icon.setAttribute('data-lucide', 'sun');
}

// ─── Slide navigation ──────────────────
function goToOutput() {
  document.getElementById('inputSlide').classList.remove('active');
  document.getElementById('outputSlide').classList.add('active');
  ['printBtn','pdfBtn'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'flex';
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goBack() {
  document.getElementById('outputSlide').classList.remove('active');
  document.getElementById('inputSlide').classList.add('active');
  ['printBtn','pdfBtn'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ─── City tab switching ─────────────────
function switchCity(index) {
  document.querySelectorAll('.city-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('city-' + index)?.classList.add('active');
  document.getElementById('tab-' + index)?.classList.add('active');
}

// ─── Destination autocomplete ───────────
let acTimeout = null;
async function autocompleteCity(val) {
  const dd = document.getElementById('ac-dropdown');
  if (!dd) return;
  clearTimeout(acTimeout);
  if (!val || val.length < 2) { dd.style.display = 'none'; return; }

  // Autocomplete on the last typed city (after last comma)
  const parts = val.split(',');
  const query = parts[parts.length - 1].trim();
  if (!query || query.length < 2) { dd.style.display = 'none'; return; }

  acTimeout = setTimeout(async () => {
    try {
      const res  = await fetch('/api/cities?q=' + encodeURIComponent(query));
      const list = await res.json();
      if (!list.length) { dd.style.display = 'none'; return; }

      dd.innerHTML = list.map(city => `
        <div onclick="selectCity('${city}')"
          style="padding:10px 16px;font-size:14px;font-weight:600;cursor:pointer;
            border-bottom:1px solid #ECE7DC;transition:background 0.15s;color:#14213D;"
          onmouseover="this.style.background='#F7F5F0'"
          onmouseout="this.style.background='#fff'">
          📍 ${city}
        </div>
      `).join('');
      dd.style.display = 'block';
    } catch { dd.style.display = 'none'; }
  }, 250);
}

function selectCity(city) {
  const el = document.getElementById('destination');
  const dd = document.getElementById('ac-dropdown');
  if (!el) return;
  const parts = el.value.split(',');
  parts[parts.length - 1] = ' ' + city;
  el.value = parts.join(',').replace(/^,\s*/, '');
  if (dd) dd.style.display = 'none';
  el.focus();
}

function hideAC() {
  const dd = document.getElementById('ac-dropdown');
  if (dd) dd.style.display = 'none';
}

// ─── Quick destination fill ─────────────
function fillDestination(dest) {
  const el = document.getElementById('destination');
  if (el) { el.value = dest; el.focus(); }
}

// ─── Budget slider ──────────────────────
function updateBudgetDisplay(val) {
  const num  = parseInt(val);
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
  try {
    localStorage.setItem('voyager_last_trip',
      JSON.stringify({ destination, days, budget, trip_type, ts: Date.now() }));
  } catch(e) {}
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
  } catch(e) {}
}

function resumeLastTrip() {
  try {
    const trip = JSON.parse(localStorage.getItem('voyager_last_trip'));
    if (!trip) return;
    const destEl = document.getElementById('destination');
    const daysEl = document.getElementById('days');
    const rangeEl = document.getElementById('budgetRange');
    const radioEl = document.querySelector(`input[name="trip_type"][value="${trip.trip_type}"]`);
    if (destEl)  destEl.value  = trip.destination;
    if (daysEl)  daysEl.value  = trip.days;
    if (rangeEl) rangeEl.value = trip.budget;
    updateBudgetDisplay(trip.budget);
    if (radioEl) radioEl.checked = true;
    showToast('🕐 Last trip restored!', 'success');
  } catch(e) {}
}

// ─── Budget helpers ─────────────────────
function getBudgetSplit(budget, trip_type) {
  const splits = {
    Honeymoon: { Hotels:0.50, Food:0.20, Transport:0.15, Activities:0.15 },
    Friends:   { Hotels:0.35, Food:0.25, Transport:0.15, Activities:0.25 },
    Family:    { Hotels:0.40, Food:0.20, Transport:0.25, Activities:0.15 },
    Solo:      { Hotels:0.40, Food:0.20, Transport:0.20, Activities:0.20 }
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
  return `<span style="background:${bg};color:${color};font-size:11px;padding:3px 8px;border-radius:10px;font-weight:700;">${label}</span>`;
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

// ─── Weather — uses server proxy to avoid CORS ──
async function fetchWeather(city) {
  try {
    const res  = await fetch('/api/weather?city=' + encodeURIComponent(city));
    if (!res.ok) return null;
    const data = await res.json();
    if (data.error) return null;
    return { ...data, icon: getWeatherIcon(data.desc) };
  } catch { return null; }
}

function getWeatherIcon(desc) {
  if (!desc) return '🌤️';
  const d = desc.toLowerCase();
  if (d.includes('sun') || d.includes('clear'))      return '☀️';
  if (d.includes('cloud') || d.includes('overcast')) return '⛅';
  if (d.includes('rain') || d.includes('drizzle'))   return '🌧️';
  if (d.includes('thunder') || d.includes('storm'))  return '⛈️';
  if (d.includes('snow'))                            return '❄️';
  if (d.includes('fog') || d.includes('mist'))       return '🌫️';
  if (d.includes('wind'))                            return '💨';
  return '🌤️';
}

// ─── Packing list ───────────────────────
function getPackingList(trip_type, days, destination) {
  const dest = (destination || '').toLowerCase();
  const isBeach    = ['goa','maldives','kerala','andaman','puri','pondicherry','varkala','tarkarli'].some(d => dest.includes(d));
  const isMountain = ['manali','shimla','leh','ladakh','kashmir','ooty','munnar','spiti','kasol'].some(d => dest.includes(d));

  const base = {
    '👗 Clothing':   ['T-shirts','Comfortable trousers','Undergarments','Socks','Sleepwear'],
    '🪥 Toiletries': ['Toothbrush & toothpaste','Shampoo','Sunscreen SPF 50+','Deodorant','Hand sanitizer'],
    '📱 Tech & Docs':['Phone + charger','Power bank','Travel adapter','ID / Passport','Travel insurance copy'],
    '💊 Health':     ['Personal medication','Pain relievers','Band-aids','Antacids','Mosquito repellent']
  };

  if (isBeach)    base['🏖️ Beach Essentials'] = ['Swimwear','Beach towel','Flip flops','Sunglasses','Waterproof bag'];
  if (isMountain) base['🏔️ Mountain Gear']    = ['Warm jacket','Thermal innerwear','Trekking shoes','Woollen cap & gloves','Rain poncho'];
  if (trip_type === 'Honeymoon') base['💑 Honeymoon'] = ['Formal outfit','Perfume / cologne','Camera','Candles or gifts','Couple accessories'];
  if (trip_type === 'Family')    base['👶 Family']    = ['Kids snacks','Baby wipes','First aid kit','Kids entertainment','Emergency contact list'];
  if (days >= 7) base['👗 Clothing'].push('Extra outfits','Laundry bag','Detergent strips');

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
          <div class="packing-item" onclick="togglePackItem(this)" role="checkbox" aria-checked="false" tabindex="0">
            <span class="packing-check" aria-hidden="true">○</span>
            <span>${item}</span>
          </div>
        `).join('')}
      </div>
    </div>`;
  }
  return html + '</div>';
}

function togglePackItem(el) {
  const checked = !el.classList.contains('checked');
  el.classList.toggle('checked', checked);
  el.setAttribute('aria-checked', checked);
  const check = el.querySelector('.packing-check');
  if (check) check.textContent = checked ? '✓' : '○';
}

// ─── Similar destinations ───────────────
function getSimilarDestinations(destination) {
  const map = {
    'goa':      ['Pondicherry 🌊','Varkala 🏖️','Tarkarli 🤿'],
    'manali':   ['Spiti Valley 🏔️','Leh-Ladakh ❄️','Kasol 🌿'],
    'jaipur':   ['Jodhpur 🏰','Udaipur 🌅','Pushkar 🐪'],
    'kerala':   ['Coorg 🌿','Alleppey 🛶','Munnar ☕'],
    'varanasi': ['Rishikesh 🕉️','Haridwar 🙏','Prayagraj 🌊'],
    'mumbai':   ['Pune 🏙️','Nashik 🍇','Alibaug 🌊'],
    'delhi':    ['Agra 🕌','Mathura 🙏','Jaipur 🏰'],
    'shimla':   ['Manali 🏔️','Dalhousie 🌿','Dharamshala 🙏'],
  };
  const destLower = (destination || '').toLowerCase();
  for (const [key, vals] of Object.entries(map)) {
    if (destLower.includes(key)) return vals;
  }
  return ['Goa 🏖️','Jaipur 🏰','Manali 🏔️','Kerala 🌴'];
}

// ─── Travel tips ───────────────────────
function getTravelTips(destination, trip_type) {
  const tips = [
    { icon: '📱', text: 'Download offline maps (Google Maps / Maps.me) before you leave.' },
    { icon: '💳', text: 'Carry some cash — smaller towns may not accept cards everywhere.' },
    { icon: '🌐', text: 'Buy a local SIM or activate roaming before your trip.' },
    { icon: '🔒', text: 'Keep a digital copy of all ID documents saved in your email.' },
    { icon: '🧴', text: 'Always carry sunscreen, even on cloudy days.' },
  ];
  if (trip_type === 'Solo')   tips.push({ icon: '📍', text: 'Share your live location with a trusted contact back home.' });
  if (trip_type === 'Family') tips.push({ icon: '🏥', text: 'Note the nearest hospital or clinic to your accommodation.' });
  if (trip_type === 'Honeymoon') tips.push({ icon: '🌹', text: 'Book dinner reservations and activities in advance for special dates.' });
  const d = (destination || '').toLowerCase();
  if (d.includes('goa') || d.includes('beach')) tips.push({ icon: '🌊', text: 'Swim only at patrolled beaches and watch for red flag warnings.' });
  if (d.includes('manali') || d.includes('ladakh') || d.includes('leh')) tips.push({ icon: '🏔️', text: 'Acclimatise for 1–2 days at high altitude before strenuous activities.' });
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
    if (el) el.textContent = LOADING_MSGS[i];
  }, 1800);
}

function stopLoadingMessages() {
  if (loadingInterval) { clearInterval(loadingInterval); loadingInterval = null; }
}

// ─── Chart colors ────────────────────────
const CHART_COLORS = ['#B96F34','#0F766E','#2563EB','#D9564A'];

// ─── PDF download ───────────────────────
function downloadPDF() {
  const el = document.getElementById('result');
  if (!el || !currentPlanData.length) {
    showToast('⚠️ Generate a plan first.', 'error'); return;
  }
  showToast('📄 Preparing PDF…', '');
  const opt = {
    margin: [10,10,10,10],
    filename: `voyager-${currentDestination.replace(/[^a-z0-9]/gi,'-').toLowerCase()}.pdf`,
    image:    { type: 'jpeg', quality: 0.95 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF:    { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['avoid-all','css','legacy'] }
  };
  html2pdf().set(opt).from(el).save().then(() => {
    showToast('✅ Itinerary downloaded!', 'success');
  }).catch(() => {
    showToast('❌ PDF generation failed.', 'error');
  });
}

function printItinerary() { window.print(); }

// ─── Modals ─────────────────────────────
function openModal(id)  {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// Close modals on Escape key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    ['saveModal','emailModal'].forEach(id => closeModal(id));
  }
});

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
  const btn = document.querySelector('#saveModal .modal-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
  try {
    const res = await fetch('/save-trip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        destination: currentDestination, days: currentDays,
        budget: currentBudget, trip_type: currentTripType, plan: currentPlanData
      })
    });
    const data = await res.json();
    const el   = document.getElementById('saveResult');
    if (el) {
      el.style.display = 'block';
      el.innerHTML = `
        ✅ Trip saved!<br>
        <strong>Share link:</strong><br>
        <a href="${data.share_url}" target="_blank" style="color:var(--amber);word-break:break-all">${data.share_url}</a>
        <br><br>
        <button onclick="navigator.clipboard.writeText('${data.share_url}').then(()=>showToast('📋 Link copied!','success'))"
          style="background:var(--amber);color:#fff;border:none;border-radius:8px;padding:7px 14px;cursor:pointer;font-size:13px;font-weight:700;">
          📋 Copy Link
        </button>
      `;
    }
  } catch(e) {
    showToast('❌ Could not save. Please try again.', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Save and get link'; }
  }
}

// ─── Email itinerary ─────────────────────
async function emailItinerary() {
  const emailEl = document.getElementById('emailInput');
  const email   = emailEl ? emailEl.value.trim() : '';
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showToast('⚠️ Enter a valid email address.', 'error'); return;
  }

  const btn = document.querySelector('#emailModal .modal-btn');
  const el  = document.getElementById('emailResult');
  if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
  if (el)  { el.style.display = 'block'; el.innerHTML = '⏳ Sending…'; }

  try {
    const res  = await fetch('/email-itinerary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, destination: currentDestination, plan: currentPlanData })
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
  } catch(e) {
    if (el) el.innerHTML = '❌ Something went wrong.';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Send itinerary'; }
  }
}

// ─── Generate ──────────────────────────
function setGenerateLoading(loading) {
  const btn  = document.getElementById('generateBtn');
  const load = document.getElementById('loading-state');
  if (btn)  btn.style.display  = loading ? 'none' : 'flex';
  if (load) load.classList.toggle('hidden', !loading);
}

async function generatePlan() {
  const destination = (document.getElementById('destination')?.value || '').trim();
  const days        = (document.getElementById('days')?.value || '').trim();
  const budget      = parseInt(document.getElementById('budget')?.value || '0');
  const tripTypeEl  = document.querySelector('input[name="trip_type"]:checked');
  const trip_type   = tripTypeEl ? tripTypeEl.value : 'Solo';

  // Validation
  if (!destination) { showToast('⚠️ Please enter a destination.', 'error'); return; }
  if (!days || parseInt(days) < 1) { showToast('⚠️ Please enter a valid number of days.', 'error'); return; }
  if (!budget || budget < 500)     { showToast('⚠️ Please set a budget.', 'error'); return; }

  // Cache state
  currentDestination = destination;
  currentDays        = parseInt(days);
  currentBudget      = budget;
  currentTripType    = trip_type;

  setGenerateLoading(true);
  startLoadingMessages();
  saveLastTrip(destination, days, budget, trip_type);

  // Update output header
  const destLabel = document.getElementById('output-dest-label');
  const metaLabel = document.getElementById('output-meta');
  if (destLabel) destLabel.textContent = '📍 ' + destination;
  if (metaLabel) metaLabel.textContent = `${days} days · ₹${Number(budget).toLocaleString('en-IN')} · ${trip_type}`;

  document.getElementById('tabs').innerHTML   = '';
  document.getElementById('result').innerHTML = buildSkeletonHTML();
  goToOutput();

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ destination, days, budget, trip_type })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || 'Server error');
    }

    const data = await res.json();
    if (!Array.isArray(data) || !data.length) throw new Error('No data returned');
    currentPlanData = data;

    let tabsHTML = '', contentHTML = '';

    for (let index = 0; index < data.length; index++) {
      const city      = data[index];
      const cityName  = city.city || destination;
      const daysList  = (city.plan || '').split('\n').filter(l => l.trim());
      const similar   = getSimilarDestinations(cityName);
      const tips      = getTravelTips(cityName, trip_type);
      const weatherId = `weather-widget-${index}`;

      tabsHTML += `<button id="tab-${index}" class="tab-btn ${index===0?'active':''}" onclick="switchCity(${index})" role="tab" aria-selected="${index===0}">📍 ${cityName}</button>`;

      contentHTML += `
      <div id="city-${index}" class="city-section ${index===0?'active':''}" role="tabpanel">

        <div class="city-stats">
          <div class="stat-card">
            <div class="stat-card-val">${daysList.length}</div>
            <div class="stat-card-label">Days Planned</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-val">${city.places ? city.places.length : 0}</div>
            <div class="stat-card-label">Places to Visit</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-val">${city.hotels ? city.hotels.length : 0}</div>
            <div class="stat-card-label">Hotel Options</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-val">₹${Number(budget).toLocaleString('en-IN')}</div>
            <div class="stat-card-label">Total Budget</div>
          </div>
        </div>

        <div class="results-grid">

          <!-- ITINERARY -->
          <div class="card card-full">
            <div class="card-header"><div class="card-icon">📅</div><div class="card-title">Day-by-day Itinerary</div></div>
            ${daysList.length ? daysList.map((line, di) => {
              const clean = line.replace(/^Day \d+:\s*/i, '').replace(/^🗓\s*/, '');
              return `<div class="day-block"><span class="day-num">Day ${di+1}</span><span>${clean}</span></div>`;
            }).join('') : '<p style="color:var(--muted);font-size:14px;">No itinerary data.</p>'}
          </div>

          <!-- WEATHER -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🌤️</div><div class="card-title">Live Weather in ${cityName}</div></div>
            <div id="${weatherId}"><span style="color:var(--muted);font-size:13px;">Loading weather…</span></div>
          </div>

          <!-- PLACES -->
          <div class="card">
            <div class="card-header"><div class="card-icon">📌</div><div class="card-title">Places to Visit</div></div>
            ${city.places && city.places.length ? city.places.map(p => `
              <div class="list-item">
                <div class="item-info"><div class="item-name">${p.name}</div></div>
                <a href="https://www.google.com/maps/search/${encodeURIComponent(p.name+' '+cityName)}" target="_blank" rel="noopener">
                  <button class="btn btn-map">View map</button>
                </a>
              </div>
            `).join('') : '<p style="color:var(--muted);font-size:14px;">No specific places listed.</p>'}
          </div>

          <!-- HOTELS -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🏨</div><div class="card-title">Where to Stay</div></div>
            ${city.hotels && city.hotels.length ? city.hotels.map(h => `
              <div class="list-item">
                <div class="item-info">
                  <div class="item-name">${h.name}</div>
                  <div class="item-sub">${getPrice(h.type)} &nbsp;·&nbsp; ${getRating(h.type)}</div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
                  ${getHotelBadge(h.type)}
                  <a href="${h.link}" target="_blank" rel="noopener"><button class="btn btn-book">Book →</button></a>
                </div>
              </div>
            `).join('') : '<p style="color:var(--muted);font-size:14px;">No hotel data available.</p>'}
          </div>

          <!-- FOOD -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🍜</div><div class="card-title">What to Eat</div></div>
            ${city.food?.street_food?.length ? `
              <p style="font-size:11px;font-weight:800;letter-spacing:0.07em;text-transform:uppercase;color:var(--muted);margin-bottom:12px;">Street Food</p>
              <div class="food-tags">${city.food.street_food.map(f => `<span class="food-tag">🍴 ${f}</span>`).join('')}</div>
            ` : ''}
            ${city.food?.restaurants?.length ? `
              <p style="font-size:11px;font-weight:800;letter-spacing:0.07em;text-transform:uppercase;color:var(--muted);margin:16px 0 10px;">Restaurants</p>
              ${city.food.restaurants.map(r => `
                <div class="list-item">
                  <div class="item-info"><div class="item-name">${r.name}</div></div>
                  <a href="${r.link}" target="_blank" rel="noopener"><button class="btn btn-reserve">Reserve</button></a>
                </div>
              `).join('')}
            ` : (!city.food?.street_food?.length ? '<p style="color:var(--muted);font-size:14px;">No food data available.</p>' : '')}
          </div>

          <!-- TRANSPORT -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🚕</div><div class="card-title">Getting Around</div></div>
            <div class="transport-row">
              ${city.transport?.cabs?.length ? city.transport.cabs.map(c => `
                <a href="${c.link}" target="_blank" rel="noopener"><button class="btn btn-cab">🚕 ${c.name}</button></a>
              `).join('') : '<p style="color:var(--muted);font-size:14px;">No transport data.</p>'}
            </div>
          </div>

          <!-- BUDGET CHART -->
          <div class="card">
            <div class="card-header"><div class="card-icon">📊</div><div class="card-title">Budget Breakdown</div></div>
            <div class="chart-container"><canvas id="chart-${index}" aria-label="Budget breakdown chart"></canvas></div>
            <div class="budget-breakdown" id="budget-breakdown-${index}"></div>
          </div>

          <!-- PACKING LIST -->
          <div class="card">
            <div class="card-header"><div class="card-icon">🧳</div><div class="card-title">Packing List</div></div>
            ${renderPackingList(trip_type, parseInt(days), cityName)}
          </div>

          <!-- TRAVEL TIPS -->
          <div class="card">
            <div class="card-header"><div class="card-icon">💡</div><div class="card-title">Travel Tips</div></div>
            <div class="tips-list">
              ${tips.map(tip => `<div class="tip-item"><span class="tip-icon">${tip.icon}</span><span>${tip.text}</span></div>`).join('')}
            </div>
          </div>

          <!-- AI TIPS -->
          ${city.tips?.length ? `
          <div class="card">
            <div class="card-header"><div class="card-icon">🤖</div><div class="card-title">AI Insights for ${cityName}</div></div>
            <div class="tips-list">
              ${city.tips.map(tip => `<div class="tip-item"><span class="tip-icon">✦</span><span>${tip}</span></div>`).join('')}
            </div>
          </div>` : ''}

          <!-- SMART SUGGESTION -->
          <div class="card card-full">
            <div class="card-header"><div class="card-icon">💡</div><div class="card-title">Smart Suggestions</div></div>
            <div class="suggestion-card">${getSuggestion(budget, trip_type)}</div>
          </div>

          <!-- SIMILAR DESTINATIONS -->
          <div class="card card-full">
            <div class="card-header"><div class="card-icon">🗺️</div><div class="card-title">You Might Also Like</div></div>
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
    if (window.lucide) lucide.createIcons();

    // Render charts + weather
    data.forEach((city, index) => {
      // Budget chart
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

      // Weather (via proxy — no CORS)
      const cityName = city.city || destination;
      fetchWeather(cityName).then(weather => {
        const el = document.getElementById(`weather-widget-${index}`);
        if (!el) return;
        if (!weather) {
          el.innerHTML = '<span style="color:var(--muted);font-size:13px;">Weather unavailable.</span>';
          return;
        }
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
              <span style="font-size:10px;color:var(--muted)">Humidity</span>
            </div>
            <div class="weather-detail">
              <span>🌡️</span><span>${weather.feelsLike}°C</span>
              <span style="font-size:10px;color:var(--muted)">Feels like</span>
            </div>
            <div class="weather-detail">
              <span>💨</span><span>${weather.windKmph} km/h</span>
              <span style="font-size:10px;color:var(--muted)">Wind</span>
            </div>
          </div>
        `;
      });
    });

    showToast('✅ Your ' + destination + ' itinerary is ready!', 'success');

  } catch(err) {
    console.error('Generate error:', err);
    showToast('❌ ' + (err.message || 'Something went wrong. Please try again.'), 'error');
    document.getElementById('result').innerHTML = `
      <div style="text-align:center;padding:64px 24px;">
        <div style="font-size:48px;margin-bottom:16px;">😕</div>
        <h3 style="font-family:var(--font-display);font-size:22px;margin-bottom:8px;">Could not generate itinerary</h3>
        <p style="color:var(--muted);font-size:14px;margin-bottom:24px;">${err.message || 'Please check your connection and try again.'}</p>
        <button onclick="goBack()" style="padding:12px 24px;background:var(--text);color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;">← Try Again</button>
      </div>
    `;
  } finally {
    setGenerateLoading(false);
    stopLoadingMessages();
  }
}