/* 麦当劳体验活动地图 —— 前端逻辑（零依赖）
 *
 * 地图为纯 SVG 散点图：只绘制城市坐标点与经纬网格，不描绘任何行政边界，
 * 因此不涉及领土表示；如需带底图的视图，请自行接入腾讯地图 / 高德 / 百度 / 天地图，
 * 并遵守《中华人民共和国测绘法》与相应地图合规要求（见 README「地图合规」一节）。
 */
(function () {
  "use strict";

  var DATA_URL = "../data/atlas.json";

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text, asHTML) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) {
      if (asHTML) n.innerHTML = text; else n.textContent = text;
    }
    return n;
  }
  function fmt(n) { return n == null ? "—" : String(n); }
  function yuan(fen) {
    if (fen == null || isNaN(fen)) return "—";
    return "¥" + (Number(fen) / 100).toFixed(2).replace(/\.00$/, "");
  }

  // ---- Web Mercator 投影 ------------------------------------------
  function project(lat, lng) {
    var x = (lng + 180) / 360;
    var s = Math.sin((lat * Math.PI) / 180);
    var y = 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI);
    return [x, y];
  }

  var state = {
    atlas: null, cities: [], storeIndex: {}, selected: null,
    mode: "variety", category: "all",
    variety: {},            // cityCode -> 可体验 SPU 数
    catSets: {},            // catName -> Set(cityCode)
    spuCount: {}            // catName -> SPU 数
  };

  // ---- 统计卡 ------------------------------------------------------
  function renderStats(a) {
    var box = $("stats");
    box.innerHTML = "";
    var items = [
      [a.meta.cityCount, "可预约城市"],
      [a.meta.storeCount, "可办活动门店"],
      [a.meta.sessionCount, "场次样本"],
      [a.meta.spuCount, "体验品类 SPU"],
      [a.meta.toolCount, "MCP 工具（实测）"]
    ];
    items.forEach(function (it) {
      var d = el("div", "stat");
      d.appendChild(el("b", null, fmt(it[0])));
      d.appendChild(el("span", null, it[1]));
      box.appendChild(d);
    });
  }

  // ---- 派生数据 ----------------------------------------------------
  function derive(a) {
    state.variety = {};
    state.catSets = {};
    state.spuCount = {};
    (a.coverage || []).forEach(function (c) {
      var cat = c.catName || "未分类";
      state.spuCount[cat] = (state.spuCount[cat] || 0) + 1;
      if (!state.catSets[cat]) state.catSets[cat] = {};
      (c.cityCodes || []).forEach(function (code) {
        state.variety[code] = (state.variety[code] || 0) + 1;
        state.catSets[cat][code] = true;
      });
    });
  }

  // ---- 品类下拉 ----------------------------------------------------
  function renderCategorySelect() {
    var sel = $("catSel");
    sel.innerHTML = "";
    var all = el("option", null, "全部品类");
    all.value = "all";
    sel.appendChild(all);
    Object.keys(state.catSets).sort().forEach(function (cat) {
      var o = el("option", null, cat + "（" + state.spuCount[cat] + " 款）");
      o.value = cat;
      sel.appendChild(o);
    });
    sel.value = state.category;
  }

  // ---- 覆盖条形图（可点击筛选）-------------------------------------
  function renderCoverage(a) {
    var box = $("coverage");
    box.innerHTML = "";
    var max = 1;
    (a.coverage || []).forEach(function (c) { if (c.cities > max) max = c.cities; });
    (a.coverage || []).forEach(function (c) {
      var row = el("div", "bar" + (state.category === c.catName ? " on" : ""));
      row.appendChild(el("div", "lb", c.catName || "未分类"));
      var track = el("div", "tr");
      var fill = el("div", "fl");
      fill.style.width = (c.cities / max) * 100 + "%";
      if (c.cities === 0) fill.style.background = "#D3D1C7";
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("div", "vl", fmt(c.cities)));
      row.title = (c.spuName || "") + "（spuId " + c.spuId + "）";
      row.addEventListener("click", function () {
        state.category = (state.category === c.catName) ? "all" : c.catName;
        renderCategorySelect();
        renderCoverage(a);
        renderMap(a);
        renderLegend();
      });
      box.appendChild(row);
    });
  }

  // ---- 数据洞察 ----------------------------------------------------
  function renderInsights(a) {
    var box = $("insights");
    box.innerHTML = "";
    var cities = a.cities || [];
    var cov = a.coverage || [];

    // 1. 覆盖最少的品类
    var zero = cov.filter(function (c) { return c.cities === 0; });
    if (zero.length) {
      box.appendChild(el("div", "insight",
        "有 " + zero.length + " 款体验活动<b>全国零城市可约</b>，例如「" +
        zero[0].spuName + "」。已下架或尚未开放场次。", true));
    }

    // 2. 覆盖最差的非零品类
    var nonzero = cov.filter(function (c) { return c.cities > 0; })
                     .sort(function (x, y) { return x.cities - y.cities; });
    if (nonzero.length) {
      box.appendChild(el("div", "insight",
        "覆盖最窄的在售活动是「" + nonzero[0].spuName + "」，全国仅 <b>" +
        nonzero[0].cities + "</b> 个城市可约。", true));
    }

    // 3. 体验丰富度分布
    var vals = cities.map(function (c) { return state.variety[c.code] || 0; })
                     .sort(function (x, y) { return x - y; });
    if (vals.length) {
      var median = vals[Math.floor(vals.length / 2)];
      var top = cities.slice().sort(function (x, y) {
        return (state.variety[y.code] || 0) - (state.variety[x.code] || 0);
      })[0];
      box.appendChild(el("div", "insight",
        "每城可体验的活动种类：中位数 <b>" + median + "</b> 款，最少 " + vals[0] +
        " 款，最多 " + vals[vals.length - 1] + " 款。体验最丰富的是<b>" +
        (top ? top.name : "—") + "</b>。", true));
    }

    // 4. 门店集中度
    var counts = cities.map(function (c) {
      return (state.storeIndex[c.code] || []).length;
    }).sort(function (x, y) { return y - x; });
    if (counts.length) {
      var top10 = counts.slice(0, 10).reduce(function (s, v) { return s + v; }, 0);
      var total = counts.reduce(function (s, v) { return s + v; }, 0) || 1;
      box.appendChild(el("div", "insight",
        "可办门店高度集中：前 10 个城市占全国 <b>" +
        Math.round((top10 / total) * 100) + "%</b>（" +
        (counts[0] || 0) + " 家为其一城之最）。", true));
    }
  }

  // ---- 地图 --------------------------------------------------------
  function renderMap(a) {
    var svg = $("map");
    var wrap = $("mapWrap");
    var W = wrap.clientWidth || 900;
    var H = wrap.clientHeight || 620;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.innerHTML = "";

    var cities = a.cities || [];
    if (!cities.length) return;
    var pts = cities.map(function (c) { return project(c.latitude, c.longitude); });
    var xs = pts.map(function (p) { return p[0]; });
    var ys = pts.map(function (p) { return p[1]; });
    var pad = 46;
    var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    var spanX = Math.max(maxX - minX, 1e-6), spanY = Math.max(maxY - minY, 1e-6);
    var scale = Math.min((W - pad * 2) / spanX, (H - pad * 2) / spanY);
    var offX = (W - spanX * scale) / 2, offY = (H - spanY * scale) / 2;

    function toScreen(lat, lng) {
      var p = project(lat, lng);
      return [offX + (p[0] - minX) * scale, offY + (p[1] - minY) * scale];
    }

    // 经纬网格（仅为读数参考，不表示任何边界）
    var grid = document.createElementNS("http://www.w3.org/2000/svg", "g");
    for (var lat = 20; lat <= 50; lat += 10) {
      var p1 = toScreen(lat, 73), p2 = toScreen(lat, 135);
      var ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
      ln.setAttribute("x1", p1[0]); ln.setAttribute("y1", p1[1]);
      ln.setAttribute("x2", p2[0]); ln.setAttribute("y2", p2[1]);
      ln.setAttribute("stroke", "#eeece6"); ln.setAttribute("stroke-width", "1");
      grid.appendChild(ln);
      var t = document.createElementNS("http://www.w3.org/2000/svg", "text");
      t.setAttribute("x", 6); t.setAttribute("y", p1[1] + 4);
      t.setAttribute("font-size", "10"); t.setAttribute("fill", "#b9b8b2");
      t.textContent = lat + "°N";
      grid.appendChild(t);
    }
    svg.appendChild(grid);

    var catSet = state.category === "all" ? null : state.catSets[state.category];

    // 归一化用的最大值
    var maxVal = 1;
    cities.forEach(function (c) {
      var v = state.mode === "variety"
        ? (state.variety[c.code] || 0)
        : (state.storeIndex[c.code] || []).length;
      if (v > maxVal) maxVal = v;
    });

    var layer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    cities.forEach(function (c) {
      var val = state.mode === "variety"
        ? (state.variety[c.code] || 0)
        : (state.storeIndex[c.code] || []).length;
      var p = toScreen(c.latitude, c.longitude);
      var r = 3 + 7 * Math.sqrt(val / maxVal);
      var covered = !catSet || catSet[c.code];
      var circ = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circ.setAttribute("cx", p[0]); circ.setAttribute("cy", p[1]);
      circ.setAttribute("r", covered ? r : Math.max(2.2, r * 0.55));
      circ.setAttribute("fill", covered ? "#DA291C" : "#D3D1C7");
      circ.setAttribute("fill-opacity", covered ? "0.72" : "0.5");
      circ.setAttribute("stroke", "#ffffff");
      circ.setAttribute("stroke-width", "0.8");
      circ.setAttribute("class", "dot");
      circ.setAttribute("data-code", c.code);
      (function (city) {
        circ.addEventListener("click", function () { selectCity(city.code); });
        var title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        var label = state.mode === "variety"
          ? (state.variety[city.code] || 0) + " 款体验活动"
          : (state.storeIndex[city.code] || []).length + " 家可办门店";
        title.textContent = city.name + " · " + label +
          (catSet && !catSet[city.code] ? "（不在所选品类覆盖内）" : "");
        circ.appendChild(title);
      })(c);
      layer.appendChild(circ);
    });
    svg.appendChild(layer);

    if (state.selected) {
      var node = document.querySelector('.dot[data-code="' + state.selected + '"]');
      if (node) node.classList.add("sel");
    }
  }

  function renderLegend() {
    var box = $("legend");
    box.innerHTML = "";
    var modeLabel = state.mode === "variety" ? "可体验的活动款数" : "可办活动门店数";
    box.appendChild(el("div", null, "圆点大小 = " + modeLabel));
    box.appendChild(el("div", null, ""));
    var row1 = el("div");
    var i1 = el("i"); i1.style.background = "#DA291C";
    row1.appendChild(i1);
    row1.appendChild(document.createTextNode(
      state.category === "all" ? "在采范围内的城市" : "「" + state.category + "」可约"));
    box.appendChild(row1);
    var row2 = el("div");
    var i2 = el("i"); i2.style.background = "#D3D1C7";
    row2.appendChild(i2);
    row2.appendChild(document.createTextNode(
      state.category === "all" ? "—" : "该品类不可约"));
    box.appendChild(row2);
  }

  // ---- 结果可见性引导 ------------------------------------------------
  // 搜索结果/城市详情渲染在右侧栏较深处（品类覆盖列表之下），
  // 输入关键词后若目标区块不在视野内，自动滚进视野，否则用户会以为搜索无响应。
  function ensureVisible(node) {
    if (!node) return;
    var r = node.getBoundingClientRect();
    if (r.top < 0 || r.top > window.innerHeight - 80) {
      node.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // ---- 搜索（城市 + 门店）------------------------------------------
  function renderResults(kw) {
    var box = $("resultList");
    box.innerHTML = "";
    kw = (kw || "").trim();
    if (!kw) {
      box.appendChild(el("div", "empty", "输入城市名或门店名，如：北京 / 东单"));
      return;
    }
    ensureVisible(box.closest(".sec"));
    var a = state.atlas;
    var hits = [];

    (a.cities || []).forEach(function (c) {
      if (c.name.indexOf(kw) >= 0) {
        hits.push({ type: "city", name: c.name, code: c.code,
                    note: (state.storeIndex[c.code] || []).length + " 家可办门店 · " +
                          (state.variety[c.code] || 0) + " 款活动" });
      }
    });

    var storeHits = 0;
    Object.keys(state.storeIndex).some(function (code) {
      var stores = state.storeIndex[code] || [];
      for (var i = 0; i < stores.length && storeHits < 25; i++) {
        var s = stores[i];
        var nm = s.name || s.shortName || "";
        if (nm.indexOf(kw) >= 0) {
          hits.push({ type: "store", name: nm, code: code,
                      note: (s.address || "") + (s.distanceText ? " · " + s.distanceText : "") });
          storeHits++;
        }
      }
      return storeHits >= 25;
    });

    if (!hits.length) {
      box.appendChild(el("div", "empty", "没有匹配的城市或门店"));
      return;
    }
    hits.slice(0, 40).forEach(function (h) {
      var card = el("div", "card");
      card.style.cursor = "pointer";
      card.appendChild(el("div", "n", h.name));
      card.appendChild(el("div", "m", h.note));
      card.addEventListener("click", function () { selectCity(h.code); });
      box.appendChild(card);
    });
    if (hits.length > 40) {
      box.appendChild(el("div", "empty", "另有 " + (hits.length - 40) + " 条未展示"));
    }
  }

  // ---- 城市详情 ----------------------------------------------------
  function selectCity(code) {
    var a = state.atlas;
    var city = null;
    (a.cities || []).forEach(function (c) { if (c.code === code) city = c; });
    if (!city) return;

    state.selected = code;
    Array.prototype.forEach.call(document.querySelectorAll(".dot"), function (d) {
      d.classList.remove("sel");
    });
    var node = document.querySelector('.dot[data-code="' + code + '"]');
    if (node) node.classList.add("sel");

    var filter = $("storeFilter").value;
    var stores = (state.storeIndex[code] || []).filter(function (s) {
      if (filter !== "open") return true;
      return s.onlineBusinessStatus !== false && s.businessStatus !== 0;
    });

    $("pTitle").textContent = city.name;
    $("pSub").textContent = "行政区划码 " + code + " · 共 " +
      (state.storeIndex[code] || []).length + " 家可办门店 · " +
      (state.variety[code] || 0) + " 款体验活动";
    $("detail").style.display = "block";
    ensureVisible($("detail"));

    var sl = $("storeList");
    sl.innerHTML = "";
    if (!stores.length) {
      sl.appendChild(el("div", "empty",
        filter === "open" ? "该城市当前没有可预约门店" : "该城市暂无采到可办门店"));
    } else {
      stores.slice(0, 40).forEach(function (s) {
        var card = el("div", "card");
        card.appendChild(el("div", "n", s.name || s.shortName || "（未命名门店）"));
        var meta = el("div", "m");
        meta.textContent = (s.address || "地址未知") +
          (s.distanceText ? " · " + s.distanceText : "");
        card.appendChild(meta);
        var tags = el("div", "m");
        if (s.onlineBusinessStatus === false || s.businessStatus === 0) {
          tags.appendChild(el("span", "tag none", "暂不可预约"));
        } else {
          tags.appendChild(el("span", "tag ok", "可预约"));
        }
        card.appendChild(tags);
        sl.appendChild(card);
      });
      if (stores.length > 40) {
        sl.appendChild(el("div", "empty", "另有 " + (stores.length - 40) + " 家门店未展示"));
      }
    }

    // 7 天日历 + 场次
    var sample = null;
    (a.sessions || []).forEach(function (s) { if (s.cityCode === code) sample = s; });
    var cal = $("cal");
    cal.innerHTML = "";
    var sess = $("sessionList");
    sess.innerHTML = "";

    if (!sample) {
      cal.style.display = "none";
      sess.appendChild(el("div", "empty", "该城市未纳入场次抽样（可运行 collect.py --deep 深采）"));
      return;
    }
    cal.style.display = "grid";

    var byDate = {};
    (sample.sessions || []).forEach(function (x) { byDate[x.date] = x; });
    (sample.dates || []).forEach(function (d) {
      var n = byDate[d.date] ? byDate[d.date].length : 0;
      var cell = el("div", n === 0 ? "zero" : "some");
      cell.appendChild(el("div", "d", d.date.slice(5).replace("-", "/")));
      cell.appendChild(el("div", "c", n === 0 ? "—" : String(n)));
      cell.title = d.date + "：" + n + " 个场次";
      cal.appendChild(cell);
    });

    var hdr = el("div", "card");
    hdr.appendChild(el("div", "n", sample.storeName || sample.storeCode));
    hdr.appendChild(el("div", "m",
      (sample.sessions || []).length + " 个场次（采样日）"));
    sess.appendChild(hdr);

    (sample.sessions || []).forEach(function (s) {
      var row = el("div", "sess");
      row.appendChild(el("div", "t", s.timeStart + "–" + s.timeEnd));
      var r = el("div", "r");
      r.textContent = (s.partyMin || "?") + "~" + (s.partyMax || "?") + " 人 · " +
        yuan(s.price) + " · 余位 " + fmt(s.leftNum);
      row.appendChild(r);
      sess.appendChild(row);
    });
    if (!(sample.sessions || []).length) {
      sess.appendChild(el("div", "empty", "采样日暂无场次"));
    }
  }

  // ---- 启动 -------------------------------------------------------
  function init(a) {
    state.atlas = a;
    state.cities = a.cities || [];
    state.storeIndex = a.storeIndex || {};
    derive(a);
    renderStats(a);
    renderCategorySelect();
    renderCoverage(a);
    renderInsights(a);
    renderMap(a);
    renderLegend();
    renderResults("");

    $("modeSeg").addEventListener("click", function (e) {
      var btn = e.target.closest("button");
      if (!btn) return;
      state.mode = btn.getAttribute("data-mode");
      Array.prototype.forEach.call($("modeSeg").children, function (b) {
        b.classList.toggle("on", b === btn);
      });
      renderMap(a);
      renderLegend();
    });
    $("catSel").addEventListener("change", function (e) {
      state.category = e.target.value;
      renderCoverage(a);
      renderMap(a);
      renderLegend();
    });
    $("storeFilter").addEventListener("change", function () {
      if (state.selected) selectCity(state.selected);
    });
    $("search").addEventListener("input", function (e) {
      renderResults(e.target.value);
    });

    var timer = null;
    window.addEventListener("resize", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { renderMap(a); }, 150);
    });
  }

  fetch(DATA_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(init)
    .catch(function (err) {
      $("stats").innerHTML = '<div class="stat"><b>!</b><span>数据加载失败</span></div>';
      $("pSub").textContent =
        "无法加载 " + DATA_URL + "（" + err.message +
        "）。请先运行 python src/build_atlas.py 生成数据包；" +
        "直接双击打开本地文件时，浏览器会拦截 fetch，请改用 dist/index.html 单文件版本。";
    });
})();
