"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Digest, getApiErrorDetail } from "@/lib/types";

export default function DigestsPage() {
  const [digests, setDigests] = useState<Digest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDigest, setSelectedDigest] = useState<Digest | null>(null);

  useEffect(() => {
    const fetchDigests = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const res = await api.get<Digest[]>("/api/digests");
        setDigests(res.data || []);
      } catch (err: unknown) {
        setError(getApiErrorDetail(err) || "Failed to load digests");
      } finally {
        setIsLoading(false);
      }
    };

    fetchDigests();
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Digest History</h1>
        <p className="mt-2 text-gray-600">
          View previously generated digests
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Digest List */}
        <div className="lg:col-span-1">
          {isLoading ? (
            <div className="text-center py-6">
              <p className="text-gray-600">Loading digests...</p>
            </div>
          ) : digests.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-600">No digests yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {digests.map((digest) => (
                <button
                  key={digest.id}
                  onClick={() => setSelectedDigest(digest)}
                  className={`w-full text-left p-4 rounded-lg border-2 transition-colors ${
                    selectedDigest?.id === digest.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 bg-white hover:border-gray-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">
                        {formatDate(digest.created_at)}
                      </p>
                      <p className="text-sm text-gray-500">
                        {digest.status === "generated" ? "✓" : "⚠"} {digest.status}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Preview */}
        <div className="lg:col-span-2">
          {selectedDigest ? (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">
                    Digest Preview
                  </h2>
                  <p className="mt-1 text-sm text-gray-600">
                    Generated: {formatDate(selectedDigest.created_at)}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    selectedDigest.status === "generated"
                      ? "bg-green-100 text-green-800"
                      : "bg-yellow-100 text-yellow-800"
                  }`}
                >
                  {selectedDigest.status}
                </span>
              </div>

              <div className="prose prose-sm max-w-none">
                <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-96">
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                    {selectedDigest.content_text || "No content available"}
                  </pre>
                </div>
              </div>

              <div className="mt-6">
                <button
                  onClick={() =>
                    navigator.clipboard.writeText(selectedDigest.content_text)
                  }
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Copy to Clipboard
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-6 text-center">
              <p className="text-gray-500">
                Select a digest from the list to preview
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
