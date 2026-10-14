"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

export default function Home() {
  const router = useRouter();
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === "loading") return;

    if (session) {
      router.push("/dashboard");
    } else {
      router.push("/auth/login");
    }
  }, [session, status, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-gray-500">Redirecting...</p>
    </div>
  );
}
