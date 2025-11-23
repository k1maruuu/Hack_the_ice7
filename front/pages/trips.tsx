// pages/trips.tsx
import { NextPage } from "next";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import api from "../lib/api";
import { parseCookies } from "../lib/auth";
import { Booking } from "../lib/types";

const TripsPage: NextPage = () => {
  const router = useRouter();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthed, setIsAuthed] = useState<boolean>(false);

  useEffect(() => {
    const cookies = parseCookies();
    const token = cookies._token;

    if (!token) {
      setIsAuthed(false);
      setLoading(false);
      return;
    }

    setIsAuthed(true);
    setLoading(true);
    setError(null);

    api
      .get<Booking[]>("/bookings/my", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      .then((res) => {
        setBookings(res.data);
      })
      .catch((err) => {
        console.error(err);
        setError("Не удалось загрузить ваши поездки");
      })
      .finally(() => setLoading(false));
  }, []);

  const renderAmount = (b: Booking) => {
    const num = Number(b.total_amount);
    if (Number.isFinite(num)) {
      return `${num.toLocaleString("ru-RU")} ₽`;
    }
    return `${b.total_amount} ₽`;
  };

  if (!isAuthed) {
    return (
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 pt-10 pb-20">
        <div className="bg-white rounded-[32px] shadow-[0_20px_60px_rgba(15,23,42,0.12)] px-4 sm:px-8 py-6 sm:py-8">
          <h1 className="text-lg sm:text-xl font-semibold text-[#243850] mb-4">
            Мои поездки
          </h1>
          <p className="text-sm text-gray-600 mb-4">
            Чтобы просматривать купленные билеты, войдите в аккаунт.
          </p>
          <button
            onClick={() => router.push("/login?mode=login")}
            className="px-5 py-2 rounded-full bg-[#243850] text-white text-sm hover:bg-[#1b2a3a]"
          >
            Войти
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 pt-10 pb-20">
      <div className="bg-white rounded-[32px] shadow-[0_20px_60px_rgba(15,23,42,0.12)] px-4 sm:px-8 py-6 sm:py-8">
        <h1 className="text-lg sm:text-xl font-semibold text-[#243850] mb-4">
          Мои поездки
        </h1>

        {loading && (
          <p className="text-sm text-gray-500">Загружаем ваши поездки…</p>
        )}

        {error && !loading && (
          <p className="text-sm text-red-500 mb-4">{error}</p>
        )}

        {!loading && !error && bookings.length === 0 && (
          <div className="border border-dashed border-gray-200 rounded-2xl px-4 py-6 sm:px-6 sm:py-8 text-center">
            <h2 className="text-sm sm:text-base font-medium text-[#243850] mb-2">
              У вас пока нет поездок
            </h2>
            <p className="text-xs sm:text-sm text-gray-500 mb-4">
              Найдите маршрут на главной странице и забронируйте поездку.
            </p>
            <button
              onClick={() => router.push("/")}
              className="px-5 py-2 rounded-full bg-[#243850] text-white text-xs sm:text-sm hover:bg-[#1b2a3a]"
            >
              Найти маршрут
            </button>
          </div>
        )}

        {!loading && bookings.length > 0 && (
          <div className="space-y-3">
            {bookings.map((b) => (
              <div
                key={b.id}
                className="border border-gray-100 rounded-2xl px-4 py-4 sm:px-6 sm:py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
              >
                <div>
                  <p className="text-xs uppercase tracking-wide text-[#00B33C] mb-1">
                    Билет #{b.id}
                  </p>
                  <p className="text-sm sm:text-base font-semibold text-[#243850]">
                    Поездка {new Date(b.departure_date).toLocaleDateString(
                      "ru-RU"
                    )}
                    {b.return_date
                      ? ` — ${new Date(
                          b.return_date
                        ).toLocaleDateString("ru-RU")}`
                      : ""}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Пассажиров: {b.passenger_count ?? 1}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Оформлено:{" "}
                    {new Date(b.created_at).toLocaleString("ru-RU")}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Контакты: {b.contact_email} • {b.contact_phone}
                  </p>
                </div>

                <div className="text-right">
                  <p className="text-xs text-gray-500 mb-1">Статус</p>
                  <p className="text-sm font-semibold text-[#243850] mb-2">
                    {b.status === "pending"
                      ? "В обработке"
                      : b.status === "confirmed"
                      ? "Подтверждён"
                      : b.status === "cancelled"
                      ? "Отменён"
                      : b.status}
                  </p>
                  <p className="text-xs text-gray-500 mb-1">Стоимость</p>
                  <p className="text-base font-semibold text-[#243850]">
                    {renderAmount(b)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TripsPage;
