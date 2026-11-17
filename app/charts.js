// D3 chart library for the Streamlit dashboard. Each chart is drawn into its own iframe by charts.py,
// which sets window.SPEC and calls CHARTS[SPEC.type](root, SPEC). Charts redraw on resize; Streamlit sizes the
// iframe to its content (st.iframe height="content").
//
// Narrow screens (< NARROW_PX): row labels move onto their own line above the mark, values go to the right end
// of that line, and the marks use the full width.
(function () {
  const TEXT = "#f0efec", TEXT2 = "#c3c2b7", MUTED = "#898781", GRID = "#2c2c2a", AXIS = "#383835";
  const SURFACE = "#000000", EMPTY = "#262624";
  const NARROW_PX = 560;
  const fmtInt = d3.format(",");
  const pct1 = v => (v == null ? "—" : `${(+v).toFixed(1)}%`);
  const pct2 = v => (v == null ? "—" : `${(+v).toFixed(2)}%`);
  const isNarrow = root => root.clientWidth < NARROW_PX;

  // ---------------------------------------------------------------- tooltip
  const tip = d3.select("body").append("div").attr("class", "tip");
  function showTip(ev, html) { tip.html(html).style("opacity", 1); moveTip(ev); }
  function moveTip(ev) {
    const n = tip.node(), w = n.offsetWidth, h = n.offsetHeight;
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + w > window.innerWidth - 6) x = Math.max(6, ev.clientX - w - 14);
    if (y + h > window.innerHeight - 6) y = ev.clientY - h - 14;
    // Keep the whole tooltip inside the frame; the frame is tall enough for it (see reserveTipSpace).
    y = Math.max(6, Math.min(y, window.innerHeight - h - 6));
    tip.style("left", `${x}px`).style("top", `${y}px`);
  }
  function hideTip() { tip.style("opacity", 0); }
  // Every tooltip a chart can show, so the frame can be made tall enough for the tallest one.
  const tipSources = [];
  function hover(sel, html, group) {
    tipSources.push(() => sel.data().map(html));
    sel.on("mouseenter", function (ev, d) {
      if (group) group.classed("dim", o => o !== d);
      showTip(ev, html(d));
    }).on("mousemove", moveTip).on("mouseleave", () => {
      if (group) group.classed("dim", false);
      hideTip();
    });
  }
  const tipRows = rows => rows.map(([k, v]) => `<div class="tr"><span>${k}</span><b>${v}</b></div>`).join("");
  const tipHtml = (title, rows, note) =>
    `<div class="tt">${title}</div>${tipRows(rows || [])}${note ? `<div class="tn">${note}</div>` : ""}`;

  function textWidth(svg, text, size, weight) {
    const t = svg.append("text").attr("font-size", size).attr("font-weight", weight || 400).text(text);
    const w = t.node().getComputedTextLength();
    t.remove();
    return w;
  }

  // Shorten text with an ellipsis until it fits maxW (narrow layouts; the tooltip keeps the full label).
  function fitText(svg, text, size, maxW) {
    if (textWidth(svg, text, size) <= maxW) return text;
    let t = text;
    while (t.length > 1 && textWidth(svg, `${t}…`, size) > maxW) t = t.slice(0, -1);
    return `${t.trimEnd()}…`;
  }

  function legend(root, items) {
    const lg = d3.select(root).append("div").attr("class", "legend");
    items.forEach(it => {
      const i = lg.append("span").attr("class", "li");
      i.append("span").attr("class", "sw").style("background", it.color)
        .style("border", it.hollow ? `2px solid ${it.color}` : null).classed("hollow", !!it.hollow);
      i.append("span").text(it.label);
    });
  }

  // Row label (and optional value) for the row layouts. Wide: label right-aligned in a left column, vertically
  // centred on the mark. Narrow: label left-aligned on its own line above the mark, value at the right end.
  function rowLabel(g, narrow, labelW, W, labelOf, valueOf) {
    if (narrow) {
      const svg = d3.select(g.node().ownerSVGElement);
      g.append("text").attr("x", 0).attr("y", -10).attr("fill", TEXT2).attr("font-size", 12)
        .text(d => fitText(svg, labelOf(d), 12, W - (valueOf ? textWidth(svg, valueOf(d), 12) + 14 : 4)));
      if (valueOf) g.append("text").attr("x", W - 2).attr("y", -10).attr("text-anchor", "end").attr("fill", TEXT)
        .attr("font-size", 12).text(valueOf);
    } else {
      g.append("text").attr("x", labelW - 12).attr("y", 4).attr("text-anchor", "end").attr("fill", TEXT2)
        .attr("font-size", 13).text(labelOf);
    }
  }

  // ---------------------------------------------------------------- segmented bar (one whole, <= 6 parts)
  function segmented(root, s) {
    const W = root.clientWidth, H = s.barHeight || 64, gap = 2;
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const total = d3.sum(s.parts, p => p.pct);
    const x = d3.scaleLinear().domain([0, total]).range([0, W - gap * (s.parts.length - 1)]);
    let acc = 0;
    const parts = s.parts.map((p, i) => {
      const o = { ...p, x0: x(acc) + i * gap, w: x(p.pct) };
      acc += p.pct;
      return o;
    });
    const g = svg.selectAll("g.seg").data(parts).join("g").attr("class", "seg")
      .attr("transform", d => `translate(${d.x0},0)`);
    g.append("rect").attr("width", d => Math.max(1, d.w)).attr("height", H).attr("rx", 4).attr("fill", d => d.color);
    g.each(function (d) {
      const el = d3.select(this), ink = d.ink || "#ffffff";
      const big = pct1(d.pct), name = d.short || d.label;
      if (textWidth(svg, big, 18, 600) + 12 > d.w) return;
      const showName = textWidth(svg, name, 12) + 12 <= d.w && H >= 52;
      el.append("text").attr("x", 8).attr("y", showName ? H / 2 - 4 : H / 2 + 6).attr("fill", ink)
        .attr("font-size", 18).attr("font-weight", 600).text(big);
      if (showName) el.append("text").attr("x", 8).attr("y", H / 2 + 14).attr("fill", ink)
        .attr("font-size", 12).attr("opacity", 0.92).text(name);
    });
    hover(g, d => tipHtml(d.label, d.tip || [["Share", pct2(d.pct)]], d.note), g);
    legend(root, s.parts.map(p => ({ color: p.color, label: `${p.label} · ${pct1(p.pct)}` })));
  }

  // ---------------------------------------------------------------- dumbbell / range rows on one axis
  function dumbbell(root, s) {
    const W = root.clientWidth, narrow = isNarrow(root);
    const rowH = narrow ? 50 : (s.rowHeight || 34), top = 26;
    const labelW = narrow ? 8 : (s.labelWidth || 150), right = narrow ? 22 : 54;
    const H = top + rowH * s.rows.length + 6;
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const max = s.max || d3.max(s.rows, r => Math.max(r.a ?? 0, r.b ?? 0)) * 1.05;
    const x = d3.scaleLinear().domain([s.min || 0, max]).range([labelW, W - right]).nice();
    svg.append("g").attr("transform", `translate(0,${top - 6})`)
      .call(d3.axisTop(x).ticks(Math.max(2, Math.floor((W - labelW) / 80))).tickFormat(v => `${v}${s.unit ?? "%"}`)
        .tickSize(-(rowH * s.rows.length)))
      .call(a => a.select(".domain").remove())
      .call(a => a.selectAll("line").attr("stroke", GRID))
      .call(a => a.selectAll("text").attr("fill", MUTED).attr("font-size", 11));
    const markY = narrow ? 8 : 0;
    const g = svg.selectAll("g.row").data(s.rows).join("g").attr("class", "row")
      .attr("transform", (d, i) => `translate(0,${top + i * rowH + rowH / 2})`);
    g.append("rect").attr("x", 0).attr("y", -rowH / 2).attr("width", W).attr("height", rowH).attr("fill", "transparent");
    rowLabel(g, narrow, labelW, W, d => d.label, d => d.valueLabel ?? "");
    g.append("line").attr("x1", d => x(d.a)).attr("x2", d => x(d.b ?? d.a)).attr("y1", markY).attr("y2", markY)
      .attr("stroke", d => d.color).attr("stroke-width", d => (d.band ? 10 : 2)).attr("stroke-linecap", "round")
      .attr("opacity", d => (d.band ? 0.85 : 1));
    g.filter(d => !d.band).append("circle").attr("cx", d => x(d.a)).attr("cy", markY).attr("r", 6)
      .attr("fill", d => (d.b == null ? d.color : SURFACE))
      .attr("stroke", d => d.color).attr("stroke-width", 2);
    g.filter(d => !d.band && d.b != null).append("circle").attr("cx", d => x(d.b)).attr("cy", markY).attr("r", 6)
      .attr("fill", d => d.color).attr("stroke", SURFACE).attr("stroke-width", 2);
    if (!narrow) g.append("text").attr("x", d => x(Math.max(d.a, d.b ?? d.a)) + 12).attr("y", 4).attr("fill", TEXT)
      .attr("font-size", 12).text(d => d.valueLabel ?? "");
    hover(g, d => tipHtml(d.label, d.tip, d.note), g);
    if (s.legend) legend(root, s.legend);
  }

  // ---------------------------------------------------------------- heatmap (rows x cols, % of row)
  function heatmap(root, s) {
    const W = root.clientWidth, narrow = isNarrow(root), gap = 2;
    const labelW = narrow ? 0 : (s.labelWidth || 150), cellH = narrow ? 34 : (s.cellHeight || 40);
    const rowLabelH = narrow ? 18 : 0, rowH = cellH + rowLabelH;
    const cols = s.cols.length, cw = (W - labelW - gap * (cols - 1)) / cols;
    const headSize = narrow ? 10 : 12;
    // Column headers wrap onto as many lines as they need to fit their cell.
    const probe = d3.select(root).append("svg").attr("width", 0).attr("height", 0);
    const wrap = text => {
      const words = (Array.isArray(text) ? text.join(" ") : text).split(" "), lines = [];
      words.forEach(w => {
        const last = lines[lines.length - 1];
        if (last && textWidth(probe, `${last} ${w}`, headSize) <= cw - 4) lines[lines.length - 1] = `${last} ${w}`;
        else lines.push(w);
      });
      return lines;
    };
    const heads = s.cols.map(wrap);
    probe.remove();
    const top = 14 + 13 * d3.max(heads, h => h.length);
    const H = top + rowH * s.rows.length + 4;
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const vmax = s.max || d3.max(s.cells.flat(), c => (c && c.v != null && !c.small ? c.v : 0)) || 1;
    const color = d3.scaleSequential(d3.interpolateRgbBasis(["#14263f", "#1c5cab", "#3987e5", "#86b6ef", "#cde2fb"]))
      .domain([0, vmax]);
    heads.forEach((lines, j) => {
      const cx = labelW + j * (cw + gap) + cw / 2;
      const t = svg.append("text").attr("text-anchor", "middle").attr("fill", TEXT2).attr("font-size", headSize);
      lines.forEach((ln, k) => t.append("tspan").attr("x", cx).attr("y", top - 10 - (lines.length - 1 - k) * 13).text(ln));
    });
    const cells = [];
    s.rows.forEach((r, i) => {
      const y0 = top + i * rowH;
      if (narrow) svg.append("text").attr("x", 0).attr("y", y0 + 13).attr("fill", TEXT2).attr("font-size", 12).text(r);
      else svg.append("text").attr("x", labelW - 12).attr("y", y0 + cellH / 2 + 4).attr("text-anchor", "end")
        .attr("fill", TEXT2).attr("font-size", 13).text(r);
      s.cells[i].forEach((c, j) => cells.push({ ...c, i, j, row: r }));
    });
    const g = svg.selectAll("g.cell").data(cells).join("g").attr("class", "cell")
      .attr("transform", d => `translate(${labelW + d.j * (cw + gap)},${top + d.i * rowH + rowLabelH})`);
    g.append("rect").attr("width", cw).attr("height", cellH - gap).attr("rx", 3)
      .attr("fill", d => (d.v == null || d.small ? EMPTY : color(d.v)));
    g.append("text").attr("x", cw / 2).attr("y", (cellH - gap) / 2 + 4).attr("text-anchor", "middle")
      .attr("font-size", narrow ? 11 : 12).attr("font-weight", 500)
      .attr("fill", d => (d.v == null || d.small ? MUTED : d.v > vmax * 0.55 ? "#0b0b0b" : TEXT))
      .text(d => (d.v == null || d.small ? "—" : pct1(d.v)));
    hover(g, d => tipHtml(`${d.row} → ${d.colLabel || ""}`, d.tip, d.small ? "Fewer players than the minimum to show." : d.note), g);
  }

  // ---------------------------------------------------------------- 100% stacked horizontal bars
  function stacked(root, s) {
    const W = root.clientWidth, narrow = isNarrow(root), gap = 2;
    const labelW = narrow ? 0 : (s.labelWidth || 190), barH = narrow ? 26 : (s.rowHeight || 40) - 10;
    const rowH = narrow ? barH + 30 : (s.rowHeight || 40), barY = narrow ? 18 : 0;
    const H = rowH * s.rows.length + 4;
    legend(root, s.keys.map(k => ({ color: k.color, label: k.label })));
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const x = d3.scaleLinear().domain([0, 100]).range([0, W - labelW - 4]);
    const segs = [];
    s.rows.forEach((r, i) => {
      const y0 = i * rowH;
      const lab = narrow
        ? svg.append("text").attr("x", 0).attr("y", y0 + 12).attr("fill", TEXT2).attr("font-size", 12).text(r.label)
        : svg.append("text").attr("x", labelW - 12).attr("y", y0 + barH / 2 + 4).attr("text-anchor", "end")
          .attr("fill", TEXT2).attr("font-size", 13).text(r.label);
      if (r.sub) lab.append("tspan").attr("fill", MUTED).attr("font-size", 11).text(`  ${r.sub}`);
      if (r.empty) {
        svg.append("rect").attr("x", labelW).attr("y", y0 + barY).attr("width", x(100)).attr("height", barH)
          .attr("rx", 4).attr("fill", EMPTY);
        svg.append("text").attr("x", labelW + 10).attr("y", y0 + barY + barH / 2 + 4).attr("fill", MUTED)
          .attr("font-size", 12).text(r.empty);
        return;
      }
      const tot = d3.sum(s.keys, k => r.parts[k.key] || 0) || 1;
      let acc = 0;
      s.keys.forEach(k => {
        const v = (r.parts[k.key] || 0) * 100 / tot;
        if (v <= 0) return;
        segs.push({ ...k, row: r, y0: y0 + barY, v, raw: r.parts[k.key], x0: labelW + x(acc), w: x(v) });
        acc += v;
      });
    });
    const g = svg.selectAll("g.seg").data(segs).join("g").attr("class", "seg")
      .attr("transform", d => `translate(${d.x0},${d.y0})`);
    g.append("rect").attr("width", d => Math.max(1, d.w - gap)).attr("height", barH).attr("rx", 3).attr("fill", d => d.color);
    g.filter(d => textWidth(svg, pct1(d.raw), 12, 600) + 10 < d.w - gap).append("text").attr("x", 6)
      .attr("y", barH / 2 + 4).attr("font-size", 12).attr("font-weight", 600).attr("fill", d => d.ink || "#fff")
      .text(d => pct1(d.raw));
    hover(g, d => tipHtml(`${d.row.label}: ${d.label}`, [["Share of row", pct2(d.raw)],
      ...(d.row.n != null ? [["Players in row", fmtInt(d.row.n)]] : [])], d.row.note), g);
  }

  // ---------------------------------------------------------------- sankey (first -> next)
  function sankey(root, s) {
    const W = root.clientWidth, narrow = isNarrow(root), H = s.height || 420;
    const labelPad = narrow ? 98 : 150, fontSize = narrow ? 10 : 12;
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const order = new Map(s.nodes.map((n, i) => [n.id, i]));
    const graph = d3.sankey().nodeId(d => d.id).nodeWidth(narrow ? 10 : 14).nodePadding(narrow ? 8 : 10)
      .nodeAlign(d3.sankeyLeft).nodeSort((a, b) => order.get(a.id) - order.get(b.id)).linkSort(null)
      .extent([[labelPad, 20], [W - labelPad, H - 8]])({
        nodes: s.nodes.map(d => ({ ...d })), links: s.links.map(d => ({ ...d })) });
    const link = svg.append("g").attr("fill", "none").selectAll("path").data(graph.links).join("path")
      .attr("class", "lnk").attr("d", d3.sankeyLinkHorizontal()).attr("stroke", d => d.source.color)
      .attr("stroke-opacity", 0.45).attr("stroke-width", d => Math.max(1, d.width));
    const node = svg.append("g").selectAll("g").data(graph.nodes).join("g");
    node.append("rect").attr("x", d => d.x0).attr("y", d => d.y0).attr("width", d => d.x1 - d.x0)
      .attr("height", d => Math.max(1, d.y1 - d.y0)).attr("rx", 2).attr("fill", d => d.color);
    node.append("text").attr("x", d => (d.x0 < W / 2 ? d.x0 - 6 : d.x1 + 6)).attr("y", d => (d.y0 + d.y1) / 2 + 4)
      .attr("text-anchor", d => (d.x0 < W / 2 ? "end" : "start")).attr("fill", TEXT2).attr("font-size", fontSize)
      .text(d => d.label);
    link.on("mouseenter", function (ev, d) {
      link.classed("dim", o => o !== d);
      showTip(ev, tipHtml(`${d.source.label} → ${d.target.label}`, d.tip));
    }).on("mousemove", moveTip).on("mouseleave", () => { link.classed("dim", false); hideTip(); });
    node.on("mouseenter", function (ev, d) {
      link.classed("dim", o => o.source !== d && o.target !== d);
      showTip(ev, tipHtml(d.label, d.tip, d.note));
    }).on("mousemove", moveTip).on("mouseleave", () => { link.classed("dim", false); hideTip(); });
    if (s.headers) s.headers.forEach((h, i) => svg.append("text").attr("x", i === 0 ? 0 : W).attr("y", 10)
      .attr("text-anchor", i === 0 ? "start" : "end").attr("fill", MUTED).attr("font-size", 11).text(h));
  }

  // ---------------------------------------------------------------- IQR ranges (p25-p75 bar, median tick)
  function ranges(root, s) {
    const W = root.clientWidth, narrow = isNarrow(root);
    const rowH = narrow ? 52 : 38, top = 26, labelW = narrow ? 8 : (s.labelWidth || 200), right = narrow ? 22 : 60;
    const H = top + rowH * s.rows.length + 4, markY = narrow ? 8 : 0;
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const x = d3.scaleLinear().domain([0, s.max || d3.max(s.rows, r => r.p75) * 1.1]).range([labelW, W - right]).nice();
    svg.append("g").attr("transform", `translate(0,${top - 6})`)
      .call(d3.axisTop(x).ticks(Math.max(2, Math.floor((W - labelW) / 80))).tickFormat(v => `${v}${s.unit || ""}`)
        .tickSize(-(rowH * s.rows.length)))
      .call(a => a.select(".domain").remove()).call(a => a.selectAll("line").attr("stroke", GRID))
      .call(a => a.selectAll("text").attr("fill", MUTED).attr("font-size", 11));
    const g = svg.selectAll("g.row").data(s.rows).join("g").attr("class", "row")
      .attr("transform", (d, i) => `translate(0,${top + i * rowH + rowH / 2})`);
    g.append("rect").attr("y", -rowH / 2).attr("width", W).attr("height", rowH).attr("fill", "transparent");
    rowLabel(g, narrow, labelW, W, d => d.label, d => `${d.median}${s.unit || ""}`);
    g.append("rect").attr("x", d => x(d.p25)).attr("y", markY - 9).attr("width", d => x(d.p75) - x(d.p25))
      .attr("height", 18).attr("rx", 4).attr("fill", d => d.color).attr("opacity", 0.55);
    g.append("line").attr("x1", d => x(d.median)).attr("x2", d => x(d.median)).attr("y1", markY - 13)
      .attr("y2", markY + 13).attr("stroke", TEXT).attr("stroke-width", 2);
    if (!narrow) g.append("text").attr("x", d => x(d.p75) + 10).attr("y", 4).attr("fill", TEXT).attr("font-size", 12)
      .text(d => `${d.median}${s.unit || ""}`);
    hover(g, d => tipHtml(d.label, d.tip), g);
    if (s.legend) legend(root, s.legend);
  }

  // ---------------------------------------------------------------- horizontal bars (one series)
  function hbars(root, s) {
    const W = root.clientWidth, narrow = isNarrow(root);
    const barH = narrow ? 16 : (s.rowHeight || 32) - 10, rowH = narrow ? 42 : (s.rowHeight || 32);
    const labelW = narrow ? 0 : (s.labelWidth || 220), right = narrow ? 2 : 70, barY = narrow ? 20 : 0;
    const H = rowH * s.rows.length + 4;
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const x = d3.scaleLinear().domain([0, s.max || d3.max(s.rows, r => r.value)]).range([0, W - labelW - right]);
    const g = svg.selectAll("g.row").data(s.rows).join("g").attr("class", "row")
      .attr("transform", (d, i) => `translate(0,${i * rowH})`);
    g.append("rect").attr("width", W).attr("height", rowH).attr("fill", "transparent");
    if (narrow) {
      g.append("text").attr("x", 0).attr("y", 13).attr("fill", TEXT2).attr("font-size", 12)
        .text(d => fitText(svg, d.label, 12, W - textWidth(svg, d.display, 12) - 14));
      g.append("text").attr("x", W - 2).attr("y", 13).attr("text-anchor", "end").attr("fill", TEXT)
        .attr("font-size", 12).text(d => d.display);
    } else {
      g.append("text").attr("x", labelW - 12).attr("y", barH / 2 + 4).attr("text-anchor", "end").attr("fill", TEXT2)
        .attr("font-size", 13).text(d => d.label);
    }
    g.append("rect").attr("x", labelW).attr("y", barY).attr("width", d => Math.max(2, x(d.value))).attr("height", barH)
      .attr("rx", 4).attr("fill", d => d.color || s.color || "#3987e5");
    if (!narrow) g.append("text").attr("x", d => labelW + Math.max(2, x(d.value)) + 8).attr("y", barH / 2 + 4)
      .attr("fill", TEXT).attr("font-size", 12).text(d => d.display);
    hover(g, d => tipHtml(d.label, d.tip, d.note), g);
  }

  // ---------------------------------------------------------------- vertical columns (one series)
  function columns(root, s) {
    const W = root.clientWidth, H = s.height || 240, bottom = 40, top = 22, left = 8;
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H);
    const x = d3.scaleBand().domain(s.bars.map(b => b.x)).range([left, W - 8]).padding(0.18);
    const y = d3.scaleLinear().domain([0, s.max || d3.max(s.bars, b => b.value) * 1.12]).range([H - bottom, top]);
    svg.append("line").attr("x1", left).attr("x2", W - 8).attr("y1", H - bottom).attr("y2", H - bottom).attr("stroke", AXIS);
    const g = svg.selectAll("g.col").data(s.bars).join("g").attr("class", "col");
    g.append("rect").attr("x", d => x(d.x)).attr("y", top - 20).attr("width", x.bandwidth())
      .attr("height", H - bottom - top + 20).attr("fill", "transparent");
    g.append("path").attr("fill", d => d.color || s.color || "#3987e5").attr("d", d => {
      const x0 = x(d.x), w = x.bandwidth(), y0 = y(d.value), b = H - bottom, r = Math.min(4, b - y0);
      return `M${x0},${b}V${y0 + r}Q${x0},${y0} ${x0 + r},${y0}H${x0 + w - r}Q${x0 + w},${y0} ${x0 + w},${y0 + r}V${b}Z`;
    });
    g.append("text").attr("x", d => x(d.x) + x.bandwidth() / 2).attr("y", d => y(d.value) - 6).attr("text-anchor", "middle")
      .attr("fill", TEXT).attr("font-size", 12).text(d => d.display);
    g.append("text").attr("x", d => x(d.x) + x.bandwidth() / 2).attr("y", H - bottom + 18).attr("text-anchor", "middle")
      .attr("fill", TEXT2).attr("font-size", 12).text(d => d.x);
    if (s.xLabel) svg.append("text").attr("x", W / 2).attr("y", H - 4).attr("text-anchor", "middle").attr("fill", MUTED)
      .attr("font-size", 11).text(s.xLabel);
    hover(g, d => tipHtml(d.title || d.x, d.tip), g);
  }

  window.CHARTS = { segmented, dumbbell, heatmap, stacked, sankey, ranges, hbars, columns };

  // Streamlit's own size script (st.iframe height="content") takes the max of several measurements, including
  // documentElement.scrollHeight, which never drops below the frame's current height. Frames can grow but not
  // shrink, so a chart that gets shorter after a toggle leaves a gap. Report the chart's true height in the same
  // message format, after Streamlit's own report; once the frame matches, both measurements agree.
  function reportSize() {
    const h = Math.ceil(document.getElementById("root").getBoundingClientRect().height);
    window.parent.postMessage({ type: "streamlit:iframe:setSize", width: document.documentElement.clientWidth, height: h }, "*");
  }

  // The frame is sized to the chart, and a tooltip can't draw outside it. Short charts (the ending bars) are
  // shorter than their tooltips, so make the chart area at least as tall as the tallest tooltip it can show.
  function reserveTipSpace(root) {
    const n = tip.node();
    tip.style("visibility", "hidden").style("left", "0px").style("top", "0px");
    let tallest = 0;
    tipSources.forEach(src => src().forEach(html => { n.innerHTML = html; tallest = Math.max(tallest, n.offsetHeight); }));
    tip.html("").style("visibility", null);
    if (tallest + 12 > root.getBoundingClientRect().height) root.style.minHeight = `${tallest + 12}px`;
  }

  function draw() {
    const root = document.getElementById("root");
    root.innerHTML = "";
    root.style.minHeight = "";
    tipSources.length = 0;
    window.CHARTS[window.SPEC.type](root, window.SPEC);
    reserveTipSpace(root);
    setTimeout(reportSize, 0);
    setTimeout(reportSize, 250);
  }
  let last = 0;
  window.addEventListener("resize", () => {
    if (Math.abs(window.innerWidth - last) < 4) return;
    last = window.innerWidth;
    draw();
  });
  window.addEventListener("load", () => { last = window.innerWidth; draw(); });
})();
