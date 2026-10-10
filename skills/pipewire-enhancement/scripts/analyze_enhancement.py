#!/usr/bin/env python3
"""
analyze_enhancement.py — PipeWire Enhancement Proposal Generator

Accepts your issue description and what you want to build, then produces
a complete structured implementation proposal — no template-filling needed.

Three ways to use it:

  1. Conversational (recommended):
       python3 analyze_enhancement.py
       → prompts you for issue + goal, then prints the full proposal

  2. One-liner:
       python3 analyze_enhancement.py \\
           --issue "Audio glitch at playback start on IQ9075 QLI 2.x" \\
           --goal  "Eliminate the tick without regressing other paths"

  3. From a file:
       python3 analyze_enhancement.py --from-file my_issue.txt

The proposal covers all 10 sections:
  Enhancement Summary · Classification · Affected Components · Gap Analysis ·
  Architecture & Design Notes · Implementation Plan · Test & Validation Plan ·
  Documentation Tasks · Open Questions & Risks · Acceptance Criteria
"""

import argparse
import datetime
import re
import sys
import textwrap
from typing import Optional

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
USE_COLOR = True

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

BOLD   = lambda t: _c("1",  t)
CYAN   = lambda t: _c("36", t)
GREEN  = lambda t: _c("32", t)
YELLOW = lambda t: _c("33", t)
DIM    = lambda t: _c("2",  t)
RED    = lambda t: _c("31", t)

# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

PLATFORMS = {
    "iq615":         {"name": "IQ615",        "stack": "QLI 1.x", "configs": ["Config 1"]},
    "iq8275":        {"name": "IQ8275-EVK",   "stack": "QLI 1.x / 2.x", "configs": ["Config 1", "Config 2"]},
    "iq9075":        {"name": "IQ9075",        "stack": "QLI 2.x", "configs": ["Config 1", "Config 2"]},
    "rb3":           {"name": "RB3-Gen2",      "stack": "QLI 1.x / 2.x", "configs": ["Config 1", "Config 2"]},
    "qcs6490":       {"name": "QCS6490",       "stack": "QLI 2.x", "configs": ["Config 1", "Config 2"]},
    "sa8775p":       {"name": "SA8775P",       "stack": "QLI 2.x", "configs": ["Config 2"]},
    "generic":       {"name": "generic-aarch64","stack": "QLI 1.x", "configs": ["Config 1"]},
}

ENHANCEMENT_TYPES = {
    1:  "New PipeWire feature",
    2:  "Existing feature enhancement",
    3:  "Performance improvement",
    4:  "Startup / enumeration improvement",
    5:  "Audio quality improvement",
    6:  "Routing or policy enhancement",
    7:  "Configuration enhancement",
    8:  "PAL / AudioReach integration enhancement",
    9:  "API or ABI enhancement",
    10: "Debugging / root-cause investigation",
    11: "Documentation enhancement",
    12: "Test or validation enhancement",
    13: "Packaging or deployment enhancement",
}

# Keyword → type numbers
KEYWORD_TYPE_MAP = [
    (["glitch", "tick", "pop", "noise", "quality", "distort", "crackle"],   [5, 10]),
    (["startup", "boot", "enumerat", "detect", "missing device", "not found"], [4, 10]),
    (["latency", "performance", "cpu", "power", "offload", "compress"],     [3, 8]),
    (["routing", "policy", "sink", "source", "default", "switch"],          [6]),
    (["ssmd", "multi.device", "multi device"],                               [6, 8]),
    (["fluence", "voice", "noise.cancel", "aec", "ns "],                    [8, 5]),
    (["config 1", "config 2", "topology", "bin file", "\.bin"],             [7, 8]),
    (["wireplumber", "lua", "policy"],                                       [6, 7]),
    (["pal", "audioreach", "adsp", "dsp", "agm", "spf"],                    [8]),
    (["api", "abi", "interface", "protocol"],                                [9]),
    (["document", "doc ", "guide", "readme", "wiki"],                       [11]),
    (["test", "validat", "ci ", "automat"],                                  [12]),
    (["package", "yocto", "recipe", "debian", "rpm", "deploy"],             [13]),
    (["new feature", "add support", "implement", "enable"],                  [1, 2]),
    (["improve", "enhance", "optimis", "optimiz", "better"],                [2, 3]),
    (["debug", "investigate", "root cause", "rca", "diagnos"],              [10]),
]

