import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    access_token?: string;
    user?: DefaultSession["user"] & {
      id?: string;
    };
  }

  interface User {
    id: string;
    token?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id?: string;
    access_token?: string;
  }
}
