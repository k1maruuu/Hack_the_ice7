// components/LoginForm.tsx
import { useState, useEffect } from "react";
import axios from "axios";
import { login, registerAndLogin } from "../lib/auth";
import { useAuth } from "../lib/AuthContext";
import { useRouter } from "next/router";

type Mode = "login" | "register" | "success";

// Нормализация телефона: всегда 7XXXXXXXXXX
function normalizePhone(phone: string): string {
  let digits = phone.replace(/\D/g, "");

  if (digits.startsWith("8")) {
    digits = "7" + digits.slice(1);
  }

  if (!digits.startsWith("7")) {
    digits = "7" + digits;
  }

  if (digits.length > 11) {
    digits = digits.slice(0, 11);
  }

  return digits;
}

// Примитивная проверка email
function isValidEmail(email: string): boolean {
  const trimmed = email.trim();
  if (!trimmed.includes("@")) return false;
  if (!trimmed.includes(".")) return false;
  if (trimmed.startsWith("@") || trimmed.endsWith("@")) return false;
  return true;
}

// ФИО: 2–3 слова
function isValidFullName(fullName: string): boolean {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  return parts.length === 2 || parts.length === 3;
}

// Пароль: >=8, есть буквы и цифры
function isStrongPassword(password: string): boolean {
  if (password.length < 8) return false;
  const hasLetter = /[A-Za-zА-Яа-я]/.test(password);
  const hasDigit = /\d/.test(password);
  return hasLetter && hasDigit;
}

