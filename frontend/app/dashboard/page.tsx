"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import api from "@/lib/api";
import { Digest, Schedule, Source } from "@/lib/types";

interface Stats {
  activeSources: number;
  activeSchedules: number;
  digests: number;
}

export default function DashboardPage() {
  const { data: session } = useSession();
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [sources, schedules, digests] = await Promise.all([
          api.get<Source[]>("/api/sources"),
          api.get<Schedule[]>("/api/schedules"),
          api.get<Digest[]>("/api/digests"),
        ]);
        setStats({
          activeSources: sources.data.filter((s) => s.is_active).length,
          activeSchedules: schedules.data.filter((s) => s.is_active).length,
          digests: digests.data.length,
        });
      } catch {
        setStats(null);
      }
    };

    fetchStats();
  }, []);

  const show = (value: number | undefined) => (value === undefined ? "–" : String(value));

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {session?.user?.email?.split("@")[0]}!
        </h1>
        <p className="mt-2 text-gray-600">
          Manage your news sources and digest schedules
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Add Source"
          description="Add new RSS feeds to your collection"
          href="/dashboard/sources/new"
          icon="➕"
          color="blue"
        />
        <QuickActionCard
          title="Create Schedule"
          description="Set up a new digest generation schedule"
          href="/dashboard/schedules/new"
          icon="🕐"
          color="green"
        />
        <QuickActionCard
          title="View Digests"
          description="Browse previously generated digests"
          href="/dashboard/digests"
          icon="📚"
          color="purple"
        />
      </div>

      <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
        <StatCard title="Active Sources" value={show(stats?.activeSources)} />
        <StatCard title="Active Schedules" value={show(stats?.activeSchedules)} />
        <StatCard title="Recent Digests" value={show(stats?.digests)} />
      </div>
    </div>
  );
}

function QuickActionCard({
  title,
  description,
  href,
  icon,
  color,
}: {
  title: string;
  description: string;
  href: string;
  icon: string;
  color: string;
}) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-600 hover:bg-blue-100",
    green: "bg-green-50 text-green-600 hover:bg-green-100",
    purple: "bg-purple-50 text-purple-600 hover:bg-purple-100",
  };

  return (
    <Link
      href={href}
      className={`block p-6 rounded-lg border border-gray-200 shadow-sm transition-colors ${
        colorClasses[color as keyof typeof colorClasses]
      }`}
    >
      <div className="flex items-start space-x-4">
        <span className="text-3xl">{icon}</span>
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-sm opacity-75">{description}</p>
        </div>
      </div>
    </Link>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-gray-600 text-sm">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
    </div>
  );
}
