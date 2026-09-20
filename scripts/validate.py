"""Read-only static checks; optional KiCad PCB and schematic MCU cross-checks."""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SHIELD = ROOT / "config/boards/shields/circa40plus"
ORDER = [1, 2, 3, 4, 5, 6, 45, 22, 23, 24, 25, 26, 27,
         7, 8, 9, 10, 11, 12, 46, 28, 29, 30, 31, 32,
         13, 14, 15, 16, 17, 43, 33, 34, 35, 36, 37, 38,
         18, 19, 20, 21, 44, 49, 39, 40, 41, 42]
PINS = {
    "L": {"col": [(0, 2), (0, 3), (0, 28), (0, 29), (0, 15), (0, 19)],
          "row": [(1, 1), (1, 7), (1, 5), (1, 3)]},
    "R": {"col": [(0, 2), (0, 3), (0, 28), (0, 29), (0, 4), (0, 5)],
          "row": [(1, 11), (1, 12), (1, 13), (1, 14)]},
}
MCU_PADS = {"L": {"col": [1, 2, 3, 4, 15, 16], "row": [17, 23, 22, 21]},
            "R": {"col": [1, 2, 3, 4, 5, 6], "row": [7, 8, 9, 10]}}


def text(path):
    return path.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path)
    parser.add_argument("--netlist", type=Path)
    args = parser.parse_args()
    common = text(SHIELD / "circa40plus.dtsi")
    transform = [tuple(map(int, p)) for p in re.findall(r"RC\((\d+),\s*(\d+)\)", common)]
    assert len(transform) == len(set(transform)) == len(ORDER) == 47
    assert all(0 <= r < 4 and 0 <= c < 12 for r, c in transform)
    assert sum(c < 6 for r, c in transform) == 24
    assert sum(c >= 6 for r, c in transform) == 23
    assert (3, 11) not in transform
    assert 'diode-direction = "col2row"' in common

    layout = json.loads(text(ROOT / "config/circa40plus.json"))["layouts"]["default_layout"]["layout"]
    assert [key["label"] for key in layout] == [f"SW{n}" for n in ORDER]
    assert len({(key["row"], key["col"]) for key in layout}) == 47
    assert layout == sorted(layout, key=lambda key: (key["row"], key["col"]))
    widths = {7: 1.25, 13: 1.75, 32: 1.75, 38: 1.25, 49: 1.5}
    for key, number in zip(layout, ORDER):
        assert key.get("w", 1) == widths.get(number, 1)
    for index, a in enumerate(layout):
        for b in layout[index + 1:]:
            assert not (min(a["x"] + a.get("w", 1), b["x"] + b.get("w", 1)) > max(a["x"], b["x"]) and
                        min(a["y"] + 1, b["y"] + 1) > max(a["y"], b["y"])), (a, b)
    print("PASS: editor layout has 47 ordered keys, correct widths and no overlaps")

    keymap = text(ROOT / "config/circa40plus.keymap")
    layers = re.findall(r"bindings\s*=\s*<([^>]+)>;", keymap)
    assert len(layers) == 3
    for layer in layers:
        assert len(re.findall(r"&\w+", layer)) == 47
    for side, name in [("L", "left"), ("R", "right")]:
        overlay = text(SHIELD / f"circa40plus_{name}.overlay")
        for kind in ["row", "col"]:
            prop = re.search(rf"{kind}-gpios\s*=([^;]+);", overlay).group(1)
            actual = [tuple(map(int, p)) for p in re.findall(r"&gpio(\d)\s+(\d+)", prop)]
            assert actual == PINS[side][kind], (side, kind, actual)
        gpios = PINS[side]["row"] + PINS[side]["col"]
        assert len(set(gpios)) == 10
    right = text(SHIELD / "circa40plus_right.overlay")
    assert "col-offset = <6>" in right
    assert "<&gpio1 5 GPIO_ACTIVE_LOW>" in right
    assert "<&gpio1 15 (GPIO_ACTIVE_LOW | GPIO_PULL_UP)>" in right
    assert "NRF_PSEL(SPIM_SCK, 1, 3)" in right
    assert "NRF_PSEL(SPIM_MOSI, 1, 7)" in right and "NRF_PSEL(SPIM_MISO, 1, 7)" in right
    assert not set(PINS["R"]["row"] + PINS["R"]["col"]) & {(1, 3), (1, 5), (1, 7), (1, 15)}
    print("PASS: 47 unique matrix positions, 3 x 47 bindings, GPIOs, sensor pins")

    if args.pcb:
        import pcbnew
        board = pcbnew.LoadBoard(str(args.pcb))
        fps = {f.GetReference(): f for f in board.GetFootprints()}

        def pads(ref):
            return {p.GetNumber(): p.GetNetname() for p in fps[ref].Pads() if p.GetNumber()}

        switches = [ref for ref in fps if ref.startswith("SW") and
                    re.fullmatch(r"Col\d_[LR]", pads(ref).get("1", ""))]
        assert set(switches) == {f"SW{n}" for n in ORDER}
        physical_order = sorted(switches, key=lambda ref: (
            round(pcbnew.ToMM(fps[ref].GetPosition().y), 2),
            pcbnew.ToMM(fps[ref].GetPosition().x)))
        assert physical_order == [f"SW{n}" for n in ORDER]
        anchor = fps["SW1"].GetPosition()
        origin_x = pcbnew.ToMM(anchor.x) - 17 / 2
        origin_y = pcbnew.ToMM(anchor.y) - 17 / 2
        for key in layout:
            point = fps[key["label"]].GetPosition()
            expected_x = origin_x + (key["x"] + key.get("w", 1) / 2) * 17
            expected_y = origin_y + (key["y"] + 0.5) * 17
            assert abs(pcbnew.ToMM(point.x) - expected_x) < 0.001, key
            assert abs(pcbnew.ToMM(point.y) - expected_y) < 0.001, key
        print("PASS: all 47 editor key centers match the PCB at 17 mm pitch (within 0.001 mm)")
        for number, rc in zip(ORDER, transform):
            ref = f"SW{number}"
            sw = pads(ref)
            match = re.fullmatch(r"Col(\d)_([LR])", sw["1"])
            col, side = int(match[1]), match[2]
            diodes = [d for d in fps if re.fullmatch(r"D\d+", d) and pads(d).get("2") == sw["2"]]
            assert len(diodes) == 1, (ref, diodes)
            row_net = pads(diodes[0])["1"]
            match_row = re.fullmatch(r"Row(\d)_" + side, row_net)
            assert match_row, (ref, row_net)
            actual = (int(match_row[1]), col + (6 if side == "R" else 0))
            assert actual == rc, (ref, actual, rc)
        for side, mcu in [("L", "Left-XiaoPlus1"), ("R", "U1")]:
            for kind, nums in MCU_PADS[side].items():
                for index, pad in enumerate(nums):
                    assert pads(mcu)[str(pad)] == f"{kind.title()}{index}_{side}"
        assert [pads("J1")[str(i)] for i in range(1, 7)] == [
            "GND_R", "MOTION_R", "SDIO_R", "CS_R", "SCLK_R", "3.3V_R"]
        assert {p: pads("U1")[p] for p in ["11", "21", "22", "23"]} == {
            "11": "MOTION_R", "21": "SCLK_R", "22": "CS_R", "23": "SDIO_R"}
        print("PASS: source PCB switch order, 47 diode paths, MCU nets and FFC")

    if args.netlist:
        nets = ET.parse(args.netlist).getroot().find("nets")
        by_pin = {(node.attrib["ref"], node.attrib["pin"]): (net.attrib["name"], node.attrib)
                  for net in nets for node in net.findall("node")}
        for side, ref in [("L", "Left-XiaoPlus1"), ("R", "U1")]:
            for kind, nums in MCU_PADS[side].items():
                for index, pad in enumerate(nums):
                    net, node = by_pin[(ref, str(pad))]
                    assert net == f"{kind.title()}{index}_{side}"
                    match = re.match(r"P(\d)\.(\d+)", node["pinfunction"])
                    assert tuple(map(int, match.groups())) == PINS[side][kind][index]
        for pad, net, gpio in [(11, "MOTION_R", (1, 15)), (21, "SCLK_R", (1, 3)),
                               (22, "CS_R", (1, 5)), (23, "SDIO_R", (1, 7))]:
            actual_net, node = by_pin[("U1", str(pad))]
            assert actual_net == net
            assert tuple(map(int, re.match(r"P(\d)\.(\d+)", node["pinfunction"]).groups())) == gpio
        print("PASS: schematic MCU pin functions match GPIO configuration")
    print("Static validation only; firmware compilation and hardware testing still required.")


if __name__ == "__main__":
    main()