# Keyword → affected components
KEYWORD_COMPONENT_MAP = [
    (["glitch", "tick", "pop", "underrun", "xrun", "pre-roll"],
     [("SPA", "spa.alsa underrun / pre-roll buffer", "Investigate / Modify"),
      ("PipeWire Core", "Node state transitions (preparing→running)", "Investigate"),
      ("pipewire-pal-plugin", "Stream open/close lifecycle", "Investigate"),
      ("PAL", "usecase_mgr start/stop ramp", "Investigate"),
      ("AudioReach / ADSP", "DSP graph ramp, codec pop suppression", "Investigate")]),

    (["startup", "boot", "enumerat", "detect", "missing", "not found", "sound card"],
     [("WirePlumber", "Device/node discovery ordering", "Investigate / Modify"),
      ("Yocto", "systemd service ordering", "Config"),
      ("PAL", "modem/remoteproc startup sequence", "Investigate")]),

    (["latency", "performance", "cpu", "power"],
     [("PipeWire Core", "Buffering / scheduling / quantum", "Modify"),
      ("SPA", "spa.alsa buffer tuning", "Modify"),
      ("PAL", "DSP offload path", "Investigate")]),

    (["compress", "offload"],
     [("SPA", "spa.alsa compressed path / ALSA compress API", "Modify"),
      ("PAL", "StreamCompress lifecycle", "Modify"),
      ("PipeWire Core", "Compressed node scheduling", "Modify")]),

    (["routing", "policy", "sink", "source", "default", "switch", "link"],
     [("WirePlumber", "Default sink/source policy", "Modify"),
      ("PipeWire Core", "Link management", "Modify"),
      ("PAL", "Multi-device routing", "Investigate")]),

    (["ssmd", "multi.device", "multi device"],
     [("PAL", "Multi-device usecase (SSMD)", "Modify"),
      ("AudioReach", "SSMD topology configuration", "Modify"),
      ("WirePlumber", "Multi-sink linking policy", "Modify"),
      ("PipeWire Core", "Port routing to multiple sinks", "Modify")]),

    (["fluence", "voice", "noise.cancel", "aec"],
     [("AudioReach / ADSP", "Fluence voice processing graph", "Modify"),
      ("PAL", "Voice usecase configuration", "Modify"),
      ("WirePlumber", "Capture routing policy", "Config")]),

    (["config 1", "config 2", "topology", "\.bin"],
     [("PAL", "Config 1 / Config 2 topology selection", "Config"),
      ("AudioReach", "Topology .bin loading", "Investigate"),
      ("Yocto", "Firmware packaging", "Config")]),

    (["wireplumber", "lua"],
     [("WirePlumber", "Lua configuration / policy module", "Modify"),
      ("WirePlumber", "Event handling / startup ordering", "Modify")]),

    (["pal", "audioreach", "adsp", "agm", "spf"],
     [("pipewire-pal-plugin", "PAL API calls", "Modify"),
      ("PAL", "usecase_mgr", "Modify"),
      ("AudioReach", "Graph construction", "Modify"),
      ("ADSP", "Firmware interface", "Investigate")]),

    (["yocto", "recipe", "packageconfig", "bitbake"],
     [("Yocto", "pipewire / wireplumber recipe", "Modify"),
      ("Yocto", "PACKAGECONFIG / systemd ordering", "Config")]),

    (["debian", "rpm", "package", "deploy", "debusine"],
     [("Debian", "debian/ metadata", "Modify"),
      ("RPM", "spec file", "Modify"),
      ("CI", "Debusine / GitHub Actions", "Modify")]),

    (["document", "doc ", "guide", "readme"],
     [("Documentation", "New or updated section", "Doc"),
      ("AudioReach", "Topology / API docs", "Doc")]),

    (["test", "validat", "ci ", "automat"],
     [("PipeWire Core", "Unit / integration tests", "Test"),
      ("Platform", "Hardware-in-loop tests", "Test")]),
]

