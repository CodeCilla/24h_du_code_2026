#!/usr/bin/env python3
"""
Simulateur du processeur Nano RISC 8
Lit un fichier .bin et simule l'exécution instruction par instruction.
Produit un rapport JSON avec état registres, stack, cycles à chaque étape.

Usage:
    python3 simulator.py programme.bin             # affiche rapport JSON
    python3 simulator.py programme.bin --html      # ouvre interface web
    python3 simulator.py programme.bin -o rapport.json
"""

import sys
import json
import argparse
import os

# ─── Constantes ────────────────────────────────────────────────────────────────
MAX_CYCLES  = 100_000   # garde-fou anti-boucle infinie
RAM_SIZE    = 256

# ─── Décodage des instructions ─────────────────────────────────────────────────

def reg_name(n):
    return f"R{n}"

def decode(memory, pc):
    """
    Décode l'instruction à l'adresse pc.
    Retourne un dict avec : mnemonic, operands, size (octets), cycles
    """
    b0 = memory[pc]

    # ── Instructions 1 octet ──────────────────────────────────────────────────

    # RET : 10000000
    if b0 == 0b10000000:
        return dict(mnemonic="RET", operands=[], size=1, cycles=1)

    # PUSH Rx : 101000xx
    if (b0 & 0b11111100) == 0b10100000:
        return dict(mnemonic="PUSH", operands=[reg_name(b0 & 0b11)], size=1, cycles=1)

    # POP Rx : 011000xx
    if (b0 & 0b11111100) == 0b01100000:
        return dict(mnemonic="POP", operands=[reg_name(b0 & 0b11)], size=1, cycles=1)

    # OUT Rx : 111100xx
    if (b0 & 0b11111100) == 0b11110000:
        return dict(mnemonic="OUT", operands=[reg_name(b0 & 0b11)], size=1, cycles=1)

    # MOV Rx Ry : 0101xxyy
    if (b0 & 0b11110000) == 0b01010000:
        rx = (b0 >> 2) & 0b11
        ry =  b0       & 0b11
        return dict(mnemonic="MOV", operands=[reg_name(rx), reg_name(ry)], size=1, cycles=1)

    # SUB Rx Ry : 1101xxyy
    if (b0 & 0b11110000) == 0b11010000:
        rx = (b0 >> 2) & 0b11
        ry =  b0       & 0b11
        return dict(mnemonic="SUB", operands=[reg_name(rx), reg_name(ry)], size=1, cycles=1)

    # CMP Rx Ry : 0011xxyy
    if (b0 & 0b11110000) == 0b00110000:
        rx = (b0 >> 2) & 0b11
        ry =  b0       & 0b11
        return dict(mnemonic="CMP", operands=[reg_name(rx), reg_name(ry)], size=1, cycles=1)

    # ── Instructions 2 octets ─────────────────────────────────────────────────
    b1 = memory[pc + 1] if pc + 1 < len(memory) else 0

    # CALL : 00000000 aaaaaaaa
    if b0 == 0b00000000:
        return dict(mnemonic="CALL", operands=[b1], size=2, cycles=2)

    # JMP : 01000000 aaaaaaaa
    if b0 == 0b01000000:
        return dict(mnemonic="JMP", operands=[b1], size=2, cycles=2)

    # JLT : 11000000 aaaaaaaa
    if b0 == 0b11000000:
        return dict(mnemonic="JLT", operands=[b1], size=2, cycles=2)

    # JEQ : 00100000 aaaaaaaa
    if b0 == 0b00100000:
        return dict(mnemonic="JEQ", operands=[b1], size=2, cycles=2)

    # MOV Rx valeur : 111000xx vvvvvvvv
    if (b0 & 0b11111100) == 0b11100000:
        rx = b0 & 0b11
        return dict(mnemonic="MOV", operands=[reg_name(rx), b1], size=2, cycles=2)

    # SUB Rx valeur : 000100xx vvvvvvvv
    if (b0 & 0b11111100) == 0b00010000:
        rx = b0 & 0b11
        return dict(mnemonic="SUB", operands=[reg_name(rx), b1], size=2, cycles=2)

    # CMP Rx valeur : 100100xx vvvvvvvv
    if (b0 & 0b11111100) == 0b10010000:
        rx = b0 & 0b11
        return dict(mnemonic="CMP", operands=[reg_name(rx), b1], size=2, cycles=2)

    # LDR Rx Ry addr : 1011xxyy aaaaaaaa  (3 cycles)
    if (b0 & 0b11110000) == 0b10110000:
        rx = (b0 >> 2) & 0b11
        ry =  b0       & 0b11
        return dict(mnemonic="LDR", operands=[reg_name(rx), reg_name(ry), b1], size=2, cycles=3)

    # STR Rx Ry addr : 0111xxyy aaaaaaaa  (3 cycles)
    if (b0 & 0b11110000) == 0b01110000:
        rx = (b0 >> 2) & 0b11
        ry =  b0       & 0b11
        return dict(mnemonic="STR", operands=[reg_name(rx), reg_name(ry), b1], size=2, cycles=3)

    # TIM valeur : 11111000 mvvvvvvv
    if b0 == 0b11111000:
        return dict(mnemonic="TIM", operands=[b1], size=2, cycles=2)

    raise ValueError(f"Octet inconnu à PC={pc}: 0b{b0:08b} (0x{b0:02X})")


