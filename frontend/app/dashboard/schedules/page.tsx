"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ScheduleCard from "@/components/ScheduleCard";
import api from "@/lib/api";
import { Schedule, getApiErrorDetail } from "@/lib/types";

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const fetchSchedules = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const res = await api.get<Schedule[]>("/api/schedules");
        setSchedules(res.data);
      } catch (err: unknown) {
        setError(getApiErrorDetail(err) || "Failed to load schedules");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSchedules();
  }, [reloadKey]);

  const reloadSchedules = () => setReloadKey((key) => key + 1);

  const handleScheduleDeleted = () => {
    reloadSchedules();
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Schedules</h1>
          <p className="mt-2 text-gray-600">
            Manage digest generation schedules
          </p>
        </div>
        <Link
          href="/dashboard/schedules/new"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          + Create Schedule
        </Link>
      </div>

      {error && (
        <div className="mt-6 rounded-md bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      )}

      {isLoading ? (
        <div className="mt-6 text-center">
          <p className="text-gray-600">Loading schedules...</p>
        </div>
      ) : schedules.length === 0 ? (
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-4">No schedules yet</p>
          <Link
            href="/dashboard/schedules/new"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-50 hover:bg-blue-100"
          >
            Create your first schedule
          </Link>
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {schedules.map((schedule) => (
            <ScheduleCard
              key={schedule.id}
              schedule={schedule}
              onDelete={handleScheduleDeleted}
            />
          ))}
        </div>
      )}
    </div>
  );
}
