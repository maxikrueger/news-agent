"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import ScheduleForm from "@/components/ScheduleForm";
import api from "@/lib/api";
import { Schedule, Source, getApiErrorDetail } from "@/lib/types";

export default function EditSchedulePage() {
  const router = useRouter();
  const params = useParams();
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const scheduleId = params.id;

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const [scheduleRes, sourcesRes] = await Promise.all([
          api.get<Schedule>(`/api/schedules/${scheduleId}`),
          api.get<Source[]>("/api/sources"),
        ]);
        setSchedule(scheduleRes.data);
        setSources(sourcesRes.data);
      } catch (err: unknown) {
        setError(getApiErrorDetail(err) || "Failed to load data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [scheduleId]);

  if (isLoading) {
    return <div className="text-center py-6">Loading schedule...</div>;
  }

  if (error || !schedule) {
    return (
      <div>
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">
            {error || "Schedule not found"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">Edit Schedule</h1>
      <p className="mt-2 text-gray-600">Update digest schedule settings</p>

      <div className="mt-8 max-w-2xl">
        <ScheduleForm
          initialData={schedule}
          sources={sources}
          onSuccess={() => router.push("/dashboard/schedules")}
        />
      </div>
    </div>
  );
}