# ─── Simulateur ────────────────────────────────────────────────────────────────

def simulate(binary_data):
    memory = list(binary_data) + [0] * (RAM_SIZE - len(binary_data))

    regs   = [0, 0, 0, 0]   # R0..R3
    stack  = []              # valeurs empilées
    sp     = 255             # stack pointer
    pc     = 0
    flag_lt = False
    flag_eq = False
    total_cycles = 0
    steps = []
    output = []

    for _ in range(MAX_CYCLES):
        if pc >= len(binary_data):
            break

        instr = decode(memory, pc)
        mn  = instr["mnemonic"]
        ops = instr["operands"]
        total_cycles += instr["cycles"]

        # Snapshot avant exécution
        step = {
            "pc":     pc,
            "instr":  mn,
            "ops":    ops,
            "size":   instr["size"],
            "cycles": instr["cycles"],
            "total_cycles": total_cycles,
            "regs_before":  regs[:],
            "stack_before": stack[:],
            "flags_before": {"LT": flag_lt, "EQ": flag_eq},
            "output": None,
            "comment": ""
        }

        next_pc = pc + instr["size"]
        stop = False

        # ── Exécution ─────────────────────────────────────────────────────────

        if mn == "RET":
            if not stack:
                step["comment"] = "Pile vide → arrêt du programme"
                stop = True
            else:
                next_pc = stack.pop()
                sp = min(sp + 1, 255)
                step["comment"] = f"Retour à PC={next_pc}"

        elif mn == "PUSH":
            rx = int(ops[0][1])
            stack.append(regs[rx])
            sp = max(sp - 1, 0)
            step["comment"] = f"Empile {regs[rx]} (R{rx})"

        elif mn == "POP":
            rx = int(ops[0][1])
            regs[rx] = stack.pop()
            sp = min(sp + 1, 255)
            step["comment"] = f"Dépile {regs[rx]} → R{rx}"

        elif mn == "OUT":
            rx = int(ops[0][1])
            val = regs[rx]
            output.append(val)
            step["output"] = val
            # Décodage moteur : svvvsvvv
            left  = (val >> 4) & 0x0F
            right =  val       & 0x0F
            # Signe en complément à 2 sur 4 bits
            if left  >= 8: left  -= 16
            if right >= 8: right -= 16
            step["comment"] = f"OUT={val} → moteur gauche={left}, moteur droit={right}"

        elif mn == "MOV":
            rx = int(ops[0][1])
            if isinstance(ops[1], str):   # MOV Rx Ry
                ry = int(ops[1][1])
                regs[rx] = regs[ry]
                step["comment"] = f"R{rx} = R{ry} = {regs[rx]}"
            else:                          # MOV Rx valeur
                regs[rx] = ops[1]
                step["comment"] = f"R{rx} = {ops[1]}"

        elif mn == "SUB":
            rx = int(ops[0][1])
            if isinstance(ops[1], str):   # SUB Rx Ry
                ry = int(ops[1][1])
                regs[rx] = (regs[rx] - regs[ry]) & 0xFF
                step["comment"] = f"R{rx} -= R{ry} → {regs[rx]}"
            else:                          # SUB Rx valeur
                regs[rx] = (regs[rx] - ops[1]) & 0xFF
                step["comment"] = f"R{rx} -= {ops[1]} → {regs[rx]}"

        elif mn == "CMP":
            rx = int(ops[0][1])
            if isinstance(ops[1], str):   # CMP Rx Ry
                ry = int(ops[1][1])
                val = regs[ry]
            else:
                val = ops[1]
            flag_lt = regs[rx] < val
            flag_eq = regs[rx] == val
            step["comment"] = f"CMP R{rx}({regs[rx]}) vs {val} → LT={flag_lt}, EQ={flag_eq}"

        elif mn == "JMP":
            next_pc = ops[0]
            step["comment"] = f"Saut inconditionnel → PC={next_pc}"

        elif mn == "JEQ":
            if flag_eq:
                next_pc = ops[0]
                step["comment"] = f"EQ=True → saut vers PC={next_pc}"
            else:
                step["comment"] = f"EQ=False → pas de saut"

        elif mn == "JLT":
            if flag_lt:
                next_pc = ops[0]
                step["comment"] = f"LT=True → saut vers PC={next_pc}"
            else:
                step["comment"] = f"LT=False → pas de saut"

        elif mn == "CALL":
            stack.append(next_pc)
            sp = max(sp - 1, 0)
            next_pc = ops[0]
            step["comment"] = f"Appel fonction PC={next_pc}, adresse retour empilée={stack[-1]}"

        elif mn == "LDR":
            rx  = int(ops[0][1])
            ry  = int(ops[1][1])
            addr = (ops[2] + regs[ry]) & 0xFF
            regs[rx] = memory[addr]
            step["comment"] = f"R{rx} = RAM[{ops[2]}+R{ry}={addr}] = {regs[rx]}"

        elif mn == "STR":
            rx  = int(ops[0][1])
            ry  = int(ops[1][1])
            addr = (ops[2] + regs[ry]) & 0xFF
            memory[addr] = regs[rx]
            step["comment"] = f"RAM[{ops[2]}+R{ry}={addr}] = R{rx} = {regs[rx]}"

        elif mn == "TIM":
            val = ops[0]
            m   = (val >> 7) & 1
            v   = val & 0x7F
            mult = 100 if m else 1
            ms  = mult * (v + 1)
            step["comment"] = f"Pause {ms} ms"

        # Snapshot après
        step["regs_after"]  = regs[:]
        step["stack_after"] = stack[:]
        step["flags_after"] = {"LT": flag_lt, "EQ": flag_eq}
        step["sp"] = sp
        steps.append(step)

        pc = next_pc
        if stop:
            break

    return {
        "steps":        steps,
        "total_cycles": total_cycles,
        "output":       output,
        "final_regs":   regs,
        "final_stack":  stack,
    }


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simulateur Nano RISC 8")
    parser.add_argument("binary", help="Fichier .bin à simuler")
    parser.add_argument("-o", "--output", help="Fichier JSON de rapport (optionnel)")
    parser.add_argument("--html", action="store_true", help="Ouvrir l'interface web")
    args = parser.parse_args()

    with open(args.binary, "rb") as f:
        data = f.read()

    print(f"Simulation de '{args.binary}' ({len(data)} octets)...")
    report = simulate(data)

    print(f"✅ {len(report['steps'])} instructions exécutées")
    print(f"   Cycles totaux : {report['total_cycles']}")
    print(f"   Sorties OUT   : {report['output']}")
    print(f"   Registres finaux : {report['final_regs']}")

    report_json = json.dumps(report, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report_json)
        print(f"   Rapport JSON : {args.output}")

    if args.html:
        # Générer la page HTML et l'ouvrir
        html_path = args.binary.replace(".bin", "_sim.html")
        generate_html(report, html_path)
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(html_path)}")
        print(f"   Interface web : {html_path}")

    if not args.output and not args.html:
        print("\n--- Rapport JSON ---")
        print(report_json)