DIAGNOSTIC_HINTS = {
    "glitch|tick|pop|noise|crackle": [
        "PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i 'underrun\\|xrun\\|error'",
        "pw-top  # watch for xruns in real time",
        "journalctl -u wireplumber --since '1 min ago' | grep -i 'activat\\|link\\|node'",
    ],
    "startup|enumerat|missing|not found": [
        "aplay -l && arecord -l  # check ALSA sees the card",
        "pw-cli ls Device        # check PipeWire sees the device",
        "cat /sys/class/remoteproc/remoteproc*/state  # check ADSP/modem",
        "journalctl -u wireplumber -b | head -50",
    ],
    "latency|performance|cpu": [
        "pw-top  # check quantum and CPU usage",
        "PIPEWIRE_LATENCY=64/48000 pw-play test.wav  # test lower quantum",
        "cat /proc/interrupts | grep snd",
    ],
    "routing|policy|sink|source": [
        "wpctl status            # show current device/node/link state",
        "wpctl inspect <id>      # inspect a specific object",
        "pw-dump | python3 -m json.tool | grep -A5 '\"type\": \"PipeWire:Interface:Link\"'",
    ],
    "ssmd|multi.device": [
        "grep -i 'SSMD\\|multi.*device' /etc/pal/resourcemanager.xml",
        "pw-dump | python3 -m json.tool | grep -B2 -A10 '\"type\": \"PipeWire:Interface:Link\"'",
    ],
}

# ---------------------------------------------------------------------------
# Analysis engine
# ---------------------------------------------------------------------------

def _match_keywords(text: str, keyword_list: list) -> bool:
    text_lower = text.lower()
    return any(re.search(kw, text_lower) for kw in keyword_list)


def detect_types(issue: str, goal: str) -> list:
    combined = (issue + " " + goal).lower()
    matched = set()
    for keywords, types in KEYWORD_TYPE_MAP:
        if _match_keywords(combined, keywords):
            matched.update(types)
    return sorted(matched) or [2]  # default: enhancement


def detect_components(issue: str, goal: str) -> list:
    combined = (issue + " " + goal).lower()
    seen = set()
    result = []
    for keywords, components in KEYWORD_COMPONENT_MAP:
        if _match_keywords(combined, keywords):
            for comp in components:
                key = (comp[0], comp[1])
                if key not in seen:
                    seen.add(key)
                    result.append(comp)
    if not result:
        result = [
            ("PipeWire Core", "General — to be determined", "Investigate"),
            ("SPA", "General — to be determined", "Investigate"),
        ]
    return result


def detect_platform(issue: str, goal: str) -> Optional[dict]:
    combined = (issue + " " + goal).lower()
    for key, info in PLATFORMS.items():
        if key in combined or info["name"].lower() in combined:
            return info
    return None


def detect_diagnostics(issue: str) -> list:
    hints = []
    for pattern, cmds in DIAGNOSTIC_HINTS.items():
        if re.search(pattern, issue.lower()):
            hints.extend(cmds)
    return list(dict.fromkeys(hints))  # deduplicate, preserve order


def detect_gaps(issue: str, goal: str, platform: Optional[dict]) -> list:
    gaps = []
    combined = (issue + " " + goal).lower()
    if not platform:
        gaps.append("Target platform / product not specified (IQ9075 / QCS6490 / SA8775P / RB3-Gen2 / ...)")
    if not re.search(r'pipewire\s*[\d.]|pw\s*[\d.]|1\.\d|0\.3', combined):
        gaps.append("PipeWire version not specified")
    if not re.search(r'wireplumber\s*[\d.]|wp\s*[\d.]|0\.[45]', combined):
        gaps.append("WirePlumber version not specified")
    if not re.search(r'kernel\s*[\d.]|\d+\.\d+\.\d+-', combined):
        gaps.append("Kernel version not specified")
    if re.search(r'glitch|tick|pop|noise|crackle|quality', combined):
        if not re.search(r'log|logcat|journal|pw-top|xrun|underrun', combined):
            gaps.append("No diagnostic logs provided — run: PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1")
        if not re.search(r'both channel|left|right|mono|stereo', combined):
            gaps.append("Whether issue is in both channels or one not stated")
    if re.search(r'pal|audioreach|adsp|agm', combined):
        if not re.search(r'firmware|\.bin|adsp.*version', combined):
            gaps.append("ADSP firmware version not specified")
    if re.search(r'startup|boot|enumerat', combined):
        if not re.search(r'systemd|service|journal', combined):
            gaps.append("systemd service startup logs not provided")
    return gaps


