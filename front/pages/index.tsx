// pages/index.tsx
import { useState } from "react";
import { useRouter } from "next/router";
import api from "../lib/api";
import { parseCookies } from "../lib/auth";

type SegmentOption = {
  flight_no?: string;
  dep_time?: string;
  arr_time?: string;
  price_rub?: number;
  departure_at?: string;
  arrival_at?: string;
  [key: string]: any;
};

type Segment = {
  segment_type: string;
  provider: string;
  origin: string;
  destination: string;
  options?: SegmentOption[];
};

type RoutePart = {
  segments: Segment[];
};

type SearchApiResponse = {
  type: string; // "multimodal" | "flight_only" | ...
  origin: string;
  destination: string;
  departure_date: string;
  return_date?: string | null;
  outbound: RoutePart;
  return?: RoutePart | null;
};

type RouteVariant = {
  id: string;
  title: string;
  minPrice: number | null;
  durationHours: number | null;
  transfers: number;
};

type SortKey = "price" | "duration" | "transfers";

export default function Home() {
  const router = useRouter();

  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [departureDate, setDepartureDate] = useState("");
  const [returnDate, setReturnDate] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SearchApiResponse | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const [sortKey, setSortKey] = useState<SortKey>("price");
  const [showDetails, setShowDetails] = useState(false);
  const [variants, setVariants] = useState<RouteVariant[]>([]);

  const [buyingId, setBuyingId] = useState<string | null>(null);
  const [buyError, setBuyError] = useState<string | null>(null);

  // Преобразуем YYYY-MM-DD -> DD.MM.YYYY для твоего бэка
  const formatDateForApi = (value: string): string => {
    if (!value) return "";
    const [y, m, d] = value.split("-");
    return `${d}.${m}.${y}`;
  };

  const getRouteTitle = (data: SearchApiResponse): string => {
    const segs = data.outbound?.segments || [];
    const hasFlight = segs.some((s) => s.segment_type === "flight");
    const hasBus = segs.some((s) => s.segment_type === "bus");
    const hasRiver = segs.some((s) => s.segment_type === "river");

    if (hasFlight && hasRiver) return "Авиа + Речной транспорт";
    if (hasFlight && hasBus) return "Авиа + Автобус";
    if (hasFlight) return "Авиа маршрут";
    if (hasBus || hasRiver) return "Наземный маршрут";
    return "Маршрут";
  };

  const getTransfersCount = (data: SearchApiResponse): number => {
    const segsOut = data.outbound?.segments?.length || 0;
    const segsRet = data.return?.segments?.length || 0;
    const totalSegments = segsOut + segsRet;
    const trips = data.return ? 2 : 1;
    return Math.max(0, totalSegments - trips);
  };

  const getMinPrice = (data: SearchApiResponse): number | null => {
    const allSegments = [
      ...(data.outbound?.segments || []),
      ...(data.return?.segments || []),
    ];
    const prices: number[] = [];

    allSegments.forEach((seg) => {
      seg.options?.forEach((opt) => {
        if (typeof opt.price_rub === "number") prices.push(opt.price_rub);
      });
    });

    if (!prices.length) return null;
    return Math.min(...prices);
  };

  const getApproxDurationHours = (data: SearchApiResponse): number | null => {
    const parseTime = (t?: string): number | null => {
      if (!t) return null;
      const m = t.match(/^(\d{1,2}):(\d{2})/);
      if (!m) return null;
      const h = parseInt(m[1], 10);
      const min = parseInt(m[2], 10);
      return h * 60 + min;
    };

    let totalMinutes = 0;
    let hasAny = false;

    const processPart = (part?: RoutePart | null) => {
      if (!part) return;
      part.segments.forEach((seg) => {
        seg.options?.forEach((opt) => {
          // сначала пробуем dep_time/arr_time (S7)
          const dep = parseTime(opt.dep_time);
          const arr = parseTime(opt.arr_time);
          if (dep !== null && arr !== null) {
            let diff = arr - dep;
            if (diff < 0) diff += 24 * 60;
            totalMinutes += diff;
            hasAny = true;
            return;
          }

          // если нет явных времён — пробуем ISO-даты
          if (opt.departure_at && opt.arrival_at) {
            try {
              const d1 = new Date(opt.departure_at);
              const d2 = new Date(opt.arrival_at);
              const diff = (d2.getTime() - d1.getTime()) / 60000;
              if (diff > 0) {
                totalMinutes += diff;
                hasAny = true;
              }
            } catch {
              /* ignore */
            }
          }
        });
      });
    };

    processPart(data.outbound);
    processPart(data.return);

    if (!hasAny) return null;
    return Math.round(totalMinutes / 60);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setHasSearched(true);
    setLoading(true);
    setError(null);
    setResult(null);
    setShowDetails(false);
    setVariants([]);
    setBuyError(null);

    try {
      const dep = formatDateForApi(departureDate);
      const ret = returnDate ? formatDateForApi(returnDate) : undefined;

      const params: Record<string, string> = {
        origin: origin.trim(),
        destination: destination.trim(),
        departure_date: dep,
      };
      if (ret) params.return_date = ret;

      const response = await api.get<SearchApiResponse>(
        "/api/v1/routes/search",
        { params }
      );

      const data = response.data;
      setResult(data);

      const mainVariant: RouteVariant = {
        id: "main",
        title: getRouteTitle(data),
        minPrice: getMinPrice(data),
        durationHours: getApproxDurationHours(data),
        transfers: getTransfersCount(data),
      };

      setVariants([mainVariant]);
    } catch (err: any) {
      console.error(err);
      const msg =
        err?.response?.data?.detail ||
        "Не удалось выполнить поиск. Попробуйте изменить параметры.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // Покупка билета: POST /bookings
  const handleBuy = async (variant: RouteVariant) => {
    if (!result) return;

    const cookies = parseCookies();
    const token = cookies._token;

    if (!token) {
      // не авторизован — отправляем на логин
      router.push("/login?mode=login");
      return;
    }

    try {
      setBuyingId(variant.id);
      setBuyError(null);

      await api.post(
        "/bookings",
        {
          origin: result.origin, // просто для истории, бэк может игнорить
          destination: result.destination,
          departure_date: result.departure_date,
          return_date: result.return_date ?? null,
          price_rub: variant.minPrice ?? 0,
          status: "created",
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      router.push("/trips");
    } catch (e) {
      console.error(e);
      setBuyError("Не удалось оформить покупку. Попробуйте ещё раз.");
    } finally {
      setBuyingId(null);
    }
  };

  // сортировка "вариантов" маршрута (сейчас основной + можно будет добавить другие)
  const sortedVariants = [...variants].sort((a, b) => {
    if (sortKey === "price") {
      const ap = a.minPrice ?? Infinity;
      const bp = b.minPrice ?? Infinity;
      return ap - bp;
    }
    if (sortKey === "duration") {
      const ad = a.durationHours ?? Infinity;
      const bd = b.durationHours ?? Infinity;
      return ad - bd;
    }
    return a.transfers - b.transfers;
  });

  const cheapestId =
    variants.length > 0
      ? variants.reduce((best, curr) => {
          const bestPrice = best.minPrice ?? Infinity;
          const currPrice = curr.minPrice ?? Infinity;
          return currPrice < bestPrice ? curr : best;
        }).id
      : null;

  const fastestId =
    variants.length > 0
      ? variants.reduce((best, curr) => {
          const bestDur = best.durationHours ?? Infinity;
          const currDur = curr.durationHours ?? Infinity;
          return currDur < bestDur ? curr : best;
        }).id
      : null;

  return (
    <div className="flex justify-center px-4 py-8">
      <div className="w-full max-w-[1200px]">
        {/* верхний блок */}
        <div className="grid gap-8 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] items-start">
          {/* описание слева */}
          <div className="space-y-4">
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-semibold text-[#243850]">
              Умные маршруты для сложной логистики
            </h1>
            <p className="text-sm sm:text-base text-gray-600 max-w-xl">
              Выберите точки отправления и прибытия — Comeltrans подберёт для
              вас оптимальные комбинации авиаперелётов, автобусов и других
              видов транспорта.
            </p>
          </div>

          {/* форма справа */}
          <div className="bg-white rounded-[24px] shadow-lg p-4 sm:p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Откуда
                  </label>
                  <input
                    type="text"
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                    placeholder="Москва"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Куда
                  </label>
                  <input
                    type="text"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    placeholder="Якутск"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Дата отправления
                  </label>
                  <input
                    type="date"
                    value={departureDate}
                    onChange={(e) => setDepartureDate(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Дата возвращения (опционально)
                  </label>
                  <input
                    type="date"
                    value={returnDate}
                    onChange={(e) => setReturnDate(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#243850]"
                  />
                </div>
              </div>

              {error && (
                <div className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-full bg-[#243850] text-white py-2.5 text-sm font-medium hover:bg-[#1b2a3a] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? "Идёт поиск..." : "Найти маршрут"}
              </button>
            </form>
          </div>
        </div>

        {/* результаты */}
        <div
          className={`mt-8 transition-all duration-500 ${
            hasSearched
              ? "opacity-100 translate-y-0 max-h-[3000px]"
              : "opacity-0 -translate-y-4 max-h-0 overflow-hidden"
          }`}
        >
          <div className="bg-white rounded-[24px] shadow-lg p-4 sm:p-6">
            <h2 className="text-base sm:text-lg font-semibold text-[#243850] mb-4">
              Результаты поиска
            </h2>

            {!result && !loading && (
              <p className="text-sm text-gray-500">
                Здесь появятся варианты маршрутов после поиска.
              </p>
            )}

            {result && (
              <>
                <div className="flex flex-wrap gap-2 mb-4 text-xs sm:text-sm">
                  <span className="text-gray-500 mr-1">Сортировать по:</span>
                  <button
                    type="button"
                    onClick={() => setSortKey("price")}
                    className={`px-3 py-1 rounded-full border ${
                      sortKey === "price"
                        ? "bg-[#243850] text-white border-[#243850]"
                        : "border-gray-200 text-gray-700"
                    }`}
                  >
                    цене
                  </button>
                  <button
                    type="button"
                    onClick={() => setSortKey("duration")}
                    className={`px-3 py-1 rounded-full border ${
                      sortKey === "duration"
                        ? "bg-[#243850] text-white border-[#243850]"
                        : "border-gray-200 text-gray-700"
                    }`}
                  >
                    времени в пути
                  </button>
                  <button
                    type="button"
                    onClick={() => setSortKey("transfers")}
                    className={`px-3 py-1 rounded-full border ${
                      sortKey === "transfers"
                        ? "bg-[#243850] text-white border-[#243850]"
                        : "border-gray-200 text-gray-700"
                    }`}
                  >
                    пересадкам
                  </button>
                </div>

                {buyError && (
                  <div className="mt-2 text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
                    {buyError}
                  </div>
                )}

                <div className="space-y-3">
                  {sortedVariants.map((variant) => {
                    const isCheapest = variant.id === cheapestId;
                    const isFastest = variant.id === fastestId;

                    return (
                      <div
                        key={variant.id}
                        className="border border-gray-100 rounded-2xl p-4 sm:p-5 flex flex-col gap-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="text-xs uppercase tracking-wide text-[#00B33C] mb-1">
                              {variant.title}
                            </p>
                            <p className="text-sm sm:text-base font-semibold text-[#243850]">
                              {result.origin} — {result.destination}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              Туда:{" "}
                              {result.departure_date
                                ? new Date(
                                    result.departure_date
                                  ).toLocaleDateString("ru-RU")
                                : "—"}
                              {result.return_date && (
                                <>
                                  {" "}
                                  • Обратно:{" "}
                                  {new Date(
                                    result.return_date
                                  ).toLocaleDateString("ru-RU")}
                                </>
                              )}
                            </p>
                          </div>

                          <div className="flex flex-col items-end gap-2">
                            <div className="text-right">
                              <p className="text-xs text-gray-500 mb-1">
                                Общая стоимость
                              </p>
                              <p className="text-base sm:text-lg font-semibold text-[#243850]">
                                {variant.minPrice
                                  ? `от ${variant.minPrice.toLocaleString(
                                      "ru-RU"
                                    )} ₽`
                                  : "уточняется"}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                Время в пути:{" "}
                                {variant.durationHours
                                  ? `${variant.durationHours} ч`
                                  : "уточняется"}
                              </p>
                              <p className="text-xs text-gray-500">
                                Пересадок: {variant.transfers}
                              </p>
                            </div>

                            <div className="flex gap-1">
                              {isCheapest && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px]">
                                  Самый выгодный
                                </span>
                              )}
                              {isFastest && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px]">
                                  Самый быстрый
                                </span>
                              )}
                            </div>

                            <button
                              type="button"
                              onClick={() => handleBuy(variant)}
                              disabled={buyingId === variant.id}
                              className="px-4 py-1.5 rounded-full bg-[#243850] text-white text-xs hover:bg-[#1b2a3a] disabled:opacity-60"
                            >
                              {buyingId === variant.id
                                ? "Оформляем..."
                                : "Купить билет"}
                            </button>
                          </div>
                        </div>

                        <div className="flex justify-end mt-1">
                          <button
                            type="button"
                            onClick={() => setShowDetails((v) => !v)}
                            className="px-4 py-2 rounded-full text-xs sm:text-sm border border-gray-200 hover:bg-gray-50"
                          >
                            {showDetails ? "Скрыть детали" : "Подробнее"}
                          </button>
                        </div>

                        {showDetails && (
                          <div className="mt-2 border-t border-gray-100 pt-3 space-y-3 text-xs sm:text-sm text-gray-700">
                            <div>
                              <p className="font-medium mb-1">Туда</p>
                              {result.outbound?.segments?.map((seg, idx) => (
                                <div key={idx} className="mb-2">
                                  <p className="text-gray-600">
                                    {seg.segment_type === "flight"
                                      ? "Авиа"
                                      : seg.segment_type === "bus"
                                      ? "Автобус"
                                      : seg.segment_type}
                                    : {seg.origin} → {seg.destination}
                                  </p>
                                  {seg.options?.length ? (
                                    <p className="text-gray-500">
                                      Вариантов: {seg.options.length}
                                    </p>
                                  ) : null}
                                </div>
                              ))}
                            </div>

                            {result.return && (
                              <div>
                                <p className="font-medium mb-1">Обратно</p>
                                {result.return.segments?.map((seg, idx) => (
                                  <div key={idx} className="mb-2">
                                    <p className="text-gray-600">
                                      {seg.segment_type === "flight"
                                        ? "Авиа"
                                        : seg.segment_type === "bus"
                                        ? "Автобус"
                                        : seg.segment_type}
                                      : {seg.origin} → {seg.destination}
                                    </p>
                                    {seg.options?.length ? (
                                      <p className="text-gray-500">
                                        Вариантов: {seg.options.length}
                                      </p>
                                    ) : null}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
