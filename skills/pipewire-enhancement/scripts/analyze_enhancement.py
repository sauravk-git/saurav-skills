#!/usr/bin/env python3
"""
analyze_enhancement.py — PipeWire enhancement request scaffolder.

Validates required fields, maps the request to affected components,
and prints a pre-filled input template ready to paste into QGenie chat.

Usage:
    python3 analyze_enhancement.py --interactive
    python3 analyze_enhancement.py --title "..." --platform IQ9075 --stack "QLI 2.x" --type audio-quality
    python3 analyze_enhancement.py --from-file request.txt
"""

import argparse
import datetime
import json
import sys
import textwrap
from typing import Optional

# ---------------------------------------------------------------------------
# Component mapping
# ---------------------------------------------------------------------------

TYPE_COMPONENTS = {
    "new-feature": [
        ("PipeWire Core", "New node/port/link type", "New"),
        ("SPA", "New plugin or factory", "New"),
        ("WirePlumber", "New policy module", "New"),
    ],
    "enhancement": [
        ("PipeWire Core", "Existing API extension", "Modify"),
        ("SPA", "Plugin behaviour change", "Modify"),
    ],
    "performance": [
        ("PipeWire Core", "Buffering / scheduling", "Modify"),
        ("SPA", "spa.alsa buffer tuning", "Modify"),
        ("Qualcomm PAL", "DSP offload path", "Investigate"),
    ],
    "startup": [
        ("WirePlumber", "Device/node discovery ordering", "Modify"),
        ("Qualcomm PAL", "modem/remoteproc startup", "Investigate"),
        ("Yocto", "systemd service ordering", "Config"),
    ],
    "audio-quality": [
        ("PipeWire Core", "Node state transitions", "Investigate"),
        ("SPA", "spa.alsa underrun / pre-roll", "Investigate"),
        ("WirePlumber", "Node activation sequencing", "Investigate"),
        ("pipewire-pal-plugin", "Stream open/close lifecycle", "Investigate"),
        ("PAL", "usecase_mgr start/stop ramp", "Investigate"),
        ("AudioReach / ADSP", "DSP graph ramp, codec pop suppression", "Investigate"),
    ],
    "routing": [
        ("WirePlumber", "Default sink/source policy", "Modify"),
        ("PipeWire Core", "Link management", "Modify"),
        ("Qualcomm PAL", "Multi-device routing", "Investigate"),
    ],
    "config": [
        ("WirePlumber", "Lua configuration", "Config"),
        ("Yocto", "PACKAGECONFIG / recipe", "Config"),
        ("Qualcomm PAL", "Config 1 / Config 2 topology", "Config"),
    ],
    "pal-integration": [
        ("pipewire-pal-plugin", "PAL API calls", "Modify"),
        ("PAL", "usecase_mgr", "Modify"),
        ("AudioReach", "Graph construction", "Modify"),
        ("ADSP", "Firmware interface", "Investigate"),
    ],
    "api": [
        ("PipeWire Core", "Core protocol / API", "Modify"),
        ("SPA", "SPA interface", "Modify"),
        ("pipewire-pal-plugin", "PAL API surface", "Modify"),
    ],
    "debug": [
        ("PipeWire Core", "Logging / tracing", "Investigate"),
        ("SPA", "spa.alsa diagnostics", "Investigate"),
        ("WirePlumber", "Event tracing", "Investigate"),
        ("Qualcomm PAL", "PAL debug logs", "Investigate"),
    ],
    "documentation": [
        ("IQ/QCS Documentation", "New or updated section", "Doc"),
        ("AudioReach", "Topology / API docs", "Doc"),
        ("PAL", "Usecase reference", "Doc"),
    ],
    "testing": [
        ("PipeWire Core", "Unit / integration tests", "Test"),
        ("SPA", "Plugin tests", "Test"),
        ("Platform", "Hardware-in-loop tests", "Test"),
    ],
    "packaging": [
        ("Yocto", "pipewire / wireplumber recipe", "Modify"),
        ("Debian", "debian/ metadata", "Modify"),
        ("RPM", "spec file", "Modify"),
        ("CI", "Debusine / GitHub Actions", "Modify"),
    ],
}

TYPE_ALIASES = {
    "1": "new-feature", "new": "new-feature", "feature": "new-feature",
    "2": "enhancement", "enhance": "enhancement",
    "3": "performance", "perf": "performance",
    "4": "startup", "enum": "startup", "enumeration": "startup",
    "5": "audio-quality", "quality": "audio-quality", "glitch": "audio-quality",
    "6": "routing", "policy": "routing",
    "7": "config", "configuration": "config",
    "8": "pal-integration", "pal": "pal-integration", "audioreach": "pal-integration",
    "9": "api", "abi": "api",
    "10": "debug", "debugging": "debug", "rca": "debug",
    "11": "documentation", "doc": "documentation", "docs": "documentation",
    "12": "testing", "test": "testing", "validation": "testing",
    "13": "packaging", "package": "packaging", "deploy": "packaging",
}