# ---------------------------------------------------------------------------
# Proposal renderer
# ---------------------------------------------------------------------------

def render_proposal(issue: str, goal: str) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    types = detect_types(issue, goal)
    components = detect_components(issue, goal)
    platform = detect_platform(issue, goal)
    gaps = detect_gaps(issue, goal, platform)
    diag_hints = detect_diagnostics(issue)

    lines = []

    # Header
    lines += [
        BOLD("═" * 72),
        BOLD("  PipeWire Enhancement Proposal"),
        DIM(f"  Generated: {now}"),
        BOLD("═" * 72),
        "",
    ]

    # Input echo
    lines += [
        BOLD("── Input ──────────────────────────────────────────────────────────"),
        f"  Issue : {issue}",
        f"  Goal  : {goal}",
        "",
    ]

    # 1. Enhancement Summary
    lines += [
        BOLD(CYAN("1. Enhancement Summary")),
        "─" * 72,
    ]
    summary = _build_summary(issue, goal, platform)
    lines += [textwrap.fill(summary, width=70, initial_indent="  ",
                            subsequent_indent="  "), ""]

    # 2. Classification
    lines += [BOLD(CYAN("2. Classification")), "─" * 72]
    for t in types:
        lines.append(f"  ✓  {t}. {ENHANCEMENT_TYPES[t]}")
    lines.append("")

    # 3. Affected Components
    lines += [BOLD(CYAN("3. Affected Components")), "─" * 72]
    lines.append(f"  {'Component':<35} {'Sub-component':<38} {'Change'}")
    lines.append("  " + "─" * 85)
    for comp, sub, change in components:
        lines.append(f"  {comp:<35} {sub:<38} {change}")
    lines.append("")

    # 4. Gap Analysis
    lines += [BOLD(CYAN("4. Gap Analysis")), "─" * 72]
    if gaps:
        for g in gaps:
            lines.append(f"  ⚠  {g}")
    else:
        lines.append("  ✓  All key fields provided — no critical gaps identified.")
    lines.append("")

    # 5. Architecture & Design Notes
    lines += [BOLD(CYAN("5. Architecture & Design Notes")), "─" * 72]
    arch_notes = _build_arch_notes(issue, goal, platform, components)
    for note in arch_notes:
        lines.append(f"  {note}")
    lines.append("")

    # 6. Implementation Plan
    lines += [BOLD(CYAN("6. Implementation Plan")), "─" * 72]
    plan = _build_impl_plan(issue, goal, components)
    lines.append(f"  {'Step':<5} {'Area':<28} {'Task':<38} {'Effort'}")
    lines.append("  " + "─" * 80)
    for step in plan:
        lines.append(f"  {step[0]:<5} {step[1]:<28} {step[2]:<38} {step[3]}")
    lines.append("")

    # 7. Test & Validation Plan
    lines += [BOLD(CYAN("7. Test & Validation Plan")), "─" * 72]
    tests = _build_test_plan(issue, goal, platform)
    for t in tests:
        lines.append(f"  • {t}")
    if diag_hints:
        lines += ["", DIM("  Diagnostic commands to run first:")]
        for cmd in diag_hints:
            lines.append(DIM(f"    $ {cmd}"))
    lines.append("")

    # 8. Documentation Tasks
    lines += [BOLD(CYAN("8. Documentation Tasks")), "─" * 72]
    docs = _build_doc_tasks(issue, goal)
    for d in docs:
        lines.append(f"  • {d}")
    lines.append("")

    # 9. Open Questions & Risks
    lines += [BOLD(CYAN("9. Open Questions & Risks")), "─" * 72]
    risks = _build_risks(issue, goal, platform, gaps)
    for r in risks:
        lines.append(f"  ? {r}")
    lines.append("")

    # 10. Acceptance Criteria
    lines += [BOLD(CYAN("10. Acceptance Criteria")), "─" * 72]
    criteria = _build_criteria(issue, goal, platform)
    for c in criteria:
        lines.append(f"  ✓  {c}")
    lines.append("")

    # Platform note
    if platform:
        lines += [
            DIM("── Platform context ───────────────────────────────────────────────"),
            DIM(f"  Platform : {platform['name']}"),
            DIM(f"  Stack    : {platform['stack']}"),
            DIM(f"  Configs  : {', '.join(platform['configs'])}"),
            "",
        ]

    lines.append(BOLD("═" * 72))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------

