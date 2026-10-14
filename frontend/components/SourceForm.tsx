"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { sourceSchema, SourceFormData } from "@/lib/schemas";
import api from "@/lib/api";
import { FeedTestResult, Source, SOURCE_CATEGORIES, getApiErrorDetail } from "@/lib/types";

const CATEGORIES = SOURCE_CATEGORIES;

interface SourceFormProps {
  initialData?: Source;
  onSuccess: () => void;
}

export default function SourceForm({ initialData, onSuccess }: SourceFormProps) {
  const [error, setError] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<FeedTestResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<SourceFormData>({
    resolver: zodResolver(sourceSchema),
    defaultValues: initialData,
  });

  const urlValue = useWatch({ control, name: "url" });

  const onSubmit = async (data: SourceFormData) => {
    setIsSubmitting(true);
    setError(null);

    try {
      if (initialData?.id) {
        await api.put(`/api/sources/${initialData.id}`, data);
      } else {
        await api.post("/api/sources", data);
      }
      onSuccess();
    } catch (err: unknown) {
      setError(getApiErrorDetail(err) || "Failed to save source");
    } finally {
      setIsSubmitting(false);
    }
  };

  const testFeed = async () => {
    if (!urlValue) {
      setError("URL is required to test feed");
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      const res = await api.post<FeedTestResult>("/api/sources/test", { url: urlValue });
      setTestResult(res.data);
    } catch (err: unknown) {
      setTestResult({
        valid: false,
        error: getApiErrorDetail(err) || "Failed to validate feed",
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Source Name
        </label>
        <input
          {...register("name")}
          type="text"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="e.g., BBC News"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          RSS Feed URL
        </label>
        <input
          {...register("url")}
          type="url"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="https://example.com/feed.rss"
        />
        {errors.url && (
          <p className="mt-1 text-sm text-red-600">{errors.url.message}</p>
        )}
        {urlValue && (
          <button
            type="button"
            onClick={testFeed}
            disabled={isTesting}
            className="mt-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-blue-600 bg-blue-50 hover:bg-blue-100 disabled:opacity-50"
          >
            {isTesting ? "Testing..." : "Test Feed"}
          </button>
        )}
        {testResult && (
          <div className={`mt-3 p-3 rounded-md ${testResult.valid ? "bg-green-50" : "bg-red-50"}`}>
            {testResult.valid ? (
              <>
                <p className="text-sm font-medium text-green-800">✓ Feed is valid</p>
                <p className="text-sm text-green-700">
                  Found {testResult.entries} articles
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-medium text-red-800">✗ Feed is invalid</p>
                <p className="text-sm text-red-700">{testResult.error}</p>
              </>
            )}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Category
        </label>
        <select
          {...register("category")}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
        >
          <option value="">Select a category</option>
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
        {errors.category && (
          <p className="mt-1 text-sm text-red-600">{errors.category.message}</p>
        )}
      </div>

      <div className="flex space-x-4">
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : "Save Source"}
        </button>
      </div>
    </form>
  );
}
