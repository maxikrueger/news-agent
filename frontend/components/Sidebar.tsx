"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: "📊" },
  { name: "Sources", href: "/dashboard/sources", icon: "📰" },
  { name: "Schedules", href: "/dashboard/schedules", icon: "⏰" },
  { name: "Digests", href: "/dashboard/digests", icon: "📑" },
  { name: "Settings", href: "/dashboard/settings", icon: "⚙️" },
];

interface SidebarProps {
  onClose?: () => void;
}

export default function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname();

  return (
    <div className="h-full bg-white flex flex-col overflow-y-auto">
      <div className="flex-1 py-6 px-4 sm:px-6 lg:px-8">
        <nav className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={onClose}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm sm:text-base font-medium transition-colors ${
                  isActive
                    ? "bg-blue-50 text-blue-600"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
