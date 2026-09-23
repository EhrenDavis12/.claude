#!/usr/bin/env python3
"""
Approve characters into a Flutter app: copy their finished sheets out of the
framework's drafts area into the app's assets, list each folder in
pubspec.yaml, and rewrite the catalog JSON the sprite player reads. This is
the one step the framework cannot do -- it can never write where the app
reads from -- and it is the human's "yes" made concrete.

  approve.py animate.yaml knight archer    approve these
  approve.py animate.yaml --all            every character whose sheets all exist
  approve.py animate.yaml --drop foo       remove a character from the app

The config's `app:` block names the assets folder, the catalog file and the
pubspec (paths relative to the config). See templates/animate.yaml.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from animate import Plan  # noqa: E402


class App:
    def __init__(self, plan: Plan):
        app = plan.cfg.get("app") or {}
        self.assets = plan.root / app.get("assets", "assets/characters")
        self.catalog_path = plan.root / app.get("catalog", "assets/characters/characters.json")
        self.pubspec = plan.root / app.get("pubspec", "pubspec.yaml")
        self.asset_prefix = app.get("assets", "assets/characters").rstrip("/")
        self.plan = plan

    def load(self) -> dict:
        return json.loads(self.catalog_path.read_text()) if self.catalog_path.exists() else {"characters": []}

    def save(self, catalog: dict) -> None:
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self.catalog_path.write_text(json.dumps(catalog, indent=2) + "\n")

    def pubspec_add(self, folder: str) -> None:
        line = f"    - {self.asset_prefix}/{folder}/\n"
        text = self.pubspec.read_text()
        if line in text:
            return
        anchor = f"    - {self.asset_prefix}/\n"
        if anchor not in text:
            raise SystemExit(f"{self.pubspec} needs a `- {self.asset_prefix}/` line under flutter: assets: to anchor on")
        self.pubspec.write_text(text.replace(anchor, anchor + line, 1))

    def pubspec_remove(self, folder: str) -> None:
        self.pubspec.write_text(self.pubspec.read_text().replace(f"    - {self.asset_prefix}/{folder}/\n", ""))

    def approve(self, cid: str) -> None:
        plan = self.plan
        spec = next(c for c in plan.characters if c["id"] == cid)
        sheets = {a: plan.drafts / "characters" / cid / f"{a}.png" for a in plan.actions}
        missing = [a for a, p in sheets.items() if not p.exists()]
        if missing:
            raise SystemExit(f"{cid}: no drafted sheet for {missing}; run animate.py first")
        skill = spec.get("skill")
        if skill:
            effects = {a: plan.drafts / "characters" / cid / f"{a}.png" for a in ("skill", "burst")}
            missing = [a for a, p in effects.items() if not p.exists()]
            if missing:
                raise SystemExit(f"{cid}: no drafted sheet for {missing}; run animate.py --action skill --action burst")
        dest = self.assets / cid
        dest.mkdir(parents=True, exist_ok=True)
        animations = {}
        for action, path in sheets.items():
            shutil.copyfile(path, dest / f"{action}.png")
            animations[action] = self.animation_json(cid, action, spec)
        entry = {"id": cid, "name": spec.get("name", cid.title()), "animations": animations}
        approved = list(plan.actions)
        if skill:
            for action, path in effects.items():
                shutil.copyfile(path, dest / f"{action}.png")
            entry["skill"] = {"name": skill["name"],
                              "spin": bool(skill.get("spin")),
                              "animation": self.animation_json(cid, "skill", spec),
                              "impact": self.animation_json(cid, "burst", spec)}
            approved += [f"skill({skill['name']})", "burst"]
        else:
            for stale in ("skill", "burst"):
                (dest / f"{stale}.png").unlink(missing_ok=True)
        catalog = self.load()
        catalog["characters"] = [c for c in catalog["characters"] if c["id"] != cid]
        catalog["characters"].append(entry)
        order = {c["id"]: i for i, c in enumerate(plan.characters)}
        catalog["characters"].sort(key=lambda c: order.get(c["id"], len(order)))
        self.save(catalog)
        self.pubspec_add(cid)
        print(f"approved {cid}: {', '.join(approved)} -> {dest.relative_to(plan.root)}")

    def animation_json(self, cid: str, action: str, spec: dict) -> dict:
        s = self.plan.sheet
        return {
            "sheet": f"{self.asset_prefix}/{cid}/{action}.png",
            "frameWidth": s["frame"], "frameHeight": s["frame"],
            "columns": s["columns"], "rows": s["rows"],
            "frameCount": len(self.plan.kept), "fps": self.plan.fps_of(action, spec),
            "loop": self.plan.loop_of(action),
        }

    def drop(self, cid: str) -> None:
        catalog = self.load()
        catalog["characters"] = [c for c in catalog["characters"] if c["id"] != cid]
        self.save(catalog)
        if (self.assets / cid).exists():
            shutil.rmtree(self.assets / cid)
        self.pubspec_remove(cid)
        print(f"dropped {cid}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--drop", action="append", default=[])
    args = ap.parse_args()
    plan = Plan(args.config)
    app = App(plan)
    for cid in args.drop:
        app.drop(cid)
    ids = list(args.ids)
    if args.all:
        ids = [c["id"] for c in plan.characters
               if all((plan.drafts / "characters" / c["id"] / f"{a}.png").exists()
                      for a in [*plan.actions, *(("skill", "burst") if c.get("skill") else ())])]
    for cid in ids:
        app.approve(cid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
