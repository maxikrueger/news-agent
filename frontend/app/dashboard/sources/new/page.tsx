"use client";

import { useRouter } from "next/navigation";
import SourceForm from "@/components/SourceForm";

export default function NewSourcePage() {
  const router = useRouter();

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">Add New Source</h1>
      <p className="mt-2 text-gray-600">Create a new RSS source</p>

      <div className="mt-8 max-w-2xl">
        <SourceForm
          onSuccess={() => router.push("/dashboard/sources")}
        />
      </div>
    </div>
  );
}
