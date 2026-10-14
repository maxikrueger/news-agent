import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import type { TokenResponse } from "@/lib/types";

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          console.error("[AUTH] Missing email or password");
          return null;
        }

        try {
          const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

          const res = await fetch(
            `${apiUrl}/api/auth/login`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                email: credentials.email,
                password: credentials.password,
              }),
            }
          );

          if (!res.ok) {
            console.error("[AUTH] Login rejected by backend:", res.status);
            return null;
          }

          const data: TokenResponse = await res.json();

          return {
            id: String(data.user_id),
            email: data.email,
            token: data.access_token,
          };
        } catch (error: unknown) {
          console.error(
            "[AUTH] Exception in authorize:",
            error instanceof Error ? error.message : error
          );
          return null;
        }
      },
    }),
  ],
  pages: {
    signIn: "/auth/login",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.access_token = user.token;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id;
        session.access_token = token.access_token;
      }
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
});

export { handler as GET, handler as POST };
