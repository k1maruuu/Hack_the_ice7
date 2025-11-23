// components/Header.tsx
import { useRouter } from "next/router";
import { useState } from "react";
import { useAuth } from "../lib/AuthContext";

const Header: React.FC = () => {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const goHome = () => router.push("/");
  const goTrips = () => router.push("/trips");
  const goSupport = () => router.push("/support");
  const goLogin = () => router.push("/login?mode=login");
  const goRegister = () => router.push("/login?mode=register");

  const shortName = (full?: string | null) => {
    if (!full) return "";
    const parts = full.trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return "";
    const last = parts[0];
    const initials = parts
      .slice(1)
      .map((p) => (p ? `${p[0].toUpperCase()}.` : ""))
      .join("");
    return `${last} ${initials}`;
  };

  const avatarLetter =
    user?.full_name?.trim()?.charAt(0).toUpperCase() || "U";

  const isActive = (path: string) =>
    router.pathname === path ? "text-[#243850]" : "text-gray-700";

  const handleLogout = () => {
    logout();
    setIsProfileOpen(false);
    router.push("/");
  };

  return (
    <header className="w-full bg-white shadow-sm">
      <div className="max-w-[1200px] mx-auto flex items-center justify-between py-4 px-4 sm:px-6">
        {/* ЛОГО слева */}
        <button
          onClick={goHome}
          className="text-lg font-semibold tracking-wide text-[#243850]"
        >
          Comeltrans
        </button>

        {/* ЦЕНТР: навигация (десктоп) */}
        <nav className="hidden md:flex items-center gap-8 text-sm">
          <button
            onClick={goTrips}
            className={`hover:text-[#243850] transition-colors ${isActive(
              "/trips"
            )}`}
          >
            Мои поездки
          </button>
          <button
            onClick={goSupport}
            className={`hover:text-[#243850] transition-colors ${isActive(
              "/support"
            )}`}
          >
            Поддержка
          </button>
        </nav>

        {/* ПРАВО */}
        <div className="flex items-center gap-3">
          {/* ГОСТЬ */}
          {!user && (
            <>
              <button
                onClick={goLogin}
                className="hidden sm:inline-flex px-4 py-2 text-sm rounded-full text-[#5D7285] hover:text-[#243850] transition-colors"
              >
                Вход
              </button>
              <button
                onClick={goRegister}
                className="hidden sm:inline-flex px-5 py-2 text-sm rounded-full bg-[#243850] text-white hover:bg-[#1a2839] transition-colors"
              >
                Регистрация
              </button>
            </>
          )}

          {/* АВТОРИЗОВАН: имя + мини-панель профиля в шапке */}
          {user && (
            <div className="relative hidden sm:flex items-center gap-3">
              <button
                onClick={() => setIsProfileOpen((v) => !v)}
                className="flex items-center gap-2"
              >
                <span className="text-sm text-[#243850] hover:underline">
                  {shortName(user.full_name)}
                </span>
                <span className="h-8 w-8 rounded-full bg-[#D4D9E2] flex items-center justify-center text-sm font-semibold text-[#243850]">
                  {avatarLetter}
                </span>
              </button>

              {isProfileOpen && (
                <div className="absolute right-0 top-[115%] w-64 bg-white rounded-2xl shadow-xl border border-gray-100 z-30">
                  <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-[#D4D9E2] flex items-center justify-center text-sm font-semibold text-[#243850]">
                      {avatarLetter}
                    </div>
                    <div className="text-sm">
                      <p className="font-semibold text-[#243850]">
                        {user.full_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {user.email_user || "Email не указан"}
                      </p>
                    </div>
                  </div>

                  <div className="px-4 py-3 text-xs text-gray-700 space-y-1.5">
                    <div>
                      <p className="text-gray-500">Телефон</p>
                      <p className="font-medium">
                        {user.phone_number || "Не указан"}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">Пол</p>
                      <p className="font-medium">
                        {user.sex || "Не указан"}
                      </p>
                    </div>
                  </div>

                  <div className="px-4 pb-3 pt-1 flex justify-end">
                    <button
                      onClick={handleLogout}
                      className="px-3 py-1.5 rounded-full bg-red-500 text-white text-xs hover:bg-red-600"
                    >
                      Выйти
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* МОБИЛЬНЫЙ БУРГЕР */}
          <button
            className="md:hidden flex flex-col justify-center gap-[4px]"
            onClick={() => setIsMenuOpen((v) => !v)}
            aria-label="Открыть меню"
          >
            <span className="w-6 h-[2px] bg-gray-800 rounded-full" />
            <span className="w-6 h-[2px] bg-gray-800 rounded-full" />
          </button>
        </div>
      </div>

      {/* МОБИЛЬНОЕ МЕНЮ */}
      {isMenuOpen && (
        <div className="md:hidden border-t bg-white">
          <div className="max-w-[1200px] mx-auto px-4 py-3 flex flex-col gap-2 text-sm">
            <button
              onClick={() => {
                goTrips();
                setIsMenuOpen(false);
              }}
              className={`text-left py-1 ${isActive("/trips")}`}
            >
              Мои поездки
            </button>
            <button
              onClick={() => {
                goSupport();
                setIsMenuOpen(false);
              }}
              className={`text-left py-1 ${isActive("/support")}`}
            >
              Поддержка
            </button>

            {!user && (
              <>
                <button
                  onClick={() => {
                    goLogin();
                    setIsMenuOpen(false);
                  }}
                  className="text-left py-1"
                >
                  Вход
                </button>
                <button
                  onClick={() => {
                    goRegister();
                    setIsMenuOpen(false);
                  }}
                  className="text-left py-1"
                >
                  Регистрация
                </button>
              </>
            )}

            {user && (
              <button
                onClick={() => {
                  handleLogout();
                  setIsMenuOpen(false);
                }}
                className="text-left py-1 text-red-500"
              >
                Выйти
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
