# Web3 Tools

A free, read-only toolbox for Web3: track crypto funding rounds, browse a
directory of crypto funds (CryptoRank-style), follow Acill's airdrop
watchlist, watch whale wallets on **EVM, Bitcoin and Solana**, and check live
prices and gas — from one static dashboard, plus matching Python CLI tools.

**Live demo:** https://acillnakamoto12.github.io/web3-tools/

> Read-only by design. No wallet connection, no signing, no swaps, no
> private keys or seed phrases — only public addresses and public APIs.

## What is inside

| Tool | What it does |
| --- | --- |
| 💰 **Funding tracker** | Table of crypto funding rounds (project, date, round, amount, lead investor), with search, round filter and sorting. Every round lists **all its investors** — click an investor name that is a fund in the directory to jump to that fund's entry in the Funds tab. |
| 🏦 **Funds** | Directory of crypto funds, CryptoRank-style: name, tier, latest deal, portfolio size, retail ROI and focus area, with search and tier / focus-area filters. Data is a verified snapshot from [CryptoRank Funds](https://cryptorank.io/funds) (24 Nov 2026); fund marks are text initials — no CryptoRank branding or logos. |
| 🪂 **Airdrop tracker** | **Acill's personal watchlist** — the airdrops he works on himself (project, status, deadline, task/claim, link), with status filter and search. This is not a general airdrop directory. |
| 🐋 **Whale watch** | Watchlist of famous public whale wallets (EVM + BTC + SOL) with snapshot balances, explorer links, copy-address, live balance refresh, and add-your-own wallets (stored only in your browser). |
| 📈 **Prices & gas** | Live BTC / ETH / SOL prices (CoinGecko), Ethereum gas price and Bitcoin fee estimates — all from public no-key APIs, with snapshot fallback. |
| 🐍 **CLI tools** (`tools/`) | `whale_watch.py` (check any public wallet: balance + recent txs) and `funding.py` (search the funding snapshot from your terminal). |

## Use the dashboard

Open the [live demo](https://acillnakamoto12.github.io/web3-tools/) (or open
`index.html` from a local web server — `python3 -m http.server` — not as a
`file://` URL, because the page fetches its data files).

- **Refresh live** re-checks prices and wallet balances from public APIs.
  If a live check fails (offline, rate-limited), the verified snapshot value
  stays and is labelled as a snapshot.
- **Funds:** search a fund by name, focus area or latest deal; filter by
  tier or focus area; sort by portfolio size or retail ROI. Each fund shows
  its latest deal (project, amount, date).
- **Funding ↔ Funds:** in the Funding tab, investor names that match a fund
  in the directory are links — click one to jump to that fund's entry.
- **Airdrops:** Acill's own watchlist. Filter by status (Active — daily /
  WL secured / Ended) or search by project or task.
- **+ Add wallet to watch** saves extra wallets in your browser only.

## Use the CLI tools

```sh
pip install -r tools/requirements.txt

# Check a whale wallet (BTC needs no key; EVM balance needs no key;
# EVM tx history needs a free Etherscan key)
python tools/whale_watch.py --chain btc --address 34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo
python tools/whale_watch.py --chain evm --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
python tools/whale_watch.py --chain sol --address 2UAeWoJ9ZTv6KDk1j8kNmRsG3yKq4cGSdip459GMR6Ho
export ETHERSCAN_API_KEY=your_key_here   # optional, for EVM tx history

# Search the funding snapshot
python tools/funding.py --min-amount 10000000
python tools/funding.py --round "Series B"
python tools/funding.py --total
```

See [`tools/README.md`](tools/README.md) for all flags.

## Data & sources (snapshot: 24 Nov 2026)

- **Funding rounds** — `data/funding.json`: 22 rounds announced 2–21 Nov
  2026 (total disclosed ≈ $681.2M), compiled from DefiLlama Raises,
  crypto.news, WEEX, NAUT and hodl.press. Each entry lists its source and
  all its investors (unknown investors are written as N/A, never guessed);
  where only the announcement week is known, the weekly roundup date is used
  and marked with a `date_note`.
- **Funds** — `data/funds.json`: 12 Tier 1 crypto funds as listed on
  [CryptoRank Funds](https://cryptorank.io/funds) on 24 Nov 2026 (tier,
  latest deal, portfolio size, retail ROI, primary focus area). Latest-deal
  amounts cross-checked against `data/funding.json` where the project
  appears in both (Variational $110M, Codex $30M, Index Industries $50M,
  Uranium Digital $16.50M, End Close $3.50M). Focus area shown is the
  primary tag CryptoRank lists for each fund.
- **Airdrops** — `data/airdrops.json`: Acill's personal watchlist (Qyro
  Labs, Darkhorse, vAPI Earn, Zero Guys, Pixelora), status as of 24 Nov
  2026, from Acill's own verified records. Not a general directory.
- **Whale wallets** — `data/whales.json`: 10 public wallets (3 EVM, 6 BTC,
  1 SOL). Balances are snapshots from BitInfoCharts' live rich list,
  Arkham, and on-chain incident reports (see the `source` field on each
  wallet). Exchange cold wallets hold **customer funds**, not the exchange's
  own money. Attribution labels (e.g. "Justin Sun (attributed)") mean
  on-chain analysts tagged the wallet — not a self-confirmed owner.
- **Live prices** — CoinGecko public API (no key). Live BTC balances:
  mempool.space API (no key). Live ETH balance/gas: ethereum.publicnode.com
  (no key). Live SOL balance: api.mainnet-beta.solana.com (no key).

To update the snapshot, edit `data/funding.json` / `data/funds.json` /
`data/airdrops.json` / `data/whales.json` and update `snapshot_date` — the
dashboard and CLI read the same files.

## Files

| File | What it is |
| --- | --- |
| `index.html` / `styles.css` / `app.js` | Static dashboard (no build step) |
| `data/funding.json` | Funding rounds snapshot + sources |
| `data/funds.json` | Crypto funds directory snapshot + sources |
| `data/airdrops.json` | Acill's airdrop watchlist snapshot + sources |
| `data/whales.json` | Whale watchlist snapshot + sources |
| `tools/whale_watch.py` | CLI: check a public wallet (EVM/BTC/SOL) |
| `tools/funding.py` | CLI: search the funding snapshot |
| `tools/requirements.txt` | `requests` |
| `tests/test_tools.py` | Unit tests (data validation + CLI parsing) |

## Development / tests

```sh
node --check app.js
python3 -m py_compile tools/*.py
python3 -m pytest tests/ -q        # or: python3 -m unittest discover -s tests
python3 -m http.server 8000        # then open http://localhost:8000
```

## License

MIT — see [LICENSE](LICENSE).
