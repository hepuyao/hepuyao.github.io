/** @param {Date} d */
export function toDateOnly(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

/** @param {Date} today @param {Date} target */
export function daysUntil(today, target) {
  const ms = toDateOnly(target).getTime() - toDateOnly(today).getTime();
  return Math.max(0, Math.round(ms / 86400000));
}

/** @param {Date} dateObj @param {number} years */
export function shiftYears(dateObj, years) {
  const d = new Date(dateObj.getTime());
  const month = d.getMonth();
  d.setFullYear(d.getFullYear() + years);
  if (d.getMonth() !== month) {
    d.setDate(0);
  }
  return d;
}

/** @param {Date} d */
export function ymd(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * @param {Date} today
 * @param {Date} signupStart
 * @param {Date} signupEnd
 * @param {Date | null} referenceStart
 * @param {Date | null} referenceEnd
 * @param {string} referenceBatchName
 */
export function computeCityStatus(
  today,
  signupStart,
  signupEnd,
  referenceStart,
  referenceEnd,
  referenceBatchName,
) {
  const startDay = toDateOnly(signupStart);
  const endDay = toDateOnly(signupEnd);
  const t = toDateOnly(today);
  if (t < startDay) {
    const days = daysUntil(t, startDay);
    return {
      kind: "upcoming",
      message: `还剩 ${days} 天`,
      deadline: null,
      days,
      rangeStart: signupStart,
      rangeEnd: signupEnd,
      note: null,
    };
  }
  if (t >= startDay && t <= endDay) {
    const deadline = ymd(endDay);
    return {
      kind: "open",
      message: `报名进行中，报名截止日期为 ${deadline}`,
      deadline,
      days: null,
      rangeStart: signupStart,
      rangeEnd: signupEnd,
      note: null,
    };
  }
  if (!referenceStart || !referenceEnd) {
    return {
      kind: "unknown",
      message: "暂无法估算下一批次",
      deadline: null,
      days: null,
      rangeStart: null,
      rangeEnd: null,
      note: null,
    };
  }
  let estStart = shiftYears(referenceStart, 1);
  let estEnd = shiftYears(referenceEnd, 1);
  if (toDateOnly(estStart) < t) {
    estStart = shiftYears(referenceStart, 2);
    estEnd = shiftYears(referenceEnd, 2);
  }
  if (toDateOnly(estStart) < t) {
    return {
      kind: "unknown",
      message: "暂无法估算下一批次",
      deadline: null,
      days: null,
      rangeStart: null,
      rangeEnd: null,
      note: null,
    };
  }
  const days = daysUntil(t, estStart);
  const note = referenceBatchName
    ? `参考 ${referenceBatchName} 推算`
    : "按历史同半年推算";
  return {
    kind: "estimated",
    message: `大约还剩 ${days} 天`,
    deadline: null,
    days,
    rangeStart: estStart,
    rangeEnd: estEnd,
    note,
  };
}
