/* global XLSX */
(function () {
  "use strict";
  const DEFAULT_HEAD_FILE_URL = "head.xlsx";
  const OUTPUT_ROW_DATA_START = 7;
  const OUTPUT_COL_C = 3;
  const OUTPUT_COL_D_START = 4;
  const OUTPUT_COL_D_END = 13;
  const OUTPUT_COL_D = 4;
  const OUTPUT_COL_F = 6;
  const OUTPUT_COL_H = 8;
  const OUTPUT_COL_J = 10;
  const OUTPUT_COL_M = 13;
  const OUTPUT_COL_N = 14;
  const OUTPUT_COL_O = 15;
  const OUTPUT_COL_P = 16;
  const OUTPUT_COL_Q = 17;
  const OUTPUT_COL_R = 18;
  const OUTPUT_COL_B = 2;
  const OUTPUT_COL_T = 20;
  const OUTPUT_COL_U = 21;
  const OUTPUT_COL_V = 22;
  const OUTPUT_COL_W = 23;
  const OUTPUT_COL_X = 24;
  const OUTPUT_COL_Y = 25;
  const OUTPUT_COL_Z = 26;
  const OUTPUT_COL_AA = 27;
  const OUTPUT_COL_AB = 28;
  const OUTPUT_COL_AC = 29;
  const TWO_DECIMAL_PATTERN = "0.00";
  const U_DEFAULT_TEXT = "不区分";

  const N_VALUE_BY_D = {
    "07": "不划片",
    A07: "不划片",
    J07: "不划片",
    K07: "不划片",
    G07: "不划片",
    GA07: "不划片",
    GJ07: "不划片",
    GK07: "不划片",
    "07A": "半片划片",
    A07A: "半片划片",
    J07A: "半片划片",
    K07A: "半片划片",
    G07A: "半片划片",
    GA07A: "半片划片",
    GJ07A: "半片划片",
    GK07A: "半片划片",
  };
  const N_VALUE_BY_J_FOR_D_07D = {
    "39": "三分片钝化边片",
    "40": "三分片钝化边片",
    "41": "三分片钝化边片",
    "42": "三分片钝化中片",
    "43": "三分片钝化中片",
    "44": "三分片钝化中片",
    "45": "三分片非钝化边片",
    "46": "三分片非钝化边片",
    "47": "三分片非钝化边片",
  };
  const O_VALUE_BY_D = {
    "07": null,
    A07: null,
    J07: null,
    K07: null,
    G07: null,
    GA07: null,
    GJ07: null,
    GK07: null,
    "07A": null,
    A07A: null,
    J07A: null,
    K07A: null,
    G07A: "关联外购",
    GA07A: "关联外购",
    GJ07A: "关联外购",
    GK07A: "关联外购",
    "07D": null,
  };
  const P_VALUE_BY_F = {
    "54": "JACMLTB-D",
    "56": "JACMKTB-D",
    "58": "JACMJTB-D",
    "59": "JACMNTB-D",
    "61": "JACMFTB-E",
    "63": "JACMSTB-F",
    "66": "JACMNTB-F",
    "68": "JACMYTB-D",
  };
  const Q_VALUE_BY_F = {
    "54": "182SL",
    "56": "182SK",
    "58": "182SJ",
    "59": "182SN",
    "61": "210SF",
    "63": "182SS",
    "66": "182SN",
    "68": "183SY",
  };
  const R_VALUE_BY_F = {
    "54": "16BB",
    "56": "16BB",
    "58": "16BB",
    "59": "16BB",
    "61": "18BB",
    "63": "20BB",
    "66": "20BB",
    "68": "16BB",
  };
  const AB_VALUE_BY_F = {
    "54": "0702001",
    "56": "0703001",
    "58": "0701001",
    "59": "0704001",
    "61": "0705001",
    "63": "0706001",
    "66": "0704001",
    "68": "0708001",
  };
  const AC_VALUE_BY_F = {
    "54": "/Default/04_自产电池/182SL",
    "56": "/Default/04_自产电池/182SK",
    "58": "/Default/04_自产电池/182SJ",
    "59": "/Default/04_自产电池/182SN",
    "61": "/Default/04_自产电池/210SF",
    "63": "/Default/04_自产电池/182SS",
    "66": "/Default/04_自产电池/182SN",
    "68": "/Default/04_自产电池/183SY",
  };
  const C1_VALUE_BY_SEGMENT = {
    "07": "自产电池片",
    A07: "自产电池片(L1)",
    J07: "自产电池片(BPF)",
    K07: "自产电池片(BPF+L1)",
    G07: "外购自产电池片",
    GA07: "外购自产电池片(L1)",
    GJ07: "外购自产电池片(BPF)",
    GK07: "外购自产电池片(BPF+L1)",
    "07A": "自产电池片半片",
    A07A: "自产电池片半片(L1)",
    J07A: "自产电池片半片(BPF)",
    K07A: "自产电池片半片(BPF+L1)",
    G07A: "外购自产电池片半片",
    GA07A: "外购自产电池片半片(L1)",
    GJ07A: "外购自产电池片半片(BPF)",
    GK07A: "外购自产电池片半片(BPF+L1)",
    "07D": "自产电池片三分片",
  };
  const C2_VALUE_BY_SEGMENT = { "01": "晶澳" };
  const C3_VALUE_BY_SEGMENT = {
    "54": "182SLn;16BB",
    "56": "182SKn;16BB",
    "58": "182SJn;16BB",
    "59": "182SNn;16BB",
    "61": "210SFn;18BB",
    "63": "182SSn;20BB",
    "66": "182SNn;20BB",
    "68": "183SYn;16BB",
  };
  const C4_VALUE_BY_SEGMENT = {
    AS: "DCTZ-027-R043",
    AT: "DCTZ-027-R044",
    AU: "DCTZ-027-R045",
    AV: "DCTZ-027-R046",
    AW: "DCTZ-027-R047",
    AX: "DCTZ-027-R048",
    AY: "DCTZ-027-R049",
    AZ: "DCTZ-027-R050",
    BA: "DCTZ-027-R051",
  };
  const C6_VALUE_BY_SEGMENT = {
    "01": "A类片",
    "02": "B类片",
    "08": "A2类片",
    "11": "A1类片",
    "12": "C类片",
    "13": "不区分",
  };
  const C7_VALUE_BY_SEGMENT = {
    "26": "电流0-0.4",
    "27": "电流0.4-2",
    "34": "不区分",
    "39": "电流0-0.4;钝化边片",
    "40": "电流0.4-2;钝化边片",
    "41": "不区分;钝化边片",
    "42": "电流0-0.4;钝化中片",
    "43": "电流0.4-2;钝化中片",
    "44": "不区分;钝化中片",
    "45": "电流0-0.4;非钝化边片",
    "46": "电流0.4-2;非钝化边片",
    "47": "不区分;非钝化边片",
    "48": "电流0-0.4;扬州F3",
    "49": "电流0.4-2;扬州F3",
    "50": "不区分;扬州F3",
  };
  const C8_VALUE_BY_SEGMENT = {
    "10": "120um",
    "11": "125um",
    "12": "130um",
    "13": "135um",
    "14": "140um",
    "15": "145um",
    "16": "150um",
  };
  const C9_VALUE_BY_SEGMENT = {
    "00": "不区分订单",
    "98": "碳足迹",
    "97": "黑组件",
    "94": "定制化订单",
    "92": "黑组件定制化",
    "91": "特殊定制化",
    "90": "黑组件特殊定制化",
    "89": "碳足迹定制化",
    "88": "碳足迹黑组件定制化",
    "87": "SSI认证供应商",
    "86": "SSI批准供应商",
  };
  const C10_VALUE_BY_SEGMENT = {
    "400": "正面不分色",
    "410": "正面1号色单玻",
    "411": "正面1号色双玻",
    "420": "正面2号色单玻",
    "421": "正面2号色双玻",
    "430": "正面3号色单玻",
  };
  const OUTPUT_C_LOOKUP_BY_SEGMENT_INDEX = [
    C1_VALUE_BY_SEGMENT,
    C2_VALUE_BY_SEGMENT,
    C3_VALUE_BY_SEGMENT,
    C4_VALUE_BY_SEGMENT,
    null,
    C6_VALUE_BY_SEGMENT,
    C7_VALUE_BY_SEGMENT,
    C8_VALUE_BY_SEGMENT,
    C9_VALUE_BY_SEGMENT,
    C10_VALUE_BY_SEGMENT,
  ];
  const V_VALUE_BY_M = {
    "400": "正面不分色",
    "410": "正面1号色",
    "411": "正面1号色",
    "420": "正面2号色",
    "421": "正面2号色",
    "430": "正面3号色",
  };
  const W_VALUE_BY_M = {
    "400": "不区分",
    "410": "单玻",
    "411": "双玻",
    "420": "单玻",
    "421": "双玻",
    "430": "单玻",
  };
  const X_VALUE_BY_J = {
    "26": "电流0-0.4",
    "27": "电流0.4-2",
    "34": "不区分",
    "39": "电流0-0.4",
    "40": "电流0.4-2",
    "41": "不区分",
    "42": "电流0-0.4",
    "43": "电流0.4-2",
    "44": "不区分",
    "45": "电流0-0.4",
    "46": "电流0.4-2",
    "47": "不区分",
    "48": "电流0-0.4",
    "49": "电流0.4-2",
    "50": "不区分",
  };
  const Y_VALUE_BY_D_Y1 = {
    "07": "不区分",
    A07: "L1",
    J07: "BPF",
    K07: "BPF_L1",
    G07: "不区分",
    GA07: "L1",
    GJ07: "BPF",
    GK07: "BPF_L1",
    "07A": "不区分",
    A07A: "L1",
    J07A: "BPF",
    K07A: "BPF_L1",
    G07A: "不区分",
    GA07A: "L1",
    GJ07A: "BPF",
    GK07A: "BPF_L1",
    "07D": "不区分",
  };
  const Y_VALUE_BY_D_Y2 = {
    "07": "LP",
    J07: "LP_BPF",
    K07: "LP_BPF_L1",
    "07A": "LP",
    J07A: "LP_BPF",
    K07A: "LP_BPF_L1",
    "07D": "LP",
  };
  const DEFAULT_OUTPUT_VALUES = {
    1: "WCTYPE|wt.part.WTPart|com.jasolar.Part",
    19: "N型",
    30: null,
    31: "INWORK",
    32: "EA",
    33: "false",
    34: 0,
    35: "standard",
    36: "separable",
    37: "jasolar",
    38: "Design",
    39: "组件材料生命周期",
    40: "make",
    41: "ea",
    42: "false",
    43: "false",
  };

  const HALF_SLICE_AND_EXTERNAL_CODES = new Set([
    "07A",
    "A07A",
    "J07A",
    "K07A",
    "G07A",
    "GA07A",
    "GJ07A",
    "GK07A",
  ]);
  let defaultHeadArrayBuffer = null;

  function isBlank(value) {
    if (value === null || value === undefined) {
      return true;
    }
    if (typeof value === "string" && value.trim() === "") {
      return true;
    }
    return false;
  }

  function formatTwoDecimalValue(value) {
    if (isBlank(value)) {
      return 0;
    }
    const s = String(value).trim();
    const n = Number(s);
    if (!Number.isFinite(n)) {
      return value;
    }
    return Math.round(n * 100) / 100;
  }

  function ensureRef(ws, row1Based, col1Based) {
    const addr = XLSX.utils.encode_cell({ r: row1Based - 1, c: col1Based - 1 });
    if (!ws["!ref"]) {
      ws["!ref"] = "A1:" + addr;
      return;
    }
    const d = XLSX.utils.decode_range(ws["!ref"]);
    d.e.r = Math.max(d.e.r, row1Based - 1);
    d.e.c = Math.max(d.e.c, col1Based - 1);
    ws["!ref"] = XLSX.utils.encode_range(d);
  }

  function setCell(ws, row1Based, col1Based, value, opt) {
    const addr = XLSX.utils.encode_cell({ r: row1Based - 1, c: col1Based - 1 });
    if (value === null || value === undefined) {
      delete ws[addr];
      return;
    }
    const cell = {};
    if (typeof value === "number" && Number.isFinite(value)) {
      cell.t = "n";
      cell.v = value;
    } else if (typeof value === "boolean") {
      cell.t = "b";
      cell.v = value;
    } else {
      cell.t = "s";
      cell.v = String(value);
    }
    if (opt && opt.z) {
      cell.z = opt.z;
    }
    ws[addr] = cell;
    ensureRef(ws, row1Based, col1Based);
  }

  function getCell(ws, row1Based, col1Based) {
    const addr = XLSX.utils.encode_cell({ r: row1Based - 1, c: col1Based - 1 });
    const c = ws[addr];
    if (!c) {
      return undefined;
    }
    return c.v;
  }

  function prepareWorkbookFromHead(arrayBuffer) {
    const wb = XLSX.read(arrayBuffer, { type: "array", cellDates: true });
    if (!wb.SheetNames.length) {
      throw new Error("表头文件不包含任何工作表");
    }
    const firstName = wb.SheetNames[0];
    const ws = wb.Sheets[firstName];
    for (const n of [...wb.SheetNames]) {
      if (n !== firstName) {
        delete wb.Sheets[n];
      }
    }
    wb.SheetNames = [firstName];
    if (firstName !== "Sheet1") {
      wb.Sheets["Sheet1"] = ws;
      delete wb.Sheets[firstName];
      wb.SheetNames[0] = "Sheet1";
    }
    return wb;
  }

  function collectInputRows(wb) {
    const name = wb.SheetNames[0];
    const ws = wb.Sheets[name];
    if (!ws["!ref"]) {
      return [];
    }
    const range = XLSX.utils.decode_range(ws["!ref"]);
    const rows = [];
    const startRow = 2;
    const endRow = range.e.r + 1;
    for (let row = startRow; row <= endRow; row++) {
      const cVal = getCell(ws, row, 3);
      const oVal = getCell(ws, row, 15);
      const pVal = getCell(ws, row, 16);
      rows.push([cVal, oVal, pVal]);
    }
    return rows;
  }

  function splitCodeSegments(codeValue) {
    if (isBlank(codeValue)) {
      return [];
    }
    const rawText = String(codeValue).trim();
    if (rawText === "") {
      return [];
    }
    return rawText.split(".").slice(0, OUTPUT_COL_D_END - OUTPUT_COL_D_START + 1);
  }

  function formatHSegment(segmentValue) {
    const segmentText = String(segmentValue).trim();
    const m = segmentText.match(/^(\d+)([A-Za-z]?)$/);
    if (!m) {
      return segmentText;
    }
    const num = parseInt(m[1], 10);
    const suffix = m[2] || "";
    const divided = num / 100;
    const rounded = Math.round(divided * 100) / 100;
    return rounded.toFixed(2) + suffix;
  }

  function splitHForTU(hValue) {
    if (isBlank(hValue)) {
      return [null, U_DEFAULT_TEXT];
    }
    const hText = String(hValue).trim();
    const match = hText.match(/^(.*?)([A-Za-z])$/);
    if (!match) {
      return [hText, U_DEFAULT_TEXT];
    }
    return [match[1], match[2]];
  }

  function buildComposedOutputCValue(ws, outRow) {
    const parts = [];
    for (let segmentIndex = 0; segmentIndex < 10; segmentIndex++) {
      if (segmentIndex === 4) {
        const hVal = getCell(ws, outRow, OUTPUT_COL_H);
        parts.push(isBlank(hVal) ? "" : String(hVal).trim());
        continue;
      }
      const lookupTable = OUTPUT_C_LOOKUP_BY_SEGMENT_INDEX[segmentIndex];
      if (!lookupTable) {
        parts.push("");
        continue;
      }
      const sourceCol = OUTPUT_COL_D_START + segmentIndex;
      const rawVal = getCell(ws, outRow, sourceCol);
      const keyText = isBlank(rawVal) ? "" : String(rawVal).trim();
      const mapped = keyText ? lookupTable[keyText] : undefined;
      parts.push(mapped !== undefined && mapped !== null ? mapped : "");
    }
    return parts.join("/");
  }

  function resolveNValueByDAndJ(dValue, jValue) {
    const dText = isBlank(dValue) ? "" : String(dValue).trim();
    if (dText === "") {
      return null;
    }
    if (dText === "07D") {
      const jText = isBlank(jValue) ? "" : String(jValue).trim();
      return N_VALUE_BY_J_FOR_D_07D[jText] !== undefined ? N_VALUE_BY_J_FOR_D_07D[jText] : null;
    }
    return N_VALUE_BY_D[dText] !== undefined ? N_VALUE_BY_D[dText] : null;
  }

  function resolveOValueByD(dValue) {
    const dText = isBlank(dValue) ? "" : String(dValue).trim();
    if (dText === "") {
      return null;
    }
    return O_VALUE_BY_D[dText] !== undefined ? O_VALUE_BY_D[dText] : null;
  }

  function mapGet(table, key) {
    if (isBlank(key)) {
      return null;
    }
    const k = String(key).trim();
    return table[k] !== undefined ? table[k] : null;
  }

  function resolveAbValueByDF(dValue, fValue) {
    const dText = isBlank(dValue) ? "" : String(dValue).trim();
    const fText = isBlank(fValue) ? "" : String(fValue).trim();
    if (fText === "") {
      return null;
    }
    if (fText === "54" && HALF_SLICE_AND_EXTERNAL_CODES.has(dText)) {
      return "07A02001";
    }
    if (fText === "59" && HALF_SLICE_AND_EXTERNAL_CODES.has(dText)) {
      return "07A04001";
    }
    if (fText === "63" && dText === "07D") {
      return "07D06001";
    }
    return mapGet(AB_VALUE_BY_F, fText);
  }

  function isSegment7In48To50(jValue) {
    if (isBlank(jValue)) {
      return false;
    }
    const n = parseInt(String(jValue).trim(), 10);
    if (!Number.isFinite(n)) {
      return false;
    }
    return n >= 48 && n <= 50;
  }

  function resolveYValueByDAndJ(dValue, jValue) {
    const dText = isBlank(dValue) ? "" : String(dValue).trim();
    if (dText === "") {
      return null;
    }
    if (isSegment7In48To50(jValue)) {
      return Y_VALUE_BY_D_Y2[dText] !== undefined ? Y_VALUE_BY_D_Y2[dText] : null;
    }
    return Y_VALUE_BY_D_Y1[dText] !== undefined ? Y_VALUE_BY_D_Y1[dText] : null;
  }

  function executeConvert(headBuf, inputBuf, inputFileName) {
    const wbOut = prepareWorkbookFromHead(headBuf);
    const wsOut = wbOut.Sheets.Sheet1;
    const wbIn = XLSX.read(inputBuf, { type: "array", cellDates: true });
    const rows = collectInputRows(wbIn);
    rows.forEach(function (rowTuple, idx) {
      const cVal = rowTuple[0];
      const oVal = rowTuple[1];
      const pVal = rowTuple[2];
      const outRow = OUTPUT_ROW_DATA_START + idx;
      Object.keys(DEFAULT_OUTPUT_VALUES).forEach(function (colStr) {
        const columnIndex = parseInt(colStr, 10);
        const dv = DEFAULT_OUTPUT_VALUES[columnIndex];
        if (dv !== null && dv !== undefined) {
          setCell(wsOut, outRow, columnIndex, dv);
        }
      });
      setCell(wsOut, outRow, OUTPUT_COL_B, cVal);
      const outputBValue = getCell(wsOut, outRow, OUTPUT_COL_B);
      const codeSegments = splitCodeSegments(outputBValue);
      codeSegments.forEach(function (segmentText, segmentIndex) {
        let outputCol = OUTPUT_COL_D_START + segmentIndex;
        let outputValue = segmentText;
        if (outputCol === OUTPUT_COL_H) {
          outputValue = formatHSegment(segmentText);
        }
        setCell(wsOut, outRow, outputCol, outputValue);
      });
      const hValue = getCell(wsOut, outRow, OUTPUT_COL_H);
      setCell(wsOut, outRow, OUTPUT_COL_C, buildComposedOutputCValue(wsOut, outRow));
      const tu = splitHForTU(hValue);
      setCell(wsOut, outRow, OUTPUT_COL_T, tu[0]);
      setCell(wsOut, outRow, OUTPUT_COL_U, tu[1]);
      const dValue = getCell(wsOut, outRow, OUTPUT_COL_D);
      const fValue = getCell(wsOut, outRow, OUTPUT_COL_F);
      const jValue = getCell(wsOut, outRow, OUTPUT_COL_J);
      const mValue = getCell(wsOut, outRow, OUTPUT_COL_M);
      setCell(wsOut, outRow, OUTPUT_COL_N, resolveNValueByDAndJ(dValue, jValue));
      setCell(wsOut, outRow, OUTPUT_COL_O, resolveOValueByD(dValue));
      setCell(wsOut, outRow, OUTPUT_COL_P, mapGet(P_VALUE_BY_F, fValue));
      setCell(wsOut, outRow, OUTPUT_COL_Q, mapGet(Q_VALUE_BY_F, fValue));
      setCell(wsOut, outRow, OUTPUT_COL_R, mapGet(R_VALUE_BY_F, fValue));
      setCell(wsOut, outRow, OUTPUT_COL_AB, resolveAbValueByDF(dValue, fValue));
      setCell(wsOut, outRow, OUTPUT_COL_AC, mapGet(AC_VALUE_BY_F, fValue));
      setCell(wsOut, outRow, OUTPUT_COL_V, mapGet(V_VALUE_BY_M, mValue));
      setCell(wsOut, outRow, OUTPUT_COL_W, mapGet(W_VALUE_BY_M, mValue));
      setCell(wsOut, outRow, OUTPUT_COL_X, mapGet(X_VALUE_BY_J, jValue));
      setCell(wsOut, outRow, OUTPUT_COL_Y, resolveYValueByDAndJ(dValue, jValue));
      const zVal = formatTwoDecimalValue(oVal);
      const aaVal = formatTwoDecimalValue(pVal);
      setCell(wsOut, outRow, OUTPUT_COL_Z, zVal, { z: TWO_DECIMAL_PATTERN });
      setCell(wsOut, outRow, OUTPUT_COL_AA, aaVal, { z: TWO_DECIMAL_PATTERN });
    });
    const base = (inputFileName || "export").replace(/\.[^/.]+$/, "");
    const outName = base + "_plm.xlsx";
    const out = XLSX.write(wbOut, { bookType: "xlsx", type: "array" });
    return { name: outName, data: out };
  }

  function setStatus(msg, isErr) {
    const el = document.getElementById("status");
    el.textContent = msg;
    el.className = "status" + (isErr ? " err" : "");
  }

  function readFileAsArrayBuffer(file) {
    return new Promise(function (resolve, reject) {
      const r = new FileReader();
      r.onload = function () {
        resolve(r.result);
      };
      r.onerror = function () {
        reject(r.error);
      };
      r.readAsArrayBuffer(file);
    });
  }
  function loadDefaultHeadFile() {
    return fetch(DEFAULT_HEAD_FILE_URL, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.arrayBuffer();
      })
      .then(function (arrayBuffer) {
        defaultHeadArrayBuffer = arrayBuffer;
      })
      .catch(function () {
        defaultHeadArrayBuffer = null;
      });
  }

  document.getElementById("inputFile").addEventListener("change", function (e) {
    const f = e.target.files[0];
    document.getElementById("inputLabel").textContent = f ? f.name : "未选择文件";
  });

  document.getElementById("btnConvert").addEventListener("click", function () {
    const inputEl = document.getElementById("inputFile");
    const inputFile = inputEl.files[0];
    if (!inputFile) {
      setStatus("请先选择 ERP 输入文件。", true);
      return;
    }
    if (!defaultHeadArrayBuffer) {
      setStatus("未检测到默认 head.xlsx，请确认文件已部署在当前页面目录。", true);
      return;
    }
    const btn = document.getElementById("btnConvert");
    btn.disabled = true;
    setStatus("正在转换…", false);
    Promise.all([Promise.resolve(defaultHeadArrayBuffer), readFileAsArrayBuffer(inputFile)])
      .then(function (bufs) {
        const result = executeConvert(bufs[0], bufs[1], inputFile.name);
        const blob = new Blob([result.data], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = result.name;
        a.click();
        URL.revokeObjectURL(url);
        setStatus("完成：已下载 " + result.name, false);
      })
      .catch(function (err) {
        setStatus("失败：" + (err && err.message ? err.message : String(err)), true);
      })
      .finally(function () {
        btn.disabled = false;
      });
  });
  loadDefaultHeadFile();
})();
