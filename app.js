/* Web3 Tools — read-only dashboard. No build step, no keys, no wallet connection.
   Data: data/funding.json + data/whales.json (verified snapshots, 24 Nov 2026).
   Live checks (optional, best-effort, no key): CoinGecko prices, mempool.space
   (BTC balances/fees), ethereum.publicnode.com (ETH balance/gas),
   api.mainnet-beta.solana.com (SOL balance). Any live failure falls back to
   the snapshot and is labelled as such. */

'use strict';

const SNAPSHOT_DATE = '24 Nov 2026';
const USER_WHALES_KEY = 'web3-tools-user-whales-v1';
const FETCH_TIMEOUT_MS = 8000;

const state = {
  funding: null, // { snapshot_date, rounds: [], sources: [] }
  whales: null,  // { snapshot_date, snapshot_prices_usd, wallets: [], sources: [] }
  userWhales: [],
  prices: null,  // { bitcoin, ethereum, solana } in USD, live
  pricesLive: false,
  whaleChain: 'all',
  fundingSearch: '',
  fundingRound: 'all',
  fundingSort: 'amount-desc',
  liveBalances: {}, // address -> { value, currency, live: true }
};

/* ---------- helpers ---------- */

function $(sel) { return document.querySelector(sel); }
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = text;
  return n;
}

function fmtMoneyShort(n) {
  if (n === null || n === undefined) return 'Undisclosed';
  if (n >= 1e9) return '$' + (n / 1e9).toFixed(n % 1e9 === 0 ? 0 : 2).replace(/\.00$/, '') + 'B';
  if (n >= 1e6) return '$' + (n / 1e6).toFixed(n % 1e6 === 0 ? 0 : 1).replace(/\.0$/, '') + 'M';
  if (n >= 1e3) return '$' + (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
  return '$' + n;
}

function fmtMoneyFull(n) {
  if (n === null || n === undefined) return '—';
  return '$' + Math.round(n).toLocaleString('en-US');
}

function fmtNum(n, digits) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: digits === undefined ? 3 : digits });
}

function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso + 'T00:00:00Z');
  if (isNaN(d)) return iso;
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

function shortAddr(addr) {
  if (!addr) return '';
  if (addr.length <= 20) return addr;
  return addr.slice(0, 10) + '…' + addr.slice(-8);
}

function explorerUrl(chain, addr) {
  if (chain === 'btc') return 'https://mempool.space/address/' + addr;
  if (chain === 'sol') return 'https://solscan.io/account/' + addr;
  return 'https://etherscan.io/address/' + addr;
}

function validateAddress(chain, addr) {
  if (chain === 'evm') return /^0x[0-9a-fA-F]{40}$/.test(addr);
  if (chain === 'btc') {
    return /^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$/.test(addr) ||
      /^bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71}$/.test(addr);
  }
  if (chain === 'sol') return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(addr);
  return false;
}

async function fetchJson(url, options) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, Object.assign({ signal: ctrl.signal }, options || {}));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.json();
  } finally {
    clearTimeout(t);
  }
}

async function rpcCall(url, method, params) {
  const data = await fetchJson(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: method, params: params }),
  });
  if (data.error) throw new Error(data.error.message || 'RPC error');
  return data.result;
}

/* ---------- data loading ---------- */

async function loadData() {
  const [funding, whales] = await Promise.all([
    fetchJson('data/funding.json'),
    fetchJson('data/whales.json'),
  ]);
  state.funding = funding;
  state.whales = whales;
  try {
    state.userWhales = JSON.parse(localStorage.getItem(USER_WHALES_KEY) || '[]');
  } catch (e) {
    state.userWhales = [];
  }
}

/* ---------- tabs ---------- */

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      document.querySelectorAll('.tab-panel').forEach(function (p) { p.hidden = true; });
      $('#tab-' + btn.dataset.tab).hidden = false;
    });
  });
}

/* ---------- funding ---------- */

