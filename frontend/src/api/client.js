import axios from "axios";
const apiClient = axios.create({ baseURL: "http://localhost:8000" });
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("securify_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
apiClient.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("securify_token");
      localStorage.removeItem("securify_user");
      if (window.location.pathname !== "/login") window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
export default apiClient;