def _build_summary(issue: str, goal: str, platform: Optional[dict]) -> str:
    plat_str = f" on {platform['name']} ({platform['stack']})" if platform else ""
    return (
        f"The request concerns: {issue.rstrip('.')}. "
        f"The desired outcome is: {goal.rstrip('.')}. "
        f"This affects the PipeWire / Qualcomm QLI audio stack{plat_str} "
        f"and requires investigation and/or modification of the relevant "
        f"component layers identified below."
    )


def _build_arch_notes(issue: str, goal: str, platform: Optional[dict],
                      components: list) -> list:
    combined = (issue + " " + goal).lower()
    notes = []

    if re.search(r'glitch|tick|pop|crackle', combined):
        notes += [
            "*(hypothesis)* The tick is most likely caused by one of:",
            "  1. SPA/ALSA underrun during first buffer cycle before DSP graph ramps",
            "  2. PAL stream open triggering codec pop without software mute ramp",
            "  3. WirePlumber activating node before ADSP graph is stable",
            "",
            "Proposed mitigations to evaluate in order:",
            "  1. Add pre-roll silent buffer in spa.alsa",
            "  2. Enable codec pop-suppression via PAL stream attributes",
            "  3. Add WirePlumber activation delay tied to PAL ready event",
        ]
    elif re.search(r'startup|enumerat|missing|not found', combined):
        notes += [
            "*(hypothesis)* Device not appearing is likely caused by one of:",
            "  1. remoteproc / modem not started before PipeWire/WirePlumber",
            "  2. ADSP firmware not loaded at boot",
            "  3. Audio group permissions missing for the PipeWire process",
            "  4. D-Bus socket not available at WirePlumber startup",
            "",
            "Proposed fix: add systemd After= / Wants= dependencies and",
            "verify remoteproc state before WirePlumber starts.",
        ]
    elif re.search(r'ssmd|multi.device', combined):
        notes += [
            "SSMD requires QLI 2.x and Config 2 topology on most platforms.",
            "Data flow: PipeWire node → pipewire-pal-plugin → PAL multi-device",
            "usecase → AudioReach SSMD graph → multiple codec outputs.",
            "",
            "Key change: PAL resourcemanager.xml must define the multi-device",
            "usecase. WirePlumber policy must link one source to multiple sinks.",
        ]
    elif re.search(r'latency|performance|cpu', combined):
        notes += [
            "Latency is controlled by the PipeWire quantum (buffer size).",
            "Lower quantum = lower latency but higher CPU / xrun risk.",
            "For DSP offload paths, PAL stream attributes control ADSP buffer depth.",
            "",
            "Proposed approach: profile with pw-top, then tune quantum and",
            "ALSA period size in spa.alsa configuration.",
        ]
    elif re.search(r'routing|policy|sink|source', combined):
        notes += [
            "WirePlumber controls default sink/source selection and link policy.",
            "Changes are made in Lua configuration under /etc/wireplumber/.",
            "PipeWire Core manages the actual link objects between nodes.",
        ]
    elif re.search(r'document', combined):
        notes += [
            "Documentation changes do not affect runtime behaviour.",
            "Identify the target audience (developer / integrator / end-user)",
            "and the documentation system in use (DragonWing Docs / GitHub wiki).",
        ]
    else:
        notes += [
            "Detailed architecture notes require more context.",
            "Provide PipeWire/WirePlumber versions and logs to refine this section.",
        ]

    return notes


