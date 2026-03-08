import { createBrowserRouter, Navigate } from "react-router";
import { ProtectedLayout } from "./layouts/ProtectedLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { ChatPage } from "./pages/ChatPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { VerifyPage } from "./pages/VerifyPage";

export const appRoutes = [
  {
    element: <PublicLayout />,
    children: [
      {
        path: "/login",
        element: <LoginPage />,
      },
      {
        path: "/register",
        element: <RegisterPage />,
      },
      {
        path: "/verify",
        element: <VerifyPage />,
      },
    ],
  },
  {
    element: <ProtectedLayout />,
    children: [
      {
        path: "/",
        element: <ChatPage />,
      },
      {
        path: "/history",
        element: <HistoryPage />,
      },
      {
        path: "/history/:sessionId",
        element: <SessionDetailPage />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/login" replace />,
  },
];

export const appRouter = createBrowserRouter(appRoutes);
