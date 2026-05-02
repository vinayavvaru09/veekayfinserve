"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  FileText,
  Shield,
  Building2,
  MessageSquare,
  ScrollText,
  LogOut,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard/notices", label: "Renewal Notices", icon: FileText },
  { href: "/dashboard/policies", label: "Policies", icon: Shield },
  { href: "/dashboard/providers", label: "Providers", icon: Building2 },
  { href: "/dashboard/templates", label: "Message Templates", icon: MessageSquare },
  { href: "/dashboard/logs", label: "Processing Logs", icon: ScrollText },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/auth/login");
  }

  return (
    <aside className="w-64 min-h-screen bg-brand-900 flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-brand-700">
        <p className="text-white font-bold text-lg leading-tight">Veekay Finserve</p>
        <p className="text-brand-100 text-xs mt-0.5">Renewal Dashboard</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-brand-600 text-white"
                  : "text-brand-100 hover:bg-brand-700 hover:text-white"
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Sign out */}
      <div className="px-3 py-4 border-t border-brand-700">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-brand-100 hover:bg-brand-700 hover:text-white transition-colors"
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
