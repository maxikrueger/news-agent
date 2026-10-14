"use client";

import { useSession, signOut } from "next-auth/react";
import Link from "next/link";

interface NavbarProps {
  onMenuClick?: () => void;
}

export default function Navbar({ onMenuClick }: NavbarProps) {
  const { data: session } = useSession();

  return (
    <nav className="bg-white shadow-sm fixed top-0 left-0 right-0 z-40 md:relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-4">
            {/* Hamburger Menu - Mobile Only */}
            <button
              onClick={onMenuClick}
              className="md:hidden p-2 rounded-md text-gray-700 hover:bg-gray-100"
              aria-label="Toggle menu"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>

            <Link href="/dashboard" className="text-lg sm:text-xl font-bold text-blue-600">
              📰 News Agent
            </Link>
          </div>

          <div className="flex items-center space-x-2 sm:space-x-4">
            <span className="hidden sm:inline text-sm text-gray-700">
              {session?.user?.email}
            </span>
            <button
              onClick={() => signOut({ redirect: true, callbackUrl: "/auth/login" })}
              className="px-3 py-2 text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
