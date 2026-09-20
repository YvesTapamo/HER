"""Transparent, configurable classification with explicit uncertainty."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Classification:
    sha_code: str | None
    srhr_code: str | None
    confidence: float
    method: str
    rationale: str
    review_status: str


class Classifier:
    def __init__(self, rules_path: Path):
        config = json.loads(rules_path.read_text(encoding="utf-8"))
        self.account_rules = config["account_rules"]
        self.keyword_rules = config["keyword_rules"]
        self.auto_threshold = float(config.get("auto_accept_threshold", 0.85))

    @staticmethod
    def normalize(text: str | None) -> str:
        text = unicodedata.normalize("NFKD", text or "")
        text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    def classify(self, country: str, account: str, description: str | None) -> Classification:
        rule = self.account_rules.get(country, {}).get(str(account))
        if rule:
            confidence = float(rule["confidence"])
            return Classification(
                rule.get("sha"), rule.get("srhr", "SRHR.NA"), confidence,
                "country_account_rule", rule["rationale"],
                "auto_classified" if confidence >= self.auto_threshold else "review_required",
            )

        normalized = self.normalize(description)
        matches = []
        for candidate in self.keyword_rules:
            terms = [self.normalize(term) for term in candidate["terms"]]
            if any(term in normalized for term in terms):
                matches.append(candidate)
        if len(matches) == 1:
            rule = matches[0]
            confidence = float(rule.get("confidence", 0.7))
            return Classification(
                rule.get("sha"), rule.get("srhr", "SRHR.NA"), confidence,
                "keyword_fallback", f"Keyword fallback: {rule['name']}", "review_required",
            )
        if len(matches) > 1:
            return Classification(None, None, 0.0, "ambiguous_keywords",
                                  "Multiple keyword rules matched", "review_required")
        return Classification(None, None, 0.0, "unmapped",
                              "No reliable account or keyword rule", "review_required")
