"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { useForm, useWatch } from "react-hook-form";
import api from "@/lib/api";
import { getApiErrorDetail } from "@/lib/types";

interface PasswordChangeForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export default function SettingsPage() {
  const { data: session } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<PasswordChangeForm>();

  const newPassword = useWatch({ control, name: "new_password" });

  const onPasswordChange = async (data: PasswordChangeForm) => {
    if (data.new_password !== data.confirm_password) {
      setError("New passwords do not match");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      await api.post("/api/auth/password-change", {
        current_password: data.current_password,
        new_password: data.new_password,
      });
      setSuccess("Password changed successfully");
      reset();
    } catch (err: unknown) {
      setError(getApiErrorDetail(err) || "Failed to change password");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-gray-600">Manage your account preferences</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Account Information */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Account Information
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Email Address
              </label>
              <input
                type="email"
                value={session?.user?.email || ""}
                disabled
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 bg-gray-50"
              />
              <p className="mt-1 text-xs text-gray-500">
                Email address cannot be changed
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Account Created
              </label>
              <input
                type="text"
                value={session?.user?.email ? "Active" : "Pending"}
                disabled
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 bg-gray-50"
              />
            </div>
          </div>
        </div>

        {/* Change Password */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Change Password
          </h2>

          {error && (
            <div className="rounded-md bg-red-50 p-4 mb-4">
              <p className="text-sm font-medium text-red-800">{error}</p>
            </div>
          )}

          {success && (
            <div className="rounded-md bg-green-50 p-4 mb-4">
              <p className="text-sm font-medium text-green-800">{success}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onPasswordChange)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Current Password
              </label>
              <input
                {...register("current_password", {
                  required: "Current password is required",
                })}
                type="password"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              />
              {errors.current_password && (
                <p className="mt-1 text-sm text-red-600">
                  {errors.current_password.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                New Password
              </label>
              <input
                {...register("new_password", {
                  required: "New password is required",
                  minLength: {
                    value: 8,
                    message: "Password must be at least 8 characters",
                  },
                  pattern: {
                    value: /^(?=.*[A-Z])(?=.*\d)/,
                    message:
                      "Password must contain uppercase letter and number",
                  },
                })}
                type="password"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              />
              {errors.new_password && (
                <p className="mt-1 text-sm text-red-600">
                  {errors.new_password.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Confirm New Password
              </label>
              <input
                {...register("confirm_password", {
                  required: "Please confirm your password",
                  validate: (value) =>
                    value === newPassword || "Passwords do not match",
                })}
                type="password"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              />
              {errors.confirm_password && (
                <p className="mt-1 text-sm text-red-600">
                  {errors.confirm_password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? "Updating..." : "Update Password"}
            </button>
          </form>
        </div>
      </div>

      {/* Preferences */}
      <div className="mt-6 bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Notification Preferences
        </h2>
        <p className="text-gray-600 text-sm mb-4">
          Configure how you receive digest notifications
        </p>
        <div className="space-y-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              defaultChecked={true}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            <span className="ml-2 text-sm text-gray-700">
              Receive digests at scheduled times
            </span>
          </label>
          <label className="flex items-center">
            <input
              type="checkbox"
              defaultChecked={false}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            <span className="ml-2 text-sm text-gray-700">
              Receive weekly summary email
            </span>
          </label>
          <label className="flex items-center">
            <input
              type="checkbox"
              defaultChecked={false}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            <span className="ml-2 text-sm text-gray-700">
              Notify me of errors and failures
            </span>
          </label>
        </div>
      </div>
    </div>
  );
}
