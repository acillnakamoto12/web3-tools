# Web3 Tools

A free, read-only toolbox for Web3: track crypto funding rounds, watch whale
wallets on **EVM, Bitcoin and Solana**, and check live prices and gas — from
one static dashboard, plus matching Python CLI tools.

**Live demo:** https://acillnakamoto12.github.io/web3-tools/

> Read-only by design. No wallet connection, no signing, no swaps, no
> private keys or seed phrases — only public addresses and public APIs.

## What is inside

| Tool | What it does |
| --- | --- |
| 💰 **Funding tracker** | Table of crypto funding rounds (project, date, round, amount, lead investor), with search, round filter and sorting. |
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
  crypto.news, WEEX, NAUT and hodl.press. Each entry lists its source; where
  only the announcement week is known, the weekly roundup date is used and
  marked with a `date_note`.
- **Whale wallets** — `data/whales.json`: 10 public wallets (3 EVM, 6 BTC,
  1 SOL). Balances are snapshots from BitInfoCharts' live rich list,
  Arkham, and on-chain incident reports (see the `source` field on each
  wallet). Exchange cold wallets hold **customer funds**, not the exchange's
  own money. Attribution labels (e.g. "Justin Sun (attributed)") mean
  on-chain analysts tagged the wallet — not a self-confirmed owner.
- **Live prices** — CoinGecko public API (no key). Live BTC balances:
  mempool.space API (no key). Live ETH balance/gas: ethereum.publicnode.com
  (no key). Live SOL balance: api.mainnet-beta.solana.com (no key).

To update the snapshot, edit `data/funding.json` / `data/whales.json` and
update `snapshot_date` — the dashboard and CLI read the same files.

## Files

| File | What it is |
| --- | --- |
| `index.html` / `styles.css` / `app.js` | Static dashboard (no build step) |
| `data/funding.json` | Funding rounds snapshot + sources |
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
