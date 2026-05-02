import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function daysUntil(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(dateStr);
  return Math.round((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export const POLICY_TYPES = ["Motor", "Life", "Medical"] as const;

export const NOTICE_STATUSES = [
  { value: "pending_automation", label: "Pending Automation", color: "bg-yellow-100 text-yellow-800" },
  { value: "pending_manual_upload", label: "Needs Upload", color: "bg-orange-100 text-orange-800" },
  { value: "completed", label: "Completed", color: "bg-green-100 text-green-800" },
  { value: "failed", label: "Failed", color: "bg-red-100 text-red-800" },
] as const;

export function getStatusStyle(status: string): string {
  return NOTICE_STATUSES.find((s) => s.value === status)?.color ?? "bg-gray-100 text-gray-800";
}

export function getStatusLabel(status: string): string {
  return NOTICE_STATUSES.find((s) => s.value === status)?.label ?? status;
}