def generate_html(report, path):
    report_json = json.dumps(report)
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Nano RISC 8 — Simulateur</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: monospace; background: #0d1117; color: #e6edf3; min-height: 100vh; }}
    header {{ background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px; display: flex; align-items: center; gap: 16px; }}
    header h1 {{ font-size: 18px; color: #58a6ff; }}
    .badge {{ background: #1f6feb; color: #fff; border-radius: 12px; padding: 2px 10px; font-size: 12px; }}
    .layout {{ display: grid; grid-template-columns: 320px 1fr; height: calc(100vh - 61px); }}
    .sidebar {{ background: #161b22; border-right: 1px solid #30363d; display: flex; flex-direction: column; overflow: hidden; }}
    .panel-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: #8b949e; padding: 12px 16px 8px; border-bottom: 1px solid #21262d; }}
    .steps-list {{ flex: 1; overflow-y: auto; }}
    .step-item {{ padding: 8px 16px; cursor: pointer; border-left: 3px solid transparent; border-bottom: 1px solid #21262d; transition: background .1s; }}
    .step-item:hover {{ background: #1f2937; }}
    .step-item.active {{ border-left-color: #58a6ff; background: #1f2937; }}
    .step-item.has-out {{ border-left-color: #3fb950; }}
    .step-pc {{ color: #8b949e; font-size: 11px; }}
    .step-instr {{ color: #79c0ff; font-weight: bold; }}
    .step-comment {{ font-size: 11px; color: #8b949e; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .main {{ display: flex; flex-direction: column; overflow: hidden; }}
    .detail {{ flex: 1; padding: 20px 24px; overflow-y: auto; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px 16px; }}
    .card h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: #8b949e; margin-bottom: 10px; }}
    .reg-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .reg {{ display: flex; justify-content: space-between; align-items: center; background: #0d1117; border-radius: 4px; padding: 6px 10px; }}
    .reg-name {{ color: #ffa657; font-weight: bold; }}
    .reg-val {{ color: #3fb950; font-family: monospace; }}
    .reg-changed {{ background: #1a2a1a; border: 1px solid #3fb950; }}
    .stack-items {{ display: flex; flex-direction: column-reverse; gap: 4px; min-height: 40px; }}
    .stack-item {{ background: #0d1117; border-radius: 4px; padding: 4px 10px; color: #a5d6ff; font-size: 13px; }}
    .instr-box {{ background: #0d1117; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; }}
    .instr-line {{ font-size: 20px; color: #e6edf3; margin-bottom: 4px; }}
    .instr-line .mn {{ color: #ff7b72; font-weight: bold; }}
    .instr-line .op {{ color: #79c0ff; }}
    .instr-line .opv {{ color: #3fb950; }}
    .meta {{ display: flex; gap: 16px; font-size: 12px; color: #8b949e; }}
    .meta span {{ background: #21262d; padding: 2px 8px; border-radius: 4px; }}
    .comment-box {{ background: #161b22; border-left: 3px solid #58a6ff; padding: 10px 14px; font-size: 13px; color: #8b949e; margin-bottom: 12px; border-radius: 0 6px 6px 0; }}
    .flags {{ display: flex; gap: 8px; }}
    .flag {{ padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
    .flag.on  {{ background: #1a2a1a; color: #3fb950; border: 1px solid #3fb950; }}
    .flag.off {{ background: #21262d; color: #8b949e; border: 1px solid #30363d; }}
    .out-val {{ font-size: 24px; color: #3fb950; font-weight: bold; text-align: center; padding: 8px 0; }}
    .footer {{ background: #161b22; border-top: 1px solid #30363d; padding: 10px 24px; display: flex; gap: 20px; align-items: center; font-size: 12px; color: #8b949e; }}
    .footer button {{ background: #21262d; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px 16px; cursor: pointer; font-family: monospace; }}
    .footer button:hover {{ background: #30363d; }}
    .footer button:disabled {{ opacity: .4; cursor: default; }}
    .progress {{ flex: 1; background: #21262d; border-radius: 4px; height: 6px; }}
    .progress-bar {{ height: 100%; background: #58a6ff; border-radius: 4px; transition: width .2s; }}
</style>
</head>
<body>
<header>
    <h1>🤖 Nano RISC 8 — Simulateur</h1>
    <span class="badge" id="step-badge">Étape 0 / 0</span>
    <span class="badge" style="background:#3fb950">Cycles: <span id="cycle-count">0</span></span>
</header>
<div class="layout">
    <div class="sidebar">
        <div class="panel-title">Instructions</div>
        <div class="steps-list" id="steps-list"></div>
    </div>
    <div class="main">
        <div class="detail" id="detail"></div>
        <div class="footer">
            <button id="btn-prev" onclick="go(-1)">◀ Préc</button>
            <button id="btn-next" onclick="go(1)">Suiv ▶</button>
            <div class="progress"><div class="progress-bar" id="progress"></div></div>
            <span>OUT: <b id="out-list" style="color:#3fb950">—</b></span>
        </div>
    </div>
</div>
<script>
const R = {report_json};
const steps = R.steps;
let cur = 0;

function renderList() {{
    const el = document.getElementById('steps-list');
    el.innerHTML = steps.map((s, i) => {{
        const ops = s.ops.map(o => typeof o === 'string' ? o : o).join(' ');
        const cls = (s.output !== null ? 'has-out' : '') + (i === cur ? ' active' : '');
        return `<div class="step-item ${{cls}}" onclick="jump(${{i}})">
            <div class="step-pc">PC=${{String(s.pc).padStart(3,'0')}} · ${{s.size}}B · ${{s.cycles}}cyc</div>
            <div class="step-instr">${{s.instr}} ${{ops}}</div>
            <div class="step-comment">${{s.comment}}</div>
        </div>`;
    }}).join('');
    el.children[cur]?.scrollIntoView({{block:'nearest'}});
}}

function renderDetail() {{
    const s = steps[cur];
    if (!s) return;
    const regsHtml = ['R0','R1','R2','R3'].map((r,i) => {{
        const changed = s.regs_before[i] !== s.regs_after[i];
        return `<div class="reg ${{changed?'reg-changed':''}}">
            <span class="reg-name">${{r}}</span>
            <span class="reg-val">${{s.regs_after[i]}} <span style="color:#8b949e;font-size:11px">0x${{s.regs_after[i].toString(16).toUpperCase().padStart(2,'0')}}</span></span>
        </div>`;
    }}).join('');

    const stackHtml = s.stack_after.length
        ? s.stack_after.map(v => `<div class="stack-item">${{v}}</div>`).join('')
        : '<span style="color:#8b949e;font-size:12px">vide</span>';

    const ops = s.ops.map(o => `<span class="${{typeof o==='string'?'op':'opv'}}">${{o}}</span>`).join(' ');
    const outHtml = s.output !== null
        ? `<div class="card"><h3>Sortie OUT</h3><div class="out-val">${{s.output}}</div>
           <div style="font-size:12px;color:#8b949e;text-align:center">${{s.comment}}</div></div>`
        : '';

    document.getElementById('detail').innerHTML = `
        <div class="instr-box">
            <div class="instr-line"><span class="mn">${{s.instr}}</span> ${{ops}}</div>
            <div class="meta">
                <span>PC = ${{s.pc}}</span>
                <span>${{s.size}} octet${{s.size>1?'s':''}}</span>
                <span>${{s.cycles}} cycle${{s.cycles>1?'s':''}}</span>
                <span>Total : ${{s.total_cycles}} cycles</span>
            </div>
        </div>
        <div class="comment-box">${{s.comment || '—'}}</div>
        <div class="row">
            <div class="card"><h3>Registres</h3><div class="reg-grid">${{regsHtml}}</div></div>
            <div class="card"><h3>Flags</h3><div class="flags">
                <div class="flag ${{s.flags_after.LT?'on':'off'}}">LT = ${{s.flags_after.LT?1:0}}</div>
                <div class="flag ${{s.flags_after.EQ?'on':'off'}}">EQ = ${{s.flags_after.EQ?1:0}}</div>
            </div>
            <div style="margin-top:12px"><h3 style="margin-bottom:8px">SP = ${{s.sp}}</h3></div>
            </div>
        </div>
        <div class="row">
            <div class="card"><h3>Stack</h3><div class="stack-items">${{stackHtml}}</div></div>
            ${{outHtml}}
        </div>
    `;

    // header
    document.getElementById('step-badge').textContent = `Étape ${{cur+1}} / ${{steps.length}}`;
    document.getElementById('cycle-count').textContent = s.total_cycles;
    document.getElementById('progress').style.width = `${{(cur+1)/steps.length*100}}%`;
    document.getElementById('btn-prev').disabled = cur === 0;
    document.getElementById('btn-next').disabled = cur === steps.length - 1;

    // outputs so far
    const outs = steps.slice(0, cur+1).filter(x=>x.output!==null).map(x=>x.output);
    document.getElementById('out-list').textContent = outs.length ? outs.join(', ') : '—';
}}

function jump(i) {{ cur = i; renderList(); renderDetail(); }}
function go(d) {{ jump(Math.max(0, Math.min(steps.length-1, cur+d))); }}

document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowRight') go(1);
    if (e.key === 'ArrowLeft')  go(-1);
}});

renderList();
renderDetail();
</script>
</body>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