def _build_impl_plan(issue: str, goal: str, components: list) -> list:
    combined = (issue + " " + goal).lower()
    plan = []

    if re.search(r'glitch|tick|pop|crackle', combined):
        plan = [
            (1, "SPA",         "Add pre-roll silent buffer in spa.alsa",         "M"),
            (2, "PAL",         "Enable codec pop-suppression stream attribute",   "S"),
            (3, "WirePlumber", "Add PAL-ready activation delay hook",             "M"),
            (4, "Test",        "Measure glitch with/without each fix on target",  "S"),
        ]
    elif re.search(r'startup|enumerat|missing', combined):
        plan = [
            (1, "Yocto",       "Add systemd After=/Wants= for remoteproc",        "S"),
            (2, "WirePlumber", "Add startup retry / wait-for-device logic",       "M"),
            (3, "Test",        "Verify device appears within 5s on cold boot",    "S"),
        ]
    elif re.search(r'ssmd|multi.device', combined):
        plan = [
            (1, "PAL",         "Define multi-device usecase in resourcemanager.xml", "M"),
            (2, "AudioReach",  "Configure SSMD topology in .bin",                 "L"),
            (3, "WirePlumber", "Add multi-sink linking policy in Lua",             "M"),
            (4, "Test",        "Verify simultaneous output on 2+ devices",         "M"),
        ]
    elif re.search(r'latency|performance', combined):
        plan = [
            (1, "SPA",         "Profile spa.alsa buffer / period size",            "S"),
            (2, "PipeWire Core","Tune quantum for target latency",                 "S"),
            (3, "PAL",         "Tune ADSP buffer depth via stream attributes",     "M"),
            (4, "Test",        "Measure round-trip latency before/after",          "S"),
        ]
    elif re.search(r'document', combined):
        plan = [
            (1, "Documentation","Draft new section / update existing page",        "M"),
            (2, "Review",      "Technical review by component owner",              "S"),
            (3, "Publish",     "Merge and publish to documentation system",        "S"),
        ]
    else:
        for i, (comp, sub, _) in enumerate(components[:4], 1):
            plan.append((i, comp, f"Investigate / modify: {sub[:35]}", "M"))

    return plan


def _build_test_plan(issue: str, goal: str, platform: Optional[dict]) -> list:
    combined = (issue + " " + goal).lower()
    plat = platform["name"] if platform else "target platform"
    tests = []

    if re.search(r'glitch|tick|pop|crackle|quality', combined):
        tests += [
            f"Playback test: pw-play 48kHz/16-bit stereo WAV on {plat} — no audible glitch",
            f"Playback test: pw-play 44.1kHz/24-bit stereo WAV on {plat}",
            "GStreamer pipeline test: gst-launch-1.0 audiotestsrc ! pipewiresink",
            "Regression: arecord/aplay direct ALSA path — no regression",
            "Stress test: 100 consecutive play/stop cycles — no xruns",
            "pw-top: verify zero xruns during first 500ms of playback",
        ]
    elif re.search(r'startup|enumerat|missing', combined):
        tests += [
            f"Cold boot test: device appears in pw-cli ls Device within 5s on {plat}",
            "Warm reboot test: device re-appears after systemctl restart pipewire",
            "aplay -l: ALSA card visible before PipeWire starts",
            "Stress test: 10 consecutive reboots — device always enumerated",
        ]
    elif re.search(r'ssmd|multi.device', combined):
        tests += [
            f"SSMD test: simultaneous playback to 2 output devices on {plat}",
            "Verify audio on both devices with no dropout",
            "Regression: single-device playback still works",
            "WirePlumber policy test: correct device selected on connect/disconnect",
        ]
    elif re.search(r'latency|performance', combined):
        tests += [
            "Measure round-trip latency with jack_iodelay or similar",
            "pw-top: CPU usage < baseline + 5% at target quantum",
            "Stress test: 1 hour continuous playback — no xruns",
            "Regression: default quantum path unaffected",
        ]
    elif re.search(r'document', combined):
        tests += [
            "Technical review by at least one component owner",
            "Verify all command examples work on target platform",
            "Peer review for accuracy and completeness",
        ]
    else:
        tests += [
            f"Functional test on {plat}: verify enhancement works as described",
            "Regression test: existing audio paths unaffected",
            "Stress test: 1 hour continuous operation",
        ]

    return tests


