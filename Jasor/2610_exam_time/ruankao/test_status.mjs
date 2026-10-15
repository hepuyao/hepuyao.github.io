import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { computeCityStatus, daysUntil } from "./status.js";

/** @param {string} s YYYY-MM-DD HH:mm local */
function dt(s) {
  const [datePart, timePart] = s.split(" ");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm] = timePart.split(":").map(Number);
  return new Date(y, m - 1, d, hh, mm);
}

/** @param {string} s YYYY-MM-DD local */
function day(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

describe("computeCityStatus", () => {
  it("upcoming: today 2026-11-01, window 2026-11-14..2026-11-21", () => {
    const status = computeCityStatus(
      day("2026-11-01"),
      dt("2026-11-14 00:00"),
      dt("2026-11-21 23:59"),
      null,
      null,
      "",
    );
    assert.equal(status.kind, "upcoming");
    assert.equal(status.days, 13);
    assert.match(status.message, /还剩 13 天/);
  });

  it("open: today 2026-11-15", () => {
    const status = computeCityStatus(
      day("2026-11-15"),
      dt("2026-11-14 00:00"),
      dt("2026-11-21 23:59"),
      null,
      null,
      "",
    );
    assert.equal(status.kind, "open");
    assert.equal(status.deadline, "2026-11-21");
    assert.match(status.message, /报名进行中/);
  });

  it("estimated: today 2026-10-14, ended Sep window, ref 2026 H1", () => {
    const today = day("2026-10-14");
    const status = computeCityStatus(
      today,
      dt("2026-09-11 00:00"),
      dt("2026-09-17 23:59"),
      dt("2026-03-27 00:00"),
      dt("2026-04-02 23:59"),
      "2026年上半年软考",
    );
    assert.equal(status.kind, "estimated");
    assert.equal(
      status.days,
      daysUntil(today, day("2027-03-27")),
    );
    assert.match(status.message, /大约还剩/);
    assert.match(status.note ?? "", /2026年上半年软考/);
  });

  it("unknown without reference after end", () => {
    const status = computeCityStatus(
      day("2026-10-14"),
      dt("2026-09-11 00:00"),
      dt("2026-09-17 23:59"),
      null,
      null,
      "",
    );
    assert.equal(status.kind, "unknown");
    assert.match(status.message, /暂无法估算/);
  });
});
