import axios, { AxiosError } from "axios";
import { getSession } from "next-auth/react";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(async (config) => {
  const session = await getSession();
  const token = session?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Redirect to login on unauthorized
      window.location.href = "/auth/login";
    }
    return Promise.reject(error);
  }
);

export default api;
