"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ScheduleForm from "@/components/ScheduleForm";
import api from "@/lib/api";
import { Source } from "@/lib/types";

export default function NewSchedulePage() {
  const router = useRouter();
  const [sources, setSources] = useState<Source[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSources = async () => {
      try {
        const res = await api.get<Source[]>("/api/sources");
        setSources(res.data);
      } catch {
        console.error("Failed to load sources");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSources();
  }, []);

  if (isLoading) {
    return <div className="text-center py-6">Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">Create Schedule</h1>
      <p className="mt-2 text-gray-600">Set up a new digest generation schedule</p>

      <div className="mt-8 max-w-2xl">
        <ScheduleForm
          sources={sources}
          onSuccess={() => router.push("/dashboard/schedules")}
        />
      </div>
    </div>
  );
}
