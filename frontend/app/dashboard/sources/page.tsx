"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import SourceCard from "@/components/SourceCard";
import api from "@/lib/api";
import { Source, getApiErrorDetail } from "@/lib/types";

const QUICK_ADD_SOURCES = [
  { name: "Tagesschau", url: "https://www.tagesschau.de/xml/rss2/", category: "News" },
  { name: "Der Spiegel", url: "https://www.spiegel.de/schlagzeilen/index.rss", category: "News" },
  { name: "NPR News", url: "https://feeds.npr.org/1001/rss.xml", category: "News" },
  { name: "Hacker News", url: "https://news.ycombinator.com/rss", category: "Tech" },
  { name: "TechCrunch", url: "https://techcrunch.com/feed/", category: "Tech" },
];

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addingSource, setAddingSource] = useState<string | null>(null);

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const fetchSources = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const res = await api.get<Source[]>("/api/sources");
        setSources(res.data);
      } catch (err: unknown) {
        setError(getApiErrorDetail(err) || "Failed to load sources");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSources();
  }, [reloadKey]);

  const reloadSources = () => setReloadKey((key) => key + 1);

  const handleSourceDeleted = () => {
    reloadSources();
  };

  const handleQuickAdd = async (source: typeof QUICK_ADD_SOURCES[0]) => {
    setAddingSource(source.name);
    try {
      await api.post("/api/sources", {
        name: source.name,
        url: source.url,
        category: source.category,
      });
      reloadSources();
    } catch (err: unknown) {
      setError(getApiErrorDetail(err) || `Failed to add ${source.name}`);
    } finally {
      setAddingSource(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">RSS Sources</h1>
          <p className="mt-2 text-gray-600">
            Manage your RSS feeds and sources
          </p>
        </div>
        <Link
          href="/dashboard/sources/new"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          + Add Source
        </Link>
      </div>

      {error && (
        <div className="mt-6 rounded-md bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      )}

      {isLoading ? (
        <div className="mt-6 text-center">
          <p className="text-gray-600">Loading sources...</p>
        </div>
      ) : (
        <>
          {sources.length === 0 ? (
            <div className="mt-12 text-center mb-8">
              <p className="text-gray-600 mb-4">No sources yet</p>
              <Link
                href="/dashboard/sources/new"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-50 hover:bg-blue-100"
              >
                Create your first source
              </Link>
            </div>
          ) : (
            <div className="mt-6 space-y-4">
              {sources.map((source) => (
                <SourceCard
                  key={source.id}
                  source={source}
                  onDelete={handleSourceDeleted}
                />
              ))}
            </div>
          )}

          {(() => {
            const existingUrls = new Set(sources.map((s) => s.url));
            const available = QUICK_ADD_SOURCES.filter((s) => !existingUrls.has(s.url));
            if (available.length === 0) return null;
            return (
              <div className="mt-8 bg-gray-50 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Add Popular Sources</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {available.map((source) => (
                    <button
                      key={source.name}
                      onClick={() => handleQuickAdd(source)}
                      disabled={addingSource === source.name}
                      className="p-3 text-left border border-gray-300 rounded-md hover:border-blue-500 hover:bg-blue-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="font-medium text-gray-900">{source.name}</div>
                      <div className="text-sm text-gray-500">{source.category}</div>
                      {addingSource === source.name && (
                        <div className="mt-2 text-xs text-blue-600">Adding...</div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
