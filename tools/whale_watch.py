#!/usr/bin/env python3
"""whale_watch.py — read-only whale wallet checker (EVM, Bitcoin, Solana).

Checks the public on-chain balance and recent transactions of any public
wallet address. NEVER asks for, imports, or uses private keys or seed
phrases — only public addresses.

Usage:
    python whale_watch.py --chain btc --address 34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo
    python whale_watch.py --chain evm --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
    python whale_watch.py --chain sol --address 2UAeWoJ9ZTv6KDk1j8kNmRsG3yKq4cGSdip459GMR6Ho
    python whale_watch.py --chain evm --address 0x... --json

Chains and data sources (all public, no key needed unless noted):
    btc  — mempool.space REST API (no key).
    evm  — Etherscan v2 API when ETHERSCAN_API_KEY is set (balance + txs);
           otherwise a public JSON-RPC endpoint (balance only).
    sol  — Solana public JSON-RPC api.mainnet-beta.solana.com (no key).

Environment variables:
    ETHERSCAN_API_KEY  — optional, enables EVM transaction history.
    EVM_RPC_URL        — optional, overrides the default public EVM RPC.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

DEFAULT_EVM_RPC = "https://ethereum.publicnode.com"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"
MEMPOOL_API = "https://mempool.space/api"
ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"

EVM_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
BTC_ADDR_RE = re.compile(
    r"^([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71})$"
)
SOL_ADDR_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

CHAINS = ("evm", "btc", "sol")


def validate_address(chain, address):
    """Return True when the address looks valid for the chain."""
    if chain == "evm":
        return bool(EVM_ADDR_RE.match(address))
    if chain == "btc":
        return bool(BTC_ADDR_RE.match(address))
    if chain == "sol":
        return bool(SOL_ADDR_RE.match(address))
    return False


def _get(session, url, **kwargs):
    try:
        resp = session.get(url, timeout=20, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"request to {url} failed: {exc}") from exc


def _rpc(session, url, method, params):
    try:
        resp = session.post(
            url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"RPC request to {url} failed: {exc}") from exc
    if data.get("error"):
        raise RuntimeError(f"RPC error from {url}: {data['error']}")
    return data["result"]


def _fmt_time(ts):
    if not ts:
        return "unknown"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------- Bitcoin (mempool.space, no key) ----------------


def btc_check(session, address, limit=5):
    info = _get(session, f"{MEMPOOL_API}/address/{address}")
    stats = info["chain_stats"]
    balance_btc = (stats["funded_txo_sum"] - stats["spent_txo_sum"]) / 1e8
    txs = _get(session, f"{MEMPOOL_API}/address/{address}/txs")[:limit]
    recent = []
    for tx in txs:
        status = tx.get("status", {})
        out_btc = sum(v.get("value", 0) for v in tx.get("vout", [])) / 1e8
        recent.append(
            {
                "txid": tx["txid"],
                "confirmed": bool(status.get("confirmed")),
                "time": _fmt_time(status.get("block_time")),
                "total_output_btc": round(out_btc, 8),
            }
        )
    return {
        "chain": "btc",
        "address": address,
        "balance": balance_btc,
        "currency": "BTC",
        "tx_count": stats["tx_count"],
        "recent_txs": recent,
        "explorer": f"https://mempool.space/address/{address}",
    }


# ---------------- EVM ----------------


def evm_check(session, address, api_key=None, rpc_url=None, limit=5):
    result = {"chain": "evm", "address": address, "currency": "ETH"}
    if api_key:
        params = {
            "chainid": 1,
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": api_key,
        }
        data = _get(session, ETHERSCAN_V2, params=params)
        if data.get("status") != "1":
            raise RuntimeError(f"Etherscan error: {data.get('message')} — {data.get('result')}")
        result["balance"] = int(data["result"]) / 1e18
        tx_params = dict(params, action="txlist", startblock=0, endblock=99999999,
                         page=1, offset=limit, sort="desc")
        txs = _get(session, ETHERSCAN_V2, params=tx_params)
        result["tx_count"] = None
        result["recent_txs"] = [
            {
                "txid": t["hash"],
                "confirmed": True,
                "time": _fmt_time(int(t["timeStamp"])),
                "value_eth": int(t["value"]) / 1e18,
                "from": t["from"],
                "to": t["to"],
            }
            for t in (txs.get("result") or [])[:limit]
        ]
    else:
        rpc = rpc_url or os.environ.get("EVM_RPC_URL") or DEFAULT_EVM_RPC
        hex_bal = _rpc(session, rpc, "eth_getBalance", [address, "latest"])
        result["balance"] = int(hex_bal, 16) / 1e18
        result["tx_count"] = int(
            _rpc(session, rpc, "eth_getTransactionCount", [address, "latest"]), 16
        )
        result["recent_txs"] = []
        result["note"] = (
            "Balance + tx count only. Set ETHERSCAN_API_KEY for recent transactions."
        )
    result["explorer"] = f"https://etherscan.io/address/{address}"
    return result


# ---------------- Solana ----------------


def sol_check(session, address, limit=5):
    lamports = _rpc(session, SOLANA_RPC, "getBalance", [address])
    sigs = _rpc(
        session, SOLANA_RPC, "getSignaturesForAddress", [address, {"limit": limit}]
    )
    return {
        "chain": "sol",
        "address": address,
        "balance": lamports["value"] / 1e9,
        "currency": "SOL",
        "tx_count": None,
        "recent_txs": [
            {
                "signature": s["signature"],
                "confirmed": s.get("confirmationStatus") in ("confirmed", "finalized"),
                "time": _fmt_time(s.get("blockTime")),
            }
            for s in sigs
        ],
        "explorer": f"https://solscan.io/account/{address}",
    }


# ---------------- CLI ----------------


def check(chain, address, api_key=None, rpc_url=None, limit=5):
    if chain not in CHAINS:
        raise ValueError(f"unknown chain {chain!r}; choose from {', '.join(CHAINS)}")
    if not validate_address(chain, address):
        raise ValueError(f"{address!r} does not look like a valid {chain} address")
    session = requests.Session()
    session.headers["User-Agent"] = "web3-tools/1.0 (read-only whale watcher)"
    if chain == "btc":
        return btc_check(session, address, limit)
    if chain == "sol":
        return sol_check(session, address, limit)
    return evm_check(session, address, api_key=api_key, rpc_url=rpc_url, limit=limit)


def render_human(result):
    lines = [
        f"Chain:    {result['chain'].upper()}",
        f"Address:  {result['address']}",
        f"Balance:  {result['balance']:,.6f} {result['currency']}".rstrip("0").rstrip("."),
        f"Explorer: {result['explorer']}",
    ]
    if result.get("tx_count") is not None:
        lines.append(f"Tx count: {result['tx_count']:,}")
    if result.get("note"):
        lines.append(f"Note:     {result['note']}")
    txs = result.get("recent_txs") or []
    lines.append(f"Recent transactions ({len(txs)} shown):")
    if not txs:
        lines.append("  (none available — see note above)")
    for tx in txs:
        txid = tx.get("txid") or tx.get("signature", "")
        extra = ""
        if "value_eth" in tx:
            extra = f" value={tx['value_eth']:.6f} ETH from={tx['from'][:10]}… to={tx['to'][:10]}…"
        elif "total_output_btc" in tx:
            extra = f" total_output={tx['total_output_btc']:.8f} BTC"
        lines.append(f"  - {txid[:20]}… {tx['time']} confirmed={tx['confirmed']}{extra}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only whale wallet checker (EVM, Bitcoin, Solana). "
        "Public addresses only — never uses private keys."
    )
    parser.add_argument("--chain", required=True, choices=CHAINS)
    parser.add_argument("--address", required=True, help="public wallet address")
    parser.add_argument("--api-key", default=os.environ.get("ETHERSCAN_API_KEY"),
                        help="Etherscan API key (EVM tx history; also via ETHERSCAN_API_KEY)")
    parser.add_argument("--rpc-url", default=None, help="custom EVM JSON-RPC URL")
    parser.add_argument("--limit", type=int, default=5, help="recent transactions to show")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args(argv)

    try:
        result = check(args.chain, args.address, api_key=args.api_key,
                       rpc_url=args.rpc_url, limit=args.limit)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_human(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
