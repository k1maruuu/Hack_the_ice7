import axios from "axios";
import { parseCookies } from "nookies";

const isServer = typeof window === "undefined";

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    timeout: 1000000,
});

api.interceptors.request.use(
    (config) => {
        // Не добавляем токен для запроса на /token
        const cleanUrl = config.url?.startsWith("/")
            ? config.url
            : `/${config.url}`;
        config.url = cleanUrl;


        if (isServer) {
            // На сервере НИЧЕГО не трогаем, просто логируем
            console.log(
                "SSR request:",
                config.method,
                config.url,
                "Auth:",
                config.headers?.Authorization
            );
            return config;
        }

        // Клиент: достаём токен из cookies
        const cookies = parseCookies();
        const token = cookies._token;
        console.log("Client request:", config.method, config.url, "Token:", token);

        if (token) {
            config.headers = config.headers || {};
            if (!config.headers.Authorization) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }

        return config;
    },
    (error) => {
        console.error("Request interceptor error:", error);
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error(
            "Response error:",
            error.message,
            "Status:",
            error.response?.status,
            "Data:",
            error.response?.data
        );
        return Promise.reject(error);
    }
);

export default api;