function fundingRounds() {
  let rows = (state.funding.rounds || []).slice();
  if (state.fundingSearch) {
    const q = state.fundingSearch.toLowerCase();
    rows = rows.filter(function (r) {
      return [r.project, r.lead_investor, r.category, r.round, (r.investors || []).join(' '), r.description || '']
        .join(' ').toLowerCase().includes(q);
    });
  }
  if (state.fundingRound !== 'all') {
    rows = rows.filter(function (r) { return r.round === state.fundingRound; });
  }
  rows.sort(function (a, b) {
    if (state.fundingSort === 'amount-desc') return (b.amount_usd || 0) - (a.amount_usd || 0);
    if (state.fundingSort === 'date-desc') return String(b.date).localeCompare(String(a.date));
    return String(a.date).localeCompare(String(b.date));
  });
  return rows;
}

function renderFunding() {
  const rows = fundingRounds();
  const body = $('#fundingBody');
  body.innerHTML = '';
  rows.forEach(function (r) {
    const tr = document.createElement('tr');
    const tdP = el('td');
    const strong = el('strong', null, r.project);
    tdP.appendChild(strong);
    if (r.description) tdP.appendChild(el('span', 'sub', r.description));
    tr.appendChild(tdP);
    const tdD = el('td', null, fmtDate(r.date));
    if (r.date_note) tdD.appendChild(el('span', 'sub', '* ' + r.date_note));
    tr.appendChild(tdD);
    const tdR = el('td');
    tdR.appendChild(el('span', 'round-badge', r.round));
    tr.appendChild(tdR);
    tr.appendChild(el('td', 'amount', fmtMoneyShort(r.amount_usd)));
    tr.appendChild(el('td', null, r.category || '—'));
    const tdL = el('td', null, r.lead_investor || '—');
    if (r.investors && r.investors.length > 1) {
      tdL.appendChild(el('span', 'sub', '+ ' + (r.investors.length - 1) + ' more: ' + r.investors.slice(1).join(', ')));
    }
    tr.appendChild(tdL);
    const tdS = el('td', null, r.source || '—');
    tr.appendChild(tdS);
    body.appendChild(tr);
  });
  $('#fundingEmpty').hidden = rows.length > 0;
  const total = (state.funding.rounds || []).reduce(function (s, r) { return s + (r.amount_usd || 0); }, 0);
  $('#statFundingTotal').textContent = fmtMoneyShort(total);
  $('#statRounds').textContent = String(state.funding.rounds.length);
  $('#fundingSources').innerHTML = '';
  const note = el('span', null, 'Snapshot ' + (state.funding.snapshot_date || SNAPSHOT_DATE) + '. ' +
    (state.funding.snapshot_note || '') + ' Sources: ');
  $('#fundingSources').appendChild(note);
  (state.funding.sources || []).forEach(function (s, i) {
    if (i > 0) $('#fundingSources').appendChild(document.createTextNode(' · '));
    const a = el('a', null, s.name);
    a.href = s.url; a.target = '_blank'; a.rel = 'noopener';
    $('#fundingSources').appendChild(a);
  });
}

function initFundingFilters() {
  const rounds = Array.from(new Set((state.funding.rounds || []).map(function (r) { return r.round; }))).sort();
  const sel = $('#fundingRoundFilter');
  rounds.forEach(function (rt) {
    const opt = el('option', null, rt);
    opt.value = rt;
    sel.appendChild(opt);
  });
  $('#fundingSearch').addEventListener('input', function (e) {
    state.fundingSearch = e.target.value.trim();
    renderFunding();
  });
  sel.addEventListener('change', function (e) {
    state.fundingRound = e.target.value;
    renderFunding();
  });
  $('#fundingSort').addEventListener('change', function (e) {
    state.fundingSort = e.target.value;
    renderFunding();
  });
}

/* ---------- whales ---------- */

function allWhales() {
  return (state.whales.wallets || []).concat(state.userWhales.map(function (w) {
    return Object.assign({}, w, { userAdded: true });
  }));
}

function chainLabel(chain) {
  return chain === 'btc' ? 'Bitcoin' : chain === 'sol' ? 'Solana' : 'EVM';
}

function priceFor(currency) {
  if (state.prices) {
    if (currency === 'BTC') return state.prices.bitcoin;
    if (currency === 'ETH' || currency === 'stETH') return state.prices.ethereum;
    if (currency === 'SOL') return state.prices.solana;
  }
  const snap = state.whales.snapshot_prices_usd || {};
  if (currency === 'BTC') return snap.BTC;
  if (currency === 'ETH' || currency === 'stETH') return snap.ETH;
  if (currency === 'SOL') return snap.SOL;
  return null;
}

