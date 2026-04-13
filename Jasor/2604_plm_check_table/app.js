/* global XLSX */
(function () {
  "use strict";
  const DATA_START_ROW = 7;
  const COL_B_INDEX = 2;
  const COL_AA_INDEX = 27;
  const EXCEL_FILE_PATTERN = /\.(xlsx|xlsm|xls|csv)$/i;
  function isBlank(value) {
    if (value === null || value === undefined) {
      return true;
    }
    if (typeof value === "string" && value.trim() === "") {
      return true;
    }
    return false;
  }
  function normalizeCell(value) {
    if (isBlank(value)) {
      return "";
    }
    return String(value).trim();
  }
  function getCellValue(ws, row1Based, col1Based) {
    const cellAddress = XLSX.utils.encode_cell({ r: row1Based - 1, c: col1Based - 1 });
    const cell = ws[cellAddress];
    if (!cell) {
      return undefined;
    }
    return cell.v;
  }
  function setStatus(message, isError) {
    const statusElement = document.getElementById("status");
    statusElement.textContent = message;
    statusElement.className = "status" + (isError ? " err" : "");
  }
  function setResult(lines) {
    const resultElement = document.getElementById("result");
    resultElement.textContent = lines.join("\n");
  }
  function readFileAsArrayBuffer(file) {
    return new Promise(function (resolve, reject) {
      const reader = new FileReader();
      reader.onload = function () {
        resolve(reader.result);
      };
      reader.onerror = function () {
        reject(reader.error);
      };
      reader.readAsArrayBuffer(file);
    });
  }
  function collectRowsFromWorkbook(workbook, sourceName) {
    const rows = [];
    workbook.SheetNames.forEach(function (sheetName) {
      const worksheet = workbook.Sheets[sheetName];
      if (!worksheet || !worksheet["!ref"]) {
        return;
      }
      const range = XLSX.utils.decode_range(worksheet["!ref"]);
      const endRow = range.e.r + 1;
      for (let rowIndex = DATA_START_ROW; rowIndex <= endRow; rowIndex++) {
        const bValue = normalizeCell(getCellValue(worksheet, rowIndex, COL_B_INDEX));
        const aaValue = normalizeCell(getCellValue(worksheet, rowIndex, COL_AA_INDEX));
        if (bValue === "") {
          continue;
        }
        rows.push({
          sourceName: sourceName,
          sheetName: sheetName,
          rowIndex: rowIndex,
          bValue: bValue,
          aaValue: aaValue,
        });
      }
    });
    return rows;
  }
  function buildTotalIndex(totalRows) {
    const indexByBValue = new Map();
    totalRows.forEach(function (row) {
      if (!indexByBValue.has(row.bValue)) {
        indexByBValue.set(row.bValue, []);
      }
      indexByBValue.get(row.bValue).push(row);
    });
    return indexByBValue;
  }
  function compareRows(checkRows, totalIndex) {
    const outputLines = [];
    let duplicateCount = 0;
    let sameAaCount = 0;
    let differentAaCount = 0;
    checkRows.forEach(function (checkRow) {
      const matchedRows = totalIndex.get(checkRow.bValue);
      if (!matchedRows || matchedRows.length === 0) {
        return;
      }
      duplicateCount += 1;
      matchedRows.forEach(function (matchedRow) {
        const isSameAa = checkRow.aaValue === matchedRow.aaValue;
        if (isSameAa) {
          sameAaCount += 1;
        } else {
          differentAaCount += 1;
        }
        outputLines.push(
          [
            "检测数据表在总数据中命中：",
            "检测表[" + checkRow.sourceName + " / " + checkRow.sheetName + " / 第" + checkRow.rowIndex + "行]",
            "总数据[" + matchedRow.sourceName + " / " + matchedRow.sheetName + " / 第" + matchedRow.rowIndex + "行]",
            "B列重复(" + checkRow.bValue + ")",
            isSameAa ? "AA列也重复" : "AA列不同",
            "检测表AA=" + (checkRow.aaValue === "" ? "(空)" : checkRow.aaValue),
            "总数据AA=" + (matchedRow.aaValue === "" ? "(空)" : matchedRow.aaValue),
          ].join("，")
        );
      });
    });
    return {
      outputLines: outputLines,
      duplicateCount: duplicateCount,
      sameAaCount: sameAaCount,
      differentAaCount: differentAaCount,
    };
  }
  async function executeCheck() {
    const checkFileInput = document.getElementById("checkFile");
    const totalFolderInput = document.getElementById("totalFolder");
    const checkFile = checkFileInput.files[0];
    const totalFiles = Array.from(totalFolderInput.files || []).filter(function (file) {
      return EXCEL_FILE_PATTERN.test(file.name);
    });
    if (!checkFile) {
      throw new Error("请先选择检测数据表。");
    }
    if (totalFiles.length === 0) {
      throw new Error("请先选择包含 Excel 的总数据文件夹。");
    }
    setStatus("正在读取检测数据表...", false);
    const checkFileBuffer = await readFileAsArrayBuffer(checkFile);
    const checkWorkbook = XLSX.read(checkFileBuffer, { type: "array", cellDates: true });
    const checkRows = collectRowsFromWorkbook(checkWorkbook, checkFile.name);
    if (checkRows.length === 0) {
      throw new Error("检测数据表中未找到可用 B 列数据。");
    }
    setStatus("正在读取总数据文件夹，共 " + totalFiles.length + " 个文件...", false);
    let totalRows = [];
    for (const totalFile of totalFiles) {
      const totalBuffer = await readFileAsArrayBuffer(totalFile);
      const totalWorkbook = XLSX.read(totalBuffer, { type: "array", cellDates: true });
      const fileRows = collectRowsFromWorkbook(totalWorkbook, totalFile.webkitRelativePath || totalFile.name);
      totalRows = totalRows.concat(fileRows);
    }
    const totalIndex = buildTotalIndex(totalRows);
    const compareResult = compareRows(checkRows, totalIndex);
    const summaryLines = [
      "检测完成",
      "检测表有效行数: " + checkRows.length,
      "总数据有效行数: " + totalRows.length,
      "检测表中 B 列在总数据中命中的行数: " + compareResult.duplicateCount,
      "命中后 AA 一致条数: " + compareResult.sameAaCount,
      "命中后 AA 不一致条数: " + compareResult.differentAaCount,
      "----------------------------------------",
    ];
    if (compareResult.outputLines.length === 0) {
      summaryLines.push("未发现 B 列重复记录。");
    } else {
      summaryLines.push.apply(summaryLines, compareResult.outputLines);
    }
    setResult(summaryLines);
    setStatus("完成，共输出 " + compareResult.outputLines.length + " 条命中记录。", false);
  }
  document.getElementById("checkFile").addEventListener("change", function (event) {
    const file = event.target.files[0];
    document.getElementById("checkFileLabel").textContent = file ? file.name : "未选择文件";
  });
  document.getElementById("totalFolder").addEventListener("change", function (event) {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) {
      document.getElementById("totalFolderLabel").textContent = "未选择文件夹";
      return;
    }
    const firstFilePath = files[0].webkitRelativePath || files[0].name;
    const folderName = firstFilePath.split("/")[0];
    document.getElementById("totalFolderLabel").textContent = folderName + "（共 " + files.length + " 个文件）";
  });
  document.getElementById("btnCheck").addEventListener("click", function () {
    const button = document.getElementById("btnCheck");
    button.disabled = true;
    setResult(["正在执行检测..."]);
    executeCheck()
      .catch(function (error) {
        setStatus("失败：" + (error && error.message ? error.message : String(error)), true);
        setResult(["检测失败", String(error && error.message ? error.message : error)]);
      })
      .finally(function () {
        button.disabled = false;
      });
  });
})();
