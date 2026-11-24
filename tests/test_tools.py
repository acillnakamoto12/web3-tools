"""Tests for web3-tools: data files, whale_watch.py and funding.py.

Run from the repo root:
    python3 -m pytest tests/ -q
or without pytest:
    python3 -m unittest discover -s tests -v
"""

import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import funding as funding_mod
import whale_watch as ww

EVM_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
BTC_RE = re.compile(r"^([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71})$")
SOL_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Minimal stand-in for requests.Session; routes by URL."""

    def __init__(self, routes):
        self.routes = routes  # list of (substring, payload)
        self.headers = {}

    def _match(self, url):
        for needle, payload in self.routes:
            if needle in url:
                return FakeResponse(payload)
        raise AssertionError(f"unexpected URL in test: {url}")

    def get(self, url, **kwargs):
        return self._match(url)

    def post(self, url, **kwargs):
        return self._match(url)


class TestDataFiles(unittest.TestCase):
    def test_funding_json_valid(self):
        data = json.loads((ROOT / "data" / "funding.json").read_text())
        self.assertIn("snapshot_date", data)
        self.assertGreaterEqual(len(data["rounds"]), 10)
        for r in data["rounds"]:
            for field in ("project", "date", "round", "lead_investor", "source"):
                self.assertIn(field, r, f"{r.get('project')}: missing {field}")
            self.assertRegex(r["date"], r"^\d{4}-\d{2}-\d{2}$")
            if r.get("amount_usd") is not None:
                self.assertGreater(r["amount_usd"], 0)

    def test_funds_json_valid(self):
        data = json.loads((ROOT / "data" / "funds.json").read_text())
        self.assertIn("snapshot_date", data)
        self.assertGreaterEqual(len(data["funds"]), 10)
        for f in data["funds"]:
            for field in ("name", "tier", "latest_deal", "portfolio", "retail_roi", "focus_area", "source"):
                self.assertIn(field, f, f"{f.get('name')}: missing {field}")
            self.assertIsInstance(f["tier"], int)
            self.assertGreaterEqual(f["tier"], 1)
            self.assertLessEqual(f["tier"], 5)
            self.assertGreater(f["portfolio"], 0)
            if f.get("retail_roi") is not None:
                self.assertGreaterEqual(f["retail_roi"], 0)
            deal = f["latest_deal"]
            self.assertIn("project", deal)
            self.assertRegex(deal["date"], r"^\d{4}-\d{2}-\d{2}$")
            if deal.get("amount_usd") is not None:
                self.assertGreater(deal["amount_usd"], 0)

    def test_airdrops_json_valid(self):
        data = json.loads((ROOT / "data" / "airdrops.json").read_text())
        self.assertIn("snapshot_date", data)
        self.assertGreaterEqual(len(data["airdrops"]), 1)
        for a in data["airdrops"]:
            for field in ("project", "status", "status_key", "deadline", "task", "link", "source"):
                self.assertIn(field, a, f"{a.get('project')}: missing {field}")
            self.assertIn(a["status_key"], ("active", "wl", "ended"))
            self.assertTrue(a["link"].startswith("http"))

    def test_funds_latest_deals_match_funding(self):
        """Where a fund's latest deal also appears in funding.json, the
        disclosed amount must agree (dates may differ: funding.json uses the
        weekly roundup date, funds.json the CryptoRank deal date)."""
        funding = json.loads((ROOT / "data" / "funding.json").read_text())
        by_project = {r["project"]: r for r in funding["rounds"]}
        funds = json.loads((ROOT / "data" / "funds.json").read_text())
        checked = 0
        for f in funds["funds"]:
            deal = f["latest_deal"]
            if deal["project"] in by_project and deal.get("amount_usd") is not None:
                self.assertEqual(deal["amount_usd"], by_project[deal["project"]]["amount_usd"],
                                 f"{deal['project']}: amount mismatch between funds and funding")
                checked += 1
        self.assertGreaterEqual(checked, 5, "expected at least 5 cross-checkable deals")

    def test_investor_names_match_funds(self):
        """Investor names in funding.json that normalise to a fund name must
        have that fund in funds.json (same normalisation as app.js)."""
        def norm(name):
            name = re.sub(r"[^a-z0-9 ]", " ", name.lower())
            name = re.sub(r"\b(capital|ventures|labs|partners|partner|fund|frontier)\b", " ", name)
            return re.sub(r"\s+", " ", name).strip()

        funds = json.loads((ROOT / "data" / "funds.json").read_text())
        fund_keys = {norm(f["name"]) for f in funds["funds"]}
        funding = json.loads((ROOT / "data" / "funding.json").read_text())
        linked = set()
        for r in funding["rounds"]:
            for inv in r.get("investors") or []:
                key = norm(inv)
                if key in fund_keys:
                    linked.add(inv)
        # Known links that must resolve: Dragonfly, Coinbase Ventures,
        # Pantera, Polychain, Blockchain Capital, Y Combinator.
        self.assertGreaterEqual(len(linked), 6, f"expected >=6 linked investors, got {sorted(linked)}")

    def test_whales_json_valid(self):
        data = json.loads((ROOT / "data" / "whales.json").read_text())
        self.assertIn("snapshot_date", data)
        self.assertIn("snapshot_prices_usd", data)
        chains = set()
        for w in data["wallets"]:
            self.assertIn(w["chain"], ("evm", "btc", "sol"))
            chains.add(w["chain"])
            for field in ("label", "address", "currency", "source"):
                self.assertIn(field, w, f"{w.get('label')}: missing {field}")
            if w["chain"] == "evm":
                self.assertRegex(w["address"], EVM_RE)
            elif w["chain"] == "btc":
                self.assertRegex(w["address"], BTC_RE)
            else:
                self.assertRegex(w["address"], SOL_RE)
            if w.get("balance_native") is not None:
                self.assertGreaterEqual(w["balance_native"], 0)
        self.assertEqual(chains, {"evm", "btc", "sol"}, "watchlist must cover all three chains")


class TestValidateAddress(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(ww.validate_address("evm", "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"))
        self.assertTrue(ww.validate_address("btc", "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"))
        self.assertTrue(ww.validate_address("btc", "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97"))
        self.assertTrue(ww.validate_address("sol", "2UAeWoJ9ZTv6KDk1j8kNmRsG3yKq4cGSdip459GMR6Ho"))

    def test_invalid(self):
        self.assertFalse(ww.validate_address("evm", "0x1234"))
        self.assertFalse(ww.validate_address("evm", "d8dA6BF26964aF9D7eEd9e03E53415D37aA96045"))
        self.assertFalse(ww.validate_address("btc", "not-an-address"))
        self.assertFalse(ww.validate_address("sol", "0x1234"))
        self.assertFalse(ww.validate_address("eth", "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"))


class TestWhaleWatchParsing(unittest.TestCase):
    def test_btc_check_parses_mempool(self):
        addr = "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"
        session = FakeSession([
            ("/txs", [{"txid": "ab" * 32, "status": {"confirmed": True, "block_time": 1763000000},
                       "vout": [{"value": 100000000}]}]),
            ("/address/" + addr, {"chain_stats": {"funded_txo_sum": 24859800000000,
                                                  "spent_txo_sum": 0, "tx_count": 5567}}),
        ])
        with patch.object(ww.requests, "Session", return_value=session):
            result = ww.check("btc", addr, limit=1)
        self.assertEqual(result["balance"], 248598.0)
        self.assertEqual(result["currency"], "BTC")
        self.assertEqual(result["tx_count"], 5567)
        self.assertEqual(result["recent_txs"][0]["total_output_btc"], 1.0)

    def test_evm_rpc_balance(self):
        addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        with patch.object(ww, "_rpc", side_effect=[hex(9_477_000_000_000_000_000), "0x5"]):
            result = ww.check("evm", addr)
        self.assertAlmostEqual(result["balance"], 9.477, places=3)
        self.assertEqual(result["tx_count"], 5)
        self.assertIn("note", result)

    def test_sol_check_parses_rpc(self):
        addr = "2UAeWoJ9ZTv6KDk1j8kNmRsG3yKq4cGSdip459GMR6Ho"
        with patch.object(ww, "_rpc", side_effect=[
            {"value": 98_328_000_000_000},
            [{"signature": "sig1", "confirmationStatus": "finalized", "blockTime": 1763000000}],
        ]):
            result = ww.check("sol", addr, limit=1)
        self.assertAlmostEqual(result["balance"], 98328.0)
        self.assertEqual(result["currency"], "SOL")
        self.assertEqual(result["recent_txs"][0]["signature"], "sig1")

    def test_check_rejects_bad_address(self):
        with self.assertRaises(ValueError):
            ww.check("btc", "not-an-address")

    def test_check_rejects_unknown_chain(self):
        with self.assertRaises(ValueError):
            ww.check("doge", "D8r8y7g3x")


class TestFundingModule(unittest.TestCase):
    def setUp(self):
        self.data = funding_mod.load_rounds()

    def test_loads_snapshot(self):
        self.assertIn("rounds", self.data)
        self.assertGreater(len(self.data["rounds"]), 0)

    def test_filter_by_amount(self):
        big = funding_mod.filter_rounds(self.data["rounds"], min_amount=50_000_000)
        self.assertTrue(all((r.get("amount_usd") or 0) >= 50_000_000 for r in big))
        self.assertGreater(len(big), 0)

    def test_filter_by_round(self):
        seeds = funding_mod.filter_rounds(self.data["rounds"], round_type="Seed")
        self.assertTrue(all(r["round"] == "Seed" for r in seeds))

    def test_search(self):
        hits = funding_mod.filter_rounds(self.data["rounds"], search="tether")
        self.assertGreater(len(hits), 0)
        self.assertTrue(any("Tether" in (r.get("lead_investor") or "") or
                            "Tether" in " ".join(r.get("investors", [])) for r in hits))

    def test_sort_amount_desc(self):
        rows = funding_mod.sort_rounds(self.data["rounds"], "amount")
        amounts = [r.get("amount_usd") or 0 for r in rows]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_fmt_amount(self):
        self.assertEqual(funding_mod.fmt_amount(110_000_000), "$110M")
        self.assertEqual(funding_mod.fmt_amount(47_500_000), "$47.5M")
        self.assertEqual(funding_mod.fmt_amount(None), "Undisclosed")

    def test_render_table_has_headers(self):
        out = funding_mod.render_table(self.data["rounds"][:2])
        self.assertIn("Project", out)
        self.assertIn("Variational", out)


if __name__ == "__main__":
    unittest.main()
