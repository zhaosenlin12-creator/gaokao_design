import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import App from "../App.jsx";

function openPath(pathname) {
  cleanup();
  window.history.pushState({}, "", pathname);
  render(<App />);
}

test("shows the gaokao demo page", () => {
  openPath("/app-demo/gaokao-map");
  expect(screen.getByText("山河志愿 · 高考志愿填报模拟器")).toBeInTheDocument();
  expect(screen.getByText("RIASEC 兴趣")).toBeInTheDocument();
  expect(screen.getByText("古地图")).toBeInTheDocument();
});

test("registers a local email account and logs in", () => {
  openPath("/auth/signup");
  fireEvent.change(screen.getByPlaceholderText("your-username"), { target: { value: "gaokao-user" } });
  fireEvent.change(screen.getByPlaceholderText("你的名字"), { target: { value: "高考用户" } });
  fireEvent.change(screen.getByPlaceholderText("you@example.com"), { target: { value: "1255330251@qq.com" } });
  fireEvent.change(screen.getByPlaceholderText("至少 8 位"), { target: { value: "zsl13177068887" } });
  fireEvent.click(screen.getByRole("button", { name: "创建账号" }));

  openPath("/auth/signin");
  fireEvent.change(screen.getByPlaceholderText("you@example.com"), { target: { value: "1255330251@qq.com" } });
  fireEvent.change(screen.getByPlaceholderText("至少 8 位"), { target: { value: "zsl13177068887" } });
  fireEvent.click(screen.getByRole("button", { name: "登录" }));

  expect(window.location.pathname).toBe("/app-demo/gaokao-map");
});