PLATFORMS = {
    "IQ615":        {"stack": ["QLI 1.x"], "config": ["Config 1"]},
    "IQ8275-EVK":   {"stack": ["QLI 1.x", "QLI 2.x"], "config": ["Config 1", "Config 2"]},
    "IQ9075":       {"stack": ["QLI 2.x"], "config": ["Config 1", "Config 2"]},
    "RB3-Gen2":     {"stack": ["QLI 1.x", "QLI 2.x"], "config": ["Config 1", "Config 2"]},
    "QCS6490":      {"stack": ["QLI 2.x"], "config": ["Config 1", "Config 2"]},
    "SA8775P":      {"stack": ["QLI 2.x"], "config": ["Config 2"]},
    "generic-aarch64": {"stack": ["QLI 1.x"], "config": ["Config 1"]},
}

REQUIRED_FIELDS = [
    ("title",       "Enhancement Title"),
    ("problem",     "User-visible Problem"),
    ("expected",    "Expected Behaviour"),
    ("current",     "Current Behaviour"),
    ("platform",    "Target Platform/Product"),
]

OPTIONAL_FIELDS = [
    ("build",       "Software Image / Build"),
    ("pw_version",  "PipeWire Version"),
    ("wp_version",  "WirePlumber Version"),
    ("kernel",      "Kernel Version"),
    ("firmware",    "Firmware Version"),
    ("audio_path",  "Audio Path"),
    ("repro",       "Reproduction Steps"),
    ("logs",        "Logs / Diagnostic Data"),
    ("func_req",    "Functional Requirements"),
    ("perf_req",    "Performance Requirements"),
    ("compat",      "Backward-Compat. Req."),
    ("security",    "Security Considerations"),
    ("criteria",    "Acceptance Criteria"),
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def resolve_types(type_str: str) -> list:
    """Parse comma-separated type string into canonical type keys."""
    types = []
    for t in type_str.replace(";", ",").split(","):
        t = t.strip().lower()
        canonical = TYPE_ALIASES.get(t, t)
        if canonical in TYPE_COMPONENTS:
            types.append(canonical)
        else:
            print(f"  WARN: unknown type '{t}' — skipping", file=sys.stderr)
    return types or ["enhancement"]


def map_components(types: list) -> list:
    """Return deduplicated component list for the given types."""
    seen = set()
    result = []
    for t in types:
        for comp in TYPE_COMPONENTS.get(t, []):
            key = (comp[0], comp[1])
            if key not in seen:
                seen.add(key)
                result.append(comp)
    return result


def platform_notes(platform: str) -> str:
    info = PLATFORMS.get(platform)
    if not info:
        return f"  Platform '{platform}' not in known list — add to PLATFORMS dict if needed."
    stacks = ", ".join(info["stack"])
    configs = ", ".join(info["config"])
    return f"  Supported stacks: {stacks} | Supported configs: {configs}"


def render_template(fields: dict, types: list, components: list) -> str:
    """Render the pre-filled input template."""
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    type_names = {
        "new-feature": "1. New PipeWire feature",
        "enhancement": "2. Existing feature enhancement",
        "performance": "3. Performance improvement",
        "startup":     "4. Startup / enumeration improvement",
        "audio-quality": "5. Audio quality improvement",
        "routing":     "6. Routing or policy enhancement",
        "config":      "7. Configuration enhancement",
        "pal-integration": "8. PAL / AudioReach integration enhancement",
        "api":         "9. API or ABI enhancement",
        "debug":       "10. Debugging / root-cause investigation",
        "documentation": "11. Documentation enhancement",
        "testing":     "12. Test or validation enhancement",
        "packaging":   "13. Packaging or deployment enhancement",
    }

    lines = [
        "=" * 72,
        "  PipeWire Enhancement Request — Pre-filled Template",
        f"  Generated: {now}",
        "=" * 72,
        "",
        "## Input Fields",
        "",
    ]

    all_fields = REQUIRED_FIELDS + OPTIONAL_FIELDS
    for key, label in all_fields:
        val = fields.get(key, "")
        marker = " [REQUIRED]" if (key, label) in REQUIRED_FIELDS and not val else ""
        lines.append(f"  {label:<30}: {val or '—'}{marker}")

    lines += [
        "",
        "## Detected Classification",
        "",
    ]
    for t in types:
        lines.append(f"  ✓  {type_names.get(t, t)}")

    lines += [
        "",
        "## Affected Components (auto-mapped)",
        "",
        f"  {'Component':<35} {'Sub-component':<40} {'Change'}",
        "  " + "─" * 85,
    ]
    for comp, sub, change in components:
        lines.append(f"  {comp:<35} {sub:<40} {change}")

    if fields.get("platform"):
        lines += [
            "",
            "## Platform Notes",
            "",
            platform_notes(fields["platform"]),
        ]

    lines += [
        "",
        "=" * 72,
        "  Paste the above into QGenie chat to generate the full proposal.",
        "=" * 72,
    ]

    return "\n".join(lines)


def interactive_mode() -> dict:
    """Prompt the user for each field interactively."""
    print("\nPipeWire Enhancement Request — Interactive Input")
    print("─" * 50)
    print("(Press Enter to skip optional fields)\n")

    fields = {}
    for key, label in REQUIRED_FIELDS:
        while True:
            val = input(f"  {label}: ").strip()
            if val:
                fields[key] = val
                break
            print(f"    ↳ Required — please enter a value.")

    print("\n  Optional fields (Enter to skip):")
    for key, label in OPTIONAL_FIELDS:
        val = input(f"  {label}: ").strip()
        if val:
            fields[key] = val

    print("\n  Enhancement types (comma-separated numbers or names):")
    print("  1=new-feature 2=enhancement 3=performance 4=startup 5=audio-quality")
    print("  6=routing 7=config 8=pal-integration 9=api 10=debug")
    print("  11=documentation 12=testing 13=packaging")
    type_str = input("  Types: ").strip() or "enhancement"
    fields["types"] = type_str

    return fields


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analyze_enhancement",
        description="Scaffold a PipeWire enhancement request and map it to components.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python3 analyze_enhancement.py --interactive
              python3 analyze_enhancement.py \\
                  --title "Audio glitch at playback start" \\
                  --platform IQ9075 --stack "QLI 2.x" \\
                  --type audio-quality,debug
              python3 analyze_enhancement.py --list-types
              python3 analyze_enhancement.py --list-platforms
        """),
    )
    p.add_argument("--interactive", "-i", action="store_true",
                   help="Prompt for each field interactively")
    p.add_argument("--title",    metavar="STR", help="Enhancement title")
    p.add_argument("--problem",  metavar="STR", help="User-visible problem")
    p.add_argument("--expected", metavar="STR", help="Expected behaviour")
    p.add_argument("--current",  metavar="STR", help="Current behaviour")
    p.add_argument("--platform", metavar="STR",
                   help=f"Target platform ({', '.join(PLATFORMS)})")
    p.add_argument("--stack",    metavar="STR", help="Audio stack (QLI 1.x / QLI 2.x)")
    p.add_argument("--type",     metavar="STR", default="enhancement",
                   help="Comma-separated enhancement types (numbers or names)")
    p.add_argument("--from-file", metavar="FILE",
                   help="Read fields from a JSON or plain-text file")
    p.add_argument("--output", choices=["text", "json"], default="text",
                   help="Output format (default: text)")
    p.add_argument("--list-types",     action="store_true",
                   help="List all enhancement types and exit")
    p.add_argument("--list-platforms", action="store_true",
                   help="List all known platforms and exit")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_types:
        print("\nEnhancement types:")
        for num, (key, _) in enumerate([
            ("new-feature",""), ("enhancement",""), ("performance",""),
            ("startup",""), ("audio-quality",""), ("routing",""),
            ("config",""), ("pal-integration",""), ("api",""),
            ("debug",""), ("documentation",""), ("testing",""), ("packaging",""),
        ], 1):
            aliases = [k for k, v in TYPE_ALIASES.items() if v == key and not k.isdigit()]
            print(f"  {num:>2}. {key:<20} (aliases: {', '.join(aliases[:3])})")
        return

    if args.list_platforms:
        print("\nKnown platforms:")
        for name, info in PLATFORMS.items():
            print(f"  {name:<20} stacks: {', '.join(info['stack']):<25} "
                  f"configs: {', '.join(info['config'])}")
        return

    if args.interactive:
        fields = interactive_mode()
        types = resolve_types(fields.pop("types", "enhancement"))
    elif args.from_file:
        import pathlib
        raw = pathlib.Path(args.from_file).read_text()
        try:
            fields = json.loads(raw)
        except json.JSONDecodeError:
            # Plain text — treat as title
            fields = {"title": raw.strip()[:200]}
        types = resolve_types(fields.pop("types", args.type))
    else:
        fields = {
            "title":    args.title    or "",
            "problem":  args.problem  or "",
            "expected": args.expected or "",
            "current":  args.current  or "",
            "platform": args.platform or "",
        }
        if args.stack:
            fields["build"] = args.stack
        types = resolve_types(args.type)

    # Validate required fields
    missing = [label for key, label in REQUIRED_FIELDS if not fields.get(key)]
    if missing:
        print(f"\n  WARN: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        print("  Run with --interactive to fill them in.\n", file=sys.stderr)

    components = map_components(types)

    if args.output == "json":
        print(json.dumps({
            "fields": fields,
            "types": types,
            "components": [{"component": c, "sub": s, "change": ch}
                           for c, s, ch in components],
        }, indent=2))
    else:
        print(render_template(fields, types, components))


if __name__ == "__main__":
    main()