function renderWhales() {
  const list = $('#whaleList');
  list.innerHTML = '';
  const rows = allWhales().filter(function (w) {
    return state.whaleChain === 'all' || w.chain === state.whaleChain;
  });
  rows.forEach(function (w) {
    const card = el('div', 'whale-card');
    const top = el('div', 'whale-top');
    const nameWrap = el('div');
    nameWrap.appendChild(el('h3', 'whale-name', w.label));
    nameWrap.appendChild(el('div', 'whale-type', (w.type || '') + ' · ' + chainLabel(w.chain)));
    top.appendChild(nameWrap);
    const badges = el('div', 'badges');
    badges.appendChild(el('span', 'badge badge-chain-' + w.chain, chainLabel(w.chain)));
    if (w.userAdded) badges.appendChild(el('span', 'badge badge-user', 'Yours'));
    top.appendChild(badges);
    card.appendChild(top);

    const addrBtn = el('button', 'whale-addr', shortAddr(w.address) + '  ⧉ copy');
    addrBtn.type = 'button';
    addrBtn.title = w.address + ' — click to copy';
    addrBtn.addEventListener('click', function () {
      const done = function () { addrBtn.textContent = 'Copied ✓'; setTimeout(function () { addrBtn.textContent = shortAddr(w.address) + '  ⧉ copy'; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(w.address).then(done, done);
      } else { done(); }
    });
    card.appendChild(addrBtn);

    const live = state.liveBalances[w.address];
    const balVal = live ? live.value : w.balance_native;
    const balUsd = (balVal !== null && balVal !== undefined && priceFor(w.currency))
      ? balVal * priceFor(w.currency) : (live ? null : w.balance_usd_snapshot);
    const balDiv = el('div', 'whale-balance');
    if (balVal === null || balVal === undefined) {
      balDiv.textContent = 'Balance unknown — try Refresh live';
      const src = el('span', 'src', 'Snapshot ' + (state.whales.snapshot_date || SNAPSHOT_DATE) + ': no balance on file');
      balDiv.appendChild(src);
    } else {
      balDiv.appendChild(document.createTextNode(fmtNum(balVal, 3) + ' ' + w.currency));
      const usd = el('span', 'usd', balUsd ? '≈ ' + fmtMoneyFull(balUsd) : '');
      balDiv.appendChild(usd);
      const src = el('span', live ? 'src live' : 'src',
        live ? '● Live balance (just refreshed)' : 'Snapshot ' + (state.whales.snapshot_date || SNAPSHOT_DATE));
      balDiv.appendChild(src);
    }
    card.appendChild(balDiv);

    if (w.note) card.appendChild(el('p', 'whale-note', w.note));
    if (w.last_activity) card.appendChild(el('div', 'whale-meta', 'Last activity: ' + w.last_activity));
    if (w.source) card.appendChild(el('div', 'whale-meta', 'Source: ' + w.source));

    const actions = el('div', 'whale-actions');
    const exp = el('a', 'btn btn-ghost', 'Open in explorer ↗');
    exp.href = explorerUrl(w.chain, w.address);
    exp.target = '_blank'; exp.rel = 'noopener';
    actions.appendChild(exp);
    const ref = el('button', 'btn btn-ghost', 'Refresh');
    ref.type = 'button';
    ref.addEventListener('click', function () { refreshOneWhale(w, ref); });
    actions.appendChild(ref);
    if (w.userAdded) {
      const del = el('button', 'btn btn-danger', 'Remove');
      del.type = 'button';
      del.addEventListener('click', function () {
        state.userWhales = state.userWhales.filter(function (u) { return u.address !== w.address; });
        saveUserWhales();
        renderWhales();
      });
      actions.appendChild(del);
    }
    card.appendChild(actions);
    list.appendChild(card);
  });
  $('#whaleEmpty').hidden = rows.length > 0;
  $('#statWhales').textContent = String(allWhales().length);
  const srcEl = $('#whaleSources');
  srcEl.innerHTML = '';
  srcEl.appendChild(el('span', null, 'Snapshot ' + (state.whales.snapshot_date || SNAPSHOT_DATE) + '. ' +
    (state.whales.snapshot_note || '') + ' Sources: '));
  (state.whales.sources || []).forEach(function (s, i) {
    if (i > 0) srcEl.appendChild(document.createTextNode(' · '));
    const a = el('a', null, s.name);
    a.href = s.url; a.target = '_blank'; a.rel = 'noopener';
    srcEl.appendChild(a);
  });
}

function saveUserWhales() {
  try { localStorage.setItem(USER_WHALES_KEY, JSON.stringify(state.userWhales)); } catch (e) { /* private mode */ }
}

function initWhaleFilters() {
  document.querySelectorAll('[data-chain]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('[data-chain]').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      state.whaleChain = btn.dataset.chain;
      renderWhales();
    });
  });
  $('#addWhaleBtn').addEventListener('click', function () {
    $('#whaleFormError').hidden = true;
    $('#modalOverlay').hidden = false;
    $('#fieldLabel').focus();
  });
  $('#cancelWhaleBtn').addEventListener('click', function () { $('#modalOverlay').hidden = true; });
  $('#modalOverlay').addEventListener('click', function (e) {
    if (e.target === e.currentTarget) e.currentTarget.hidden = true;
  });
  $('#whaleForm').addEventListener('submit', function (e) {
    e.preventDefault();
    const chain = $('#fieldChain').value;
    const label = $('#fieldLabel').value.trim();
    const address = $('#fieldAddress').value.trim();
    const err = $('#whaleFormError');
    if (!validateAddress(chain, address)) {
      err.textContent = 'That does not look like a valid ' + chainLabel(chain) + ' address. Check it and try again.';
      err.hidden = false;
      return;
    }
    if (allWhales().some(function (w) { return w.address.toLowerCase() === address.toLowerCase(); })) {
      err.textContent = 'This wallet is already on the watchlist.';
      err.hidden = false;
      return;
    }
    const currency = chain === 'btc' ? 'BTC' : chain === 'sol' ? 'SOL' : 'ETH';
    state.userWhales.push({
      chain: chain, label: label, address: address, currency: currency,
      balance_native: null, balance_usd_snapshot: null, type: 'Added by you',
      note: 'Added by you. Use Refresh to check its live balance.',
      last_activity: '', source: 'You',
    });
    saveUserWhales();
    $('#modalOverlay').hidden = true;
    e.target.reset();
    renderWhales();
  });
}

