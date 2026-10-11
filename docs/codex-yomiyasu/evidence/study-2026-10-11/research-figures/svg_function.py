def svg(fig):
    """Deterministic SVG with real text, explicit legend and non-overlapping DAG boxes."""
    layers = _layers(fig)
    box_w, gap, margin = 310, 70, 85
    width = max(850, 2 * margin + max(len(row) for row in layers) * (box_w + gap) - gap)
    title_lines = wrap(fig["title"], 70)
    coords, labels, ypos = {}, {}, 75 + 24 * len(title_lines)
    lane_order = {"baseline": 0, "shared": 1, "proposal": 2}
    for layer in layers:
        layer = sorted(layer, key=lambda n: (lane_order[n["lane"]], n["id"]))
        heights = []
        for node in layer:
            title, detail = wrap(node["label"], 30), wrap(node["detail"], 40)
            height = 52 + 24 * len(title) + 19 * len(detail)
            labels[node["id"]] = (title, detail)
            heights.append(height)
        row_width = len(layer) * (box_w + gap) - gap
        start = (width - row_width) / 2
        for index, node in enumerate(layer):
            coords[node["id"]] = (start + index * (box_w + gap), ypos, box_w, heights[index])
        ypos += max(heights) + 126
    height = ypos + 20
    ranks = {node["id"]: index for index, row in enumerate(layers) for node in row}
    bypasses = [i for i, e in enumerate(fig["edges"]) if e["kind"] != "feedback" and ranks[e["to"]] - ranks[e["from"]] > 1]
    base_width = width
    width += 270 + 90 * len(bypasses) if bypasses else 0
    title = html.escape(fig["title"])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
           f'<title id="title">{title}</title>', f'<desc id="desc">{html.escape(fig["alt_text"])}</desc>',
           '<defs><marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><path d="M0,0 L9,3.5 L0,7" fill="#333"/></marker></defs>',
           f'<rect width="{width}" height="{height}" fill="white"/>',
           '<g font-family="Noto Sans CJK JP, Meiryo, sans-serif" fill="#161616">',
           *[f'<text x="{width / 2}" y="{35+24*i}" text-anchor="middle" font-size="20" font-weight="bold">{html.escape(t)}</text>' for i,t in enumerate(title_lines)],
           f'<text x="{width / 2}" y="{51+24*len(title_lines)}" text-anchor="middle" font-size="13">概念図：実線は処理の流れ、破線はフィードバック。性能の実測図ではありません。</text>']
    # Arrows first, so a box never loses text to an overdrawn arrow.
    for edge_index, edge in enumerate(fig["edges"]):
        x1, y1, w1, h1 = coords[edge["from"]]
        x2, y2, w2, h2 = coords[edge["to"]]
        feedback = edge["kind"] == "feedback"
        bypass = edge_index in bypasses
        if bypass:
            side = 30 if x1 + w1 / 2 < base_width / 2 - 40 else base_width + 30 + 90 * bypasses.index(edge_index)
            path = f'M{x1+w1/2},{y1+h1} V{y1+h1+25} H{side} V{y2-28} H{x2+w2/2} V{y2-4}'
            lx, ly = side + 10, (y1+h1+y2)/2
        elif feedback:
            side = width - 30
            path = f'M{x1+w1},{y1+h1/2} H{side} V{y2+h2/2} H{x2+w2}'
            lx, ly = side - 12, (y1+h1/2+y2+h2/2)/2
        else:
            mid = (y1 + h1 + y2) / 2
            path = f'M{x1+w1/2},{y1+h1} V{mid} H{x2+w2/2} V{y2-4}'
            lx, ly = (x1+w1/2+x2+w2/2)/2, mid - 17
        dash = ' stroke-dasharray="6 5"' if feedback else ''
        out.append(f'<path d="{path}" fill="none" stroke="#333" stroke-width="1.6"{dash} marker-end="url(#arrow)"/>')
        label_lines = wrap(edge["label"], 28)
        # A background rect, instead of paint-order text strokes, also works in CairoSVG.
        label_width = max(sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in line) for line in label_lines) * 6.5 + 10
        label_x = lx - 5 if bypass else (lx - label_width + 5 if feedback else lx - label_width / 2)
        out.append(f'<rect x="{label_x}" y="{ly-13}" width="{label_width}" height="{16*len(label_lines)+4}" fill="white"/>')
        for j, label in enumerate(label_lines):
            anchor = 'start' if bypass else ('end' if feedback else 'middle')
            out.append(f'<text x="{lx}" y="{ly+16*j}" font-size="12" text-anchor="{anchor}">{html.escape(label)}</text>')
    for layer in layers:
        for node in layer:
            x, y, w, h = coords[node["id"]]
            title_lines, detail_lines = labels[node["id"]]
            change = {"unchanged": "維持", "added": "追加", "modified": "変更"}[node["change"]]
            lane = {"baseline": "既存法", "proposal": "提案法", "shared": "共通"}[node["lane"]]
            out += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#f6f6f6" stroke="#333" stroke-width="{2.4 if node["change"] != "unchanged" else 1.1}"/>',
                    f'<text x="{x+14}" y="{y+22}" font-size="12">{lane}・{change}　{html.escape(node["component_id"] or node["id"])}</text>']
            yy = y + 47
            for line in title_lines:
                out.append(f'<text x="{x+14}" y="{yy}" font-size="17" font-weight="bold">{html.escape(line)}</text>')
                yy += 24
            for line in detail_lines:
                out.append(f'<text x="{x+14}" y="{yy}" font-size="13">{html.escape(line)}</text>')
                yy += 19
    out += ['</g>', '</svg>']
    return "\n".join(out).encode("utf-8")