def _build_doc_tasks(issue: str, goal: str) -> list:
    combined = (issue + " " + goal).lower()
    tasks = []

    if re.search(r'ssmd', combined):
        tasks += [
            "New section: 'SSMD (Single Stream Multi Device) Playback'",
            "Add command examples: pw-play with multiple sinks, wpctl routing",
            "Add topology diagram: PAL → AudioReach SSMD graph",
            "Add troubleshooting: common SSMD setup errors",
        ]
    elif re.search(r'config 1|config 2|topology', combined):
        tasks += [
            "New section: 'Audio Configuration: Config 1 vs Config 2'",
            "Add comparison table (features, power, complexity, use-cases)",
            "Add migration guide: Config 1 → Config 2",
            "Add platform availability table",
        ]
    elif re.search(r'glitch|tick|quality', combined):
        tasks += [
            "Update troubleshooting guide: audio glitch at playback start/end",
            "Document pre-roll buffer configuration option",
            "Add diagnostic steps to audio quality section",
        ]
    elif re.search(r'startup|enumerat', combined):
        tasks += [
            "Update troubleshooting guide: device not enumerated at startup",
            "Document systemd service ordering requirements",
            "Add remoteproc/ADSP startup dependency notes",
        ]
    else:
        tasks += [
            "Update relevant component documentation",
            "Add change to release notes / changelog",
        ]

    tasks.append("Update CHANGELOG.md with version bump")
    return tasks


def _build_risks(issue: str, goal: str, platform: Optional[dict],
                 gaps: list) -> list:
    combined = (issue + " " + goal).lower()
    risks = []

    if gaps:
        risks.append(f"Missing information ({len(gaps)} gaps) may require rework after clarification")

    if re.search(r'glitch|tick|pop', combined):
        risks += [
            "*(hypothesis)* Root cause may differ between QLI 1.x and QLI 2.x paths",
            "Pre-roll buffer change may increase startup latency — measure impact",
            "Codec pop-suppression may not be available on all platforms",
        ]
    if re.search(r'pal|audioreach|adsp', combined):
        risks += [
            "PAL / ADSP changes require firmware rebuild and re-validation",
            "Changes to PAL stream attributes may affect other usecases",
        ]
    if re.search(r'wireplumber|policy', combined):
        risks += [
            "WirePlumber policy changes may affect device selection on other platforms",
            "Lua configuration changes require WirePlumber restart to take effect",
        ]
    if not platform:
        risks.append("Platform not specified — proposal may need adjustment per target")

    if not risks:
        risks.append("No major risks identified at this stage — refine after gap analysis")

    return risks


def _build_criteria(issue: str, goal: str, platform: Optional[dict]) -> list:
    combined = (issue + " " + goal).lower()
    plat = platform["name"] if platform else "target platform"
    criteria = []

    if re.search(r'glitch|tick|pop|crackle', combined):
        criteria += [
            f"No audible glitch on pw-play 48kHz/16-bit stereo WAV on {plat}",
            "Zero xruns reported by pw-top during first 500ms of playback",
            "No regression on GStreamer pipeline or arecord/aplay path",
            "Fix verified on at least 2 consecutive software builds",
        ]
    elif re.search(r'startup|enumerat|missing', combined):
        criteria += [
            f"Device appears in pw-cli ls Device within 5s on cold boot on {plat}",
            "No regression on warm reboot",
            "Verified across 10 consecutive boot cycles",
        ]
    elif re.search(r'ssmd|multi.device', combined):
        criteria += [
            f"Simultaneous audio output to 2+ devices verified on {plat}",
            "No dropout or glitch during SSMD playback",
            "Single-device playback regression-free",
        ]
    elif re.search(r'latency|performance', combined):
        criteria += [
            "Round-trip latency meets target (specify in ms)",
            "CPU usage within 5% of baseline",
            "Zero xruns in 1-hour stress test",
        ]
    elif re.search(r'document', combined):
        criteria += [
            "Documentation section published and linked from main guide",
            "All command examples verified on hardware",
            "Reviewed and approved by component owner",
        ]
    else:
        criteria += [
            f"Enhancement works as described on {plat}",
            "No regression on existing audio paths",
            "Code reviewed and merged",
        ]

    return criteria