/* ---------- live data ---------- */

async function fetchBtcBalance(addr) {
  const data = await fetchJson('https://mempool.space/api/address/' + addr);
  const funded = data.chain_stats.funded_txo_sum;
  const spent = data.chain_stats.spent_txo_sum;
  return (funded - spent) / 1e8;
}

async function fetchEvmBalance(addr) {
  const hex = await rpcCall('https://ethereum.publicnode.com', 'eth_getBalance', [addr, 'latest']);
  return parseInt(hex, 16) / 1e18;
}

async function fetchSolBalance(addr) {
  const result = await rpcCall('https://api.mainnet-beta.solana.com', 'getBalance', [addr]);
  return result.value / 1e9;
}

async function refreshOneWhale(w, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Checking…'; }
  try {
    let value;
    if (w.chain === 'btc') value = await fetchBtcBalance(w.address);
    else if (w.chain === 'sol') value = await fetchSolBalance(w.address);
    else value = await fetchEvmBalance(w.address);
    state.liveBalances[w.address] = { value: value, currency: w.currency, live: true };
    renderWhales();
    setLiveStatus('whaleLiveStatus', true, 'Balances: live where refreshed, snapshot otherwise');
  } catch (e) {
    if (btn) { btn.textContent = 'Live check failed — snapshot kept'; setTimeout(function () { renderWhales(); }, 2500); }
  } finally {
    if (btn) { btn.disabled = false; }
  }
}

function setLiveStatus(id, live, text) {
  const n = document.getElementById(id);
  if (!n) return;
  n.textContent = text;
  n.classList.toggle('live', !!live);
}