const LoginForm: React.FC = () => {
  const router = useRouter();
  const { reloadUser } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [isSwitching, setIsSwitching] = useState(false);

  // логин
  const [emailLogin, setEmailLogin] = useState("");
  const [passwordLogin, setPasswordLogin] = useState("");

  // рега
  const [phoneReg, setPhoneReg] = useState("");
  const [emailReg, setEmailReg] = useState("");
  const [fullNameReg, setFullNameReg] = useState("");
  const [sexReg, setSexReg] = useState<"" | "М" | "Ж">("");
  const [passwordReg, setPasswordReg] = useState("");
  const [agreePersonal, setAgreePersonal] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    const q = router.query.mode;
    if (q === "register") setMode("register");
    if (q === "login") setMode("login");
  }, [router.query.mode]);

  const switchMode = (next: Mode) => {
    setIsSwitching(true);
    setTimeout(() => {
      setMode(next);
      setIsSwitching(false);
      setError(null);
    }, 200);
  };

  const handlePhoneRegChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.replace(/\D/g, "");
    if (value.length > 11) value = value.slice(0, 11);
    setPhoneReg(value);
  };

  // ЛОГИН ПО ПОЧТЕ
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (attempts >= 5) {
      setError("Аккаунт временно заблокирован из-за большого числа попыток входа");
      return;
    }

    const trimmedEmail = emailLogin.trim();
    if (!isValidEmail(trimmedEmail)) {
      setError("Неправильная почта или пароль");
      return;
    }

    try {
      await login(trimmedEmail, passwordLogin);
      await reloadUser();
      await router.push("/");
    } catch (_err) {
      setAttempts((prev) => prev + 1);
      setError("Неправильная почта или пароль");
    }
  };

  // РЕГИСТРАЦИЯ
  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!agreePersonal || !agreeTerms) {
      setError("Нужно согласиться с условиями и обработкой данных");
      return;
    }

    const phoneDigits = phoneReg.replace(/\D/g, "");
    if (phoneDigits.length !== 11) {
      setError("Введите номер телефона в формате 7XXXXXXXXXX (11 цифр)");
      return;
    }
    const normalizedPhone = normalizePhone(phoneReg);

    if (!isValidFullName(fullNameReg)) {
      setError(
        "ФИО должно состоять из 2 или 3 слов (например: Иванов Иван или Иванов Иван Иванович)"
      );
      return;
    }

    if (!sexReg) {
      setError("Выберите пол");
      return;
    }

    if (!isValidEmail(emailReg)) {
      setError("Введите корректный e-mail (должны быть @ и точка)");
      return;
    }

    if (!isStrongPassword(passwordReg)) {
      setError(
        "Пароль должен быть не короче 8 символов и содержать буквы и цифры"
      );
      return;
    }

    try {
      await registerAndLogin({
        full_name: fullNameReg.trim(),
        sex: sexReg,
        email_user: emailReg.trim(),
        phone_number: normalizedPhone,
        password: passwordReg,
      });

      await reloadUser();
      switchMode("success");
    } catch (err: unknown) {
      console.error("Register error:", err);

      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        const detail =
          typeof err.response?.data === "object" &&
          err.response?.data !== null &&
          "detail" in err.response.data
            ? (err.response.data as { detail?: string }).detail
            : undefined;

        if (status === 400 && detail === "Email already registered") {
          setError("Пользователь с такой почтой уже существует");
        } else if (status === 403 && detail === "Weak password") {
          setError("Пароль не соответствует требованиям безопасности");
        } else {
          setError("Не удалось создать аккаунт. Попробуйте позже");
        }
      } else {
        setError("Неизвестная ошибка при регистрации");
      }
    }
  };

  const goToMain = () => {
    router.push("/");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8F8F8] px-4">
      <div
        className={`w-full max-w-md bg-white rounded-[32px] shadow-lg px-6 py-10 sm:px-10 sm:py-12 transform transition-all duration-200 ${
          isSwitching ? "scale-95 opacity-0" : "scale-100 opacity-100"
        }`}
      >
        {mode === "login" && (
          <form onSubmit={handleLoginSubmit} className="space-y-4 ">
            <div className="mb-8 text-center">
              <h1 className="text-xl font-semibold mb-1">Comeltrans</h1>
            </div>

            {error && (
              <div className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                E-mail
              </label>
              <input
                type="email"
                value={emailLogin}
                onChange={(e) => setEmailLogin(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                placeholder="you@company.ru"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Пароль
              </label>
              <input
                type="password"
                value={passwordLogin}
                onChange={(e) => setPasswordLogin(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                placeholder="Введите пароль"
                required
              />
            </div>

            <button
              type="submit"
              className="w-full rounded-full bg-[#243850] text-white py-2.5 text-sm font-medium hover:bg-[#1b2a3a] transition-colors"
            >
              Войти
            </button>

            <div className="flex justify-between items-center text-xs text-gray-500">
              <button
                type="button"
                className="underline-offset-2 hover:underline"
              >
                Восстановить пароль
              </button>
              <button
                type="button"
                onClick={() => switchMode("register")}
                className="underline-offset-2 hover:underline"
              >
                Регистрация
              </button>
            </div>
          </form>
        )}

        {mode === "register" && (
          <form onSubmit={handleRegisterSubmit} className="space-y-3">
            <div className="mb-6 text-center">
              <h1 className="text-xl font-semibold mb-1">Регистрация</h1>
            </div>

            {error && (
              <div className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs text-gray-500 mb-1">Телефон</label>
              <input
                type="tel"
                value={phoneReg}
                onChange={handlePhoneRegChange}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                placeholder="7XXXXXXXXXX"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                ФИО полностью
              </label>
              <input
                type="text"
                value={fullNameReg}
                onChange={(e) => setFullNameReg(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                placeholder="Иванов Иван Иванович"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Пол
                </label>
                <select
                  value={sexReg}
                  onChange={(e) =>
                    setSexReg(e.target.value as "" | "М" | "Ж")
                  }
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                  required
                >
                  <option value="">Не выбран</option>
                  <option value="М">Мужской</option>
                  <option value="Ж">Женский</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  E-mail
                </label>
                <input
                  type="email"
                  value={emailReg}
                  onChange={(e) => setEmailReg(e.target.value)}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                  placeholder="you@company.ru"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Пароль
              </label>
              <input
                type="password"
                value={passwordReg}
                onChange={(e) => setPasswordReg(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                placeholder="Не менее 8 символов"
                required
              />
            </div>

            <div className="space-y-1 text-[11px] text-gray-500">
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={agreePersonal}
                  onChange={(e) => setAgreePersonal(e.target.checked)}
                  className="mt-[2px]"
                />
                <span>
                  Согласен на обработку персональных данных и получение
                  информационных сообщений
                </span>
              </label>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={agreeTerms}
                  onChange={(e) => setAgreeTerms(e.target.checked)}
                  className="mt-[2px]"
                />
                <span>
                  Ознакомлен и согласен с условиями использования сервиса
                  Comeltrans
                </span>
              </label>
            </div>

            <button
              type="submit"
              className="w-full rounded-full bg-[#243850] text-white py-2.5 text-sm font-medium hover:bg-[#1b2a3a] transition-colors"
            >
              Создать аккаунт
            </button>

            <div className="text-xs text-center text-gray-500">
              Уже есть аккаунт?{" "}
              <button
                type="button"
                onClick={() => switchMode("login")}
                className="underline-offset-2 hover:underline"
              >
                Войти
              </button>
            </div>
          </form>
        )}

        {mode === "success" && (
          <div className="text-center space-y-4">
            <h1 className="text-xl font-semibold">Аккаунт создан</h1>
            <button
              type="button"
              onClick={goToMain}
              className="w-full rounded-full bg-[#243850] text-white py-2.5 text-sm font-medium hover:bg-[#1b2a3a] transition-colors"
            >
              Перейти на главную
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default LoginForm;
