export function formatChatTimestamp(date: Date): string {
  const now = new Date();

  const isSameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  const yesterday = new Date();
  yesterday.setDate(now.getDate() - 1);

  const time = date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (isSameDay(date, now)) {
    return `Heute, ${time}`;
  }

  if (isSameDay(date, yesterday)) {
    return `Gestern, ${time}`;
  }

  const sameYear = date.getFullYear() === now.getFullYear();

  return date.toLocaleString([], {
    day: "2-digit",
    month: "2-digit",
    ...(sameYear ? {} : { year: "numeric" }),
    hour: "2-digit",
    minute: "2-digit",
  });
}