async function refreshPrices() {
  try {
    const p = await fetchJson('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd');
    state.prices = { bitcoin: p.bitcoin.usd, ethereum: p.ethereum.usd, solana: p.solana.usd };
    state.pricesLive = true;
  } catch (e) {
    state.pricesLive = false;
  }
  renderPrices();
}

function renderPrices() {
  const grid = $('#priceGrid');
  grid.innerHTML = '';
  const snap = (state.whales && state.whales.snapshot_prices_usd) || {};
  [['Bitcoin', 'BTC', 'bitcoin', snap.BTC], ['Ethereum', 'ETH', 'ethereum', snap.ETH], ['Solana', 'SOL', 'solana', snap.SOL]]
    .forEach(function (row) {
      const card = el('div', 'price-card');
      card.appendChild(el('h3', null, row[0] + ' (' + row[1] + ')'));
      const liveVal = state.prices ? state.prices[row[2]] : null;
      const shown = liveVal !== null && liveVal !== undefined ? liveVal : row[3];
      card.appendChild(el('p', 'big-num', shown ? fmtMoneyFull(shown) : '—'));
      card.appendChild(el('p', 'muted', liveVal ? '● Live — CoinGecko' : 'Snapshot ' + SNAPSHOT_DATE + ' — CoinGecko (live check failed)'));
      grid.appendChild(card);
    });
  const btc = state.prices ? state.prices.bitcoin : snap.BTC;
  $('#statBtc').textContent = btc ? fmtMoneyFull(btc) : '—';
}

async function refreshGas() {
  try {
    const hex = await rpcCall('https://ethereum.publicnode.com', 'eth_gasPrice', []);
    const gwei = parseInt(hex, 16) / 1e9;
    $('#ethGas').textContent = fmtNum(gwei, 1) + ' Gwei';
    setLiveStatus('ethGasStatus', true, '● live');
  } catch (e) {
    $('#ethGas').textContent = 'Unavailable — public RPC unreachable';
    setLiveStatus('ethGasStatus', false, 'snapshot');
  }
  try {
    const fees = await fetchJson('https://mempool.space/api/v1/fees/recommended');
    $('#btcFee').textContent = fees.fastestFee + ' sat/vB (fast) · ' + fees.hourFee + ' sat/vB (1h)';
    $('#btcFeeNote').textContent = 'Live — mempool.space. Economy: ' + fees.economyFee + ' sat/vB · Minimum: ' + fees.minimumFee + ' sat/vB.';
    setLiveStatus('btcFeeStatus', true, '● live');
  } catch (e) {
    $('#btcFee').textContent = 'Unavailable — mempool.space unreachable';
    setLiveStatus('btcFeeStatus', false, 'snapshot');
  }
}

async function refreshAllLive() {
  const btn = $('#refreshLiveBtn');
  btn.disabled = true;
  btn.textContent = 'Refreshing…';
  await Promise.allSettled([refreshPrices(), refreshGas()]);
  const jobs = allWhales().map(function (w) { return refreshOneWhale(w, null); });
  await Promise.allSettled(jobs);
  renderWhales();
  renderPrices();
  btn.disabled = false;
  btn.textContent = '↻ Refresh live';
}

/* ---------- boot ---------- */

async function init() {
  try {
    await loadData();
  } catch (e) {
    document.querySelector('main').insertAdjacentHTML('afterbegin',
      '<section class="banner"><p><strong>Could not load data files.</strong> Open this page from the repo root (GitHub Pages or a local web server), not as a file:// URL.</p></section>');
    return;
  }
  initTabs();
  initFundingFilters();
  initWhaleFilters();
  renderFunding();
  renderWhales();
  renderPrices();
  $('#refreshLiveBtn').addEventListener('click', refreshAllLive);
  // Best-effort live prices on load; everything else stays snapshot until asked.
  refreshPrices();
  refreshGas();
}

document.addEventListener('DOMContentLoaded', init);

/* Tiny API for tests / scripting. */
window.Web3Tools = {
  state: state,
  validateAddress: validateAddress,
  fmtMoneyShort: fmtMoneyShort,
  fmtMoneyFull: fmtMoneyFull,
  explorerUrl: explorerUrl,
  fundingRounds: fundingRounds,
};