# ---------------------------------------------------------------------------
# Conversational input
# ---------------------------------------------------------------------------

def ask_issue_and_goal() -> tuple:
    """Prompt the user for issue and goal in a natural conversational way."""
    print()
    print(BOLD("╔══════════════════════════════════════════════════════════════════╗"))
    print(BOLD("║         PipeWire Enhancement Proposal Generator                 ║"))
    print(BOLD("╚══════════════════════════════════════════════════════════════════╝"))
    print()
    print("  Describe your issue and what you want to build.")
    print("  The more detail you give, the more accurate the proposal.")
    print()

    print(BOLD("  What issue are you seeing?"))
    print(DIM("  (e.g. 'Audio glitch at playback start on IQ9075 QLI 2.x with pw-play')"))
    issue = input("  ▶ ").strip()
    while not issue:
        print(RED("  Please describe the issue."))
        issue = input("  ▶ ").strip()

    print()
    print(BOLD("  What do you want to build / achieve?"))
    print(DIM("  (e.g. 'Eliminate the tick without regressing other audio paths')"))
    goal = input("  ▶ ").strip()
    while not goal:
        print(RED("  Please describe your goal."))
        goal = input("  ▶ ").strip()

    print()
    return issue, goal


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analyze_enhancement",
        description="PipeWire Enhancement Proposal Generator — describe your issue and goal, get a full proposal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Conversational (recommended):
              python3 analyze_enhancement.py

              # One-liner:
              python3 analyze_enhancement.py \\
                  --issue "Audio glitch at playback start on IQ9075 QLI 2.x" \\
                  --goal  "Eliminate the tick without regressing other paths"

              # From a text file:
              python3 analyze_enhancement.py --from-file my_issue.txt

              # Save proposal to file:
              python3 analyze_enhancement.py --no-color > proposal.md

              # List known platforms:
              python3 analyze_enhancement.py --list-platforms
        """),
    )
    p.add_argument("--issue",    metavar="TEXT", help="Describe the issue you are seeing")
    p.add_argument("--goal",     metavar="TEXT", help="Describe what you want to build or achieve")
    p.add_argument("--from-file",metavar="FILE",
                   help="Read issue and goal from a text file (first line = issue, second = goal)")
    p.add_argument("--no-color", action="store_true", help="Disable ANSI colour (for file output)")
    p.add_argument("--list-platforms", action="store_true", help="List known platforms and exit")
    p.add_argument("--list-types",     action="store_true", help="List enhancement types and exit")
    return p


def main() -> None:
    global USE_COLOR
    parser = build_parser()
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        USE_COLOR = False

    if args.list_platforms:
        print("\nKnown platforms:")
        for info in PLATFORMS.values():
            print(f"  {info['name']:<20} {info['stack']:<20} configs: {', '.join(info['configs'])}")
        return

    if args.list_types:
        print("\nEnhancement types:")
        for num, name in ENHANCEMENT_TYPES.items():
            print(f"  {num:>2}. {name}")
        return

    if args.from_file:
        import pathlib
        lines = pathlib.Path(args.from_file).read_text().strip().splitlines()
        issue = lines[0].strip() if lines else ""
        goal  = lines[1].strip() if len(lines) > 1 else "Improve the current behaviour"
    elif args.issue and args.goal:
        issue = args.issue
        goal  = args.goal
    elif args.issue:
        issue = args.issue
        goal  = "Improve the current behaviour"
    else:
        # Conversational mode
        issue, goal = ask_issue_and_goal()

    print(render_proposal(issue, goal))


if __name__ == "__main__":
    main()
