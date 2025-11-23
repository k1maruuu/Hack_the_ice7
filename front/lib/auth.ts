// lib/auth.ts
import type { GetServerSidePropsContext } from "next";
import api from "./api";
import { setCookie, parseCookies, destroyCookie } from "nookies";
import { User } from "./types";

export { parseCookies };

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  full_name: string;
  sex: string | null;
  email_user: string;
  email_corporate: string;
  phone_number: string;
  birthday: string;
  position_employee: string;
  password: string;
}

// ЛОГИН
export async function login(email: string, password: string): Promise<void> {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const res = await api.post<LoginResponse>("/auth/token", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  setCookie(null, "_token", res.data.access_token, {
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
}

// РЕГИСТРАЦИЯ + СРАЗУ ЛОГИН
export async function registerAndLogin(payload: RegisterPayload): Promise<void> {
  await api.post("/users/register", payload);

  // Сразу логинимся под этим же email/паролем
  await login(payload.email_user, payload.password);
}

// Получение пользователя (SSR/клиент)
export async function getCurrentUser(
  context?: GetServerSidePropsContext | null
): Promise<User | null> {
  try {
    const cookies = parseCookies(context ?? undefined);
    const token = cookies._token;
    if (!token) return null;

    const res = await api.get<User>("/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return res.data;
  } catch {
    return null;
  }
}

export function logout() {
  destroyCookie(null, "_token", { path: "/" });
}

export function isAuthenticated(
  context?: GetServerSidePropsContext | null
): boolean {
  const cookies = parseCookies(context ?? undefined);
  const token = cookies._token;
  return !!token;
}
