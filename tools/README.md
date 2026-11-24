# Tools (Python CLI)

Read-only command-line tools. They only query public APIs and the repo's own
snapshot data — they never connect a wallet, sign anything, or touch private
keys or seed phrases.

## Install

```sh
pip install -r requirements.txt
```

## whale_watch.py — check a whale wallet (EVM, Bitcoin, Solana)

```sh
# Bitcoin (mempool.space, no key needed)
python whale_watch.py --chain btc --address 34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo

# EVM (balance + tx count via public RPC; no key needed)
python whale_watch.py --chain evm --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# EVM with transaction history (needs a free Etherscan key)
export ETHERSCAN_API_KEY=your_key_here
python whale_watch.py --chain evm --address 0x176F3DAb24a159341c0509bB36B833E7Fdd0a132

# Solana (public RPC, no key needed)
python whale_watch.py --chain sol --address 2UAeWoJ9ZTv6KDk1j8kNmRsG3yKq4cGSdip459GMR6Ho

# Machine-readable output
python whale_watch.py --chain btc --address <addr> --json
```

Flags: `--limit N` (recent transactions, default 5), `--rpc-url URL` (custom
EVM JSON-RPC), `--api-key KEY` (or `ETHERSCAN_API_KEY` env var),
`EVM_RPC_URL` env var to override the default public RPC.

## funding.py — list funding rounds from the snapshot data

```sh
python funding.py                            # all rounds, biggest first
python funding.py --min-amount 10000000     # rounds of $10M+
python funding.py --round "Series B"        # only Series B
python funding.py --search tether            # rounds mentioning Tether
python funding.py --sort date                # oldest first
python funding.py --total                    # disclosed total
python funding.py --json                     # raw JSON
```

The data lives in `../data/funding.json` (snapshot 24 Nov 2026, rounds
announced 2–21 Nov 2026, with sources). Edit that file to add new rounds.